from htmlentitydefs import name2codepoint
import os
import os.path
import re

def ago(delta, units=None):
	parts = []

	for unit, value in (('year', delta.days/365), ('month', delta.days/30 % 12), ('day', delta.days % 30), ('hour', delta.seconds/3600), ('minute', delta.seconds/60 % 60), ('second', delta.seconds % 60), ('millisecond', delta.microseconds/1000)):
		if value > 0 and (unit != 'millisecond' or len(parts) == 0):
			parts.append('%s %s%s' % (value, unit, value != 1 and 's' or ''))
			if units and len(parts) >= units:
				break

	formatted =  ' and '.join(parts)
	return formatted.replace(' and ', ', ', len(parts)-2)

def substitute_entity(match):
    ent = match.group(2)
    if match.group(1) == "#":
        return unichr(int(ent))
    else:
        cp = name2codepoint.get(ent)

        if cp:
            return unichr(cp)
        else:
            return match.group()

def decode_htmlentities(string):
    entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
    return entity_re.subn(substitute_entity, string)[0]

def file_in_path(program):
	path = os.environ.get("PATH", os.defpath).split(os.pathsep)
	path = [os.path.join(dir, program) for dir in path]
	path = [True for file in path if os.path.isfile(file)]
	return bool(path)

def unicode_output(output, errors="strict"):
	try:
		encoding = os.getenv("LANG").split(".")[1]
	except:
		encoding = "ascii"
	return unicode(output, encoding, errors)
