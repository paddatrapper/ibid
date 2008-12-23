import time

from ibid.module import Module
from ibid.decorators import *

class DateTime(Module):

	@addressed
	@notprocessed
	@message
	@match('^\s*(?:date|time)\s*$')
	def process(self, event):
		reply = time.strftime(u"It is %H:%M.%S on %a, %e %b %Y",time.localtime())
		if event.public:
			reply = u'%s: %s' % (event.user, reply)

		event.addresponse(reply)
		return event
