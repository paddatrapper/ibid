import re
from subprocess import Popen, PIPE

import ibid
from ibid.plugins import Processor, match, handler
from ibid.config import Option

help = {}

help['bc'] = u'Calculate mathematical expressions using bc'
class BC(Processor):
    """bc <expression>"""

    feature = 'bc'

    bc = Option('bc', 'Path to bc executable', 'bc')

    @match(r'^bc\s+(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error = bc.communicate(expression.encode('utf-8') + '\n')
        code = bc.wait()

        if code == 0:
            event.addresponse(output.strip())

help['calc'] = 'Returns the anwser to mathematical expressions'
class Calc(Processor):
    """[calc] <expression>"""
    feature = 'calc'

    priority = 500

    extras = ('abs', 'pow', 'round', 'min', 'max')
    banned = ('for', 'yield', 'lambda')

    # Create a safe dict to pass to eval() as locals
    safe = {}
    exec('from math import *', safe)
    del safe['__builtins__']
    for function in extras:
        safe[function] = eval(function)

    @match(r'^(?:calc\s+)?(.+?)$')
    def calculate(self, event, expression):
        for term in self.banned:
            if term in expression:
                return

        try:
            result = eval(expression, {'__builtins__': None}, self.safe)
        except Exception, e:
            return

        if isinstance(result, (int, long, float, complex)):
            event.addresponse(unicode(result))

help['base'] = 'Convert numbers between bases (radixes)'
class BaseConvert(Processor):
    """[convert] <number> [(from|in) base <number>] (in|to) base <number>
    [convert] ascii <text> (in|to) (hex|dec|oct|bin|base <number>)
    [convert] <sequence> (hex|dec|oct|bin) (in|to) ascii"""

    feature = "base"
    
    abbr_named_bases = {
            "hex": 16,
            "dec": 10,
            "oct": 8,
            "bin": 2,
    }

    base_names = {
            2: u"binary",
            3: u"ternary",
            4: u"quaternary",
            6: u"senary",
            8: u"octal",
            9: u"nonary",
            10: u"decimal",
            12: u"duodecimal",
            16: u"hexadecimal",
            20: u"vigesimal",
            30: u"trigesimal",
            32: u"duotrigesimal",
            36: u"hexatridecimal",
    }

    numerals = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
    values = {}
    for value, numeral in enumerate(numerals):
        values[numeral] = value

    def _in_base(self, num, base):
        "Recursive base-display formatter"
        if num == 0:
            return "0"
        return self._in_base(num // base, base).lstrip("0") + self.numerals[num % base]

    def _from_base(self, num, base):
        "Return a base-n number in decimal. Needed as int(x, n) only works for n<=36"
        
        if base <= 36:
            num = num.upper()

        decimal = 0
        for digit in num:
            decimal *= base
            if self.values[digit] >= base:
                raise ValueError("'%s' is not a valid digit in base %i" % (digit, base))
            decimal += self.values[digit]

        return decimal

    def _parse_base(self, base):
        "Parse a base in the form of 'hex' or 'base 13' or None"

        if base is None:
            base = 10
        elif base[:3] in self.abbr_named_bases:
            base = self.abbr_named_bases[base[:3]]
        elif base.startswith(u"base"):
            base = int(base.split()[-1])
        else:
            # The above should be the only cases allowed by the regex
            # This exception indicates programmer error:
            raise ValueError("Unparsable base: " + base)

        return base

    def _name_base(self, base):
        "Shows off the bot's smartypants heritage by naming bases"

        base_name = u"base %i" % base

        if base in self.base_names:
            base_name = self.base_names[base]

        return base_name

    def setup(self):
        bases = []
        for abbr, base in self.abbr_named_bases.iteritems():
            bases.append(r"%s(?:%s)?" % (abbr, self.base_names[base][3:]))
        bases = "|".join(bases)
        self.base_conversion.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/]+)\s+(?:(?:(?:from|in)\s+)?(base\s+\d+|%s)\s+)?(?:in|to|into)\s+(base\s+\d+|%s)\s*$"
            % (bases, bases), re.I)

        self.ascii_decode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?ascii\s+(.+?)(?:(?:\s+(?:in|to|into))?\s+(base\s+\d+|%s))?$" % bases, re.I)
    
        self.ascii_encode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/\s]+?)(?:\s+(?:(?:from|in)\s+)?(base\s+\d+|%s))?\s+(?:in|to|into)\s+ascii$" % bases, re.I)

    @handler
    def base_conversion(self, event, number, base_from, base_to):
        "Arbitrary (2 <= base <= 64) numeric base conversions."

        base_from = self._parse_base(base_from)
        base_to = self._parse_base(base_to)
        
        if min(base_from, base_to) < 2 or max(base_from, base_to) > 64:
            event.addresponse(u"Sorry, valid bases are between 2 and 64, inclusive.")
            return
        
        try:
            number = self._from_base(number, base_from)
        except ValueError, e:
            event.addresponse(e.message)
            return
        
        event.addresponse(u"That is %s in %s." %
                (self._in_base(number, base_to), self._name_base(base_to)))

    @handler
    def ascii_decode(self, event, text, base_to):
        "Display the values of each character in an ASCII string"

        base_to = self._parse_base(base_to)

        if len(text) > 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1]
        
        output = u""
        for char in text:
            code_point = ord(char)
            if code_point > 255:
                output += u"U%s " % self._in_base(code_point, base_to)
            else:
                output += self._in_base(code_point, base_to) + u" "
        
        output = output.strip()

        event.addresponse(u"That is %s in %s." % (output, self._name_base(base_to)))

        if base_to == 64 and [True for plugin in ibid.processors if plugin.feature == "base64"]:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature.')

    @handler
    def ascii_encode(self, event, source, base_from):

        base_from = self._parse_base(base_from)

        output = u""
        buf = u""

        def process_buf(buf):
            char = self._from_base(buf, base_from)
            if char > 127:
                raise ValueError(u"I only deal with the first page of ASCII (i.e. under 127). %i is invalid." % char)
            elif char < 32:
                return u" %s " % "NUL SOH STX EOT ENQ ACK BEL BS HT LF VT FF SO SI DLE DC1 DC2 DC2 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US".split()[char]
            elif char == 127:
                return u" DEL "
            return unichr(char)

        try:
            for char in source:
                if char == u" ":
                    if len(buf) > 0:
                        output += process_buf(buf)
                        buf = u""
                else:
                    buf += char
                    if (len(buf) == 2 and base_from == 16) or (len(buf) == 3 and base_from == 8) or (len(buf) == 8 and base_from == 2):
                        output += process_buf(buf)
                        buf = u""

            if len(buf) > 0:
                output += process_buf(buf)
        except ValueError, e:
            event.addresponse(e.message)
            return
        
        event.addresponse(u'That is "%s".' % output)
        if base_from == 64 and [True for plugin in ibid.processors if plugin.feature == "base64"]:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature.')

# vi: set et sta sw=4 ts=4:
