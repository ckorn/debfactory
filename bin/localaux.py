#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    (C) Copyright 2009, GetDeb Team - https://launchpad.net/~getdeb
#    --------------------------------------------------------------------
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#    --------------------------------------------------------------------
"""
Local auxiliar functions library
"""

import commands
from smtplib import SMTP
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr

#!/usr/bin/python
#
#  (C) Copyright 2009, GetDeb Team - https://launchpad.net/~getdeb
#  --------------------------------------------------------------------
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  --------------------------------------------------------------------
#

import smtplib
import atexit
import time

def uniq(alist):
    set = {}
    return [set.setdefault(e,e) for e in alist if e not in set]

""" Small helper class for logging """
class Logger:
    def __init__(self, verbose=True):
        self.verbose = verbose
        
    def log(self, message, verbose=None):
        """
        If verbose is True print the message
        """
        verbose = verbose or self.verbose
        if self.verbose:
            print "%s: %s" % (time.strftime('%c'), message)
            
    def print_(self, message):
        """
        always print a message
        """
        print "%s: %s" % (time.strftime('%c'), message)
		
def check_md5sum(filename, expected_md5sum):
	"""
	"""
	md5sum=commands.getoutput('md5sum '+filename)
	(newmd5, dummy) = md5sum.split()
	#newmd5 = newmd5.strip('\r\n')
	if newmd5 != expected_md5sum:     	
		return newmd5
	return None

def send_mail_message(destination, subject, body):
    """
    Sends a mail message
    """
    fromaddr = '"GetDeb Automated Builder" <autobuild@getdeb.net>'
    if type(destination) is list:        
        destination = uniq(destination)
        for dest in destination:
            send_mail(fromaddr, dest, subject, body)
    else:
        send_mail(fromaddr, destination, subject, body)    
        
def send_mail(sender, recipient, subject, body):
    """Send an email.

    All arguments should be Unicode strings (plain ASCII works as well).

    Only the real name part of sender and recipient addresses may contain
    non-ASCII characters.

    The email will be properly MIME encoded and delivered though SMTP to
    localhost port 25.  This is easy to change if you want something different.

    The charset of the email will be the first one out of US-ASCII, ISO-8859-1
    and UTF-8 that can represent all the characters occurring in the email.
    """

    # Header class is smart enough to try US-ASCII, then the charset we
    # provide, then fall back to UTF-8.
    header_charset = 'ISO-8859-1'

    # We must choose the body charset manually
    for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
        try:
            body.encode(body_charset)
        except UnicodeError:
            pass
        else:
            break

    # Split real name (which is optional) and email address parts
    sender_name, sender_addr = parseaddr(sender)
    recipient_name, recipient_addr = parseaddr(recipient)

    # We must always pass Unicode strings to Header, otherwise it will
    # use RFC 2047 encoding even on plain ASCII strings.
    sender_name = str(Header(unicode(sender_name), header_charset))
    recipient_name = str(Header(unicode(recipient_name), header_charset))

    # Make sure email addresses do not contain non-ASCII characters
    sender_addr = sender_addr.encode('ascii')
    recipient_addr = recipient_addr.encode('ascii')

    # Create the message ('plain' stands for Content-Type: text/plain)
    msg = MIMEText(body.encode(body_charset), 'plain', body_charset)
    msg['From'] = formataddr((sender_name, sender_addr))
    msg['To'] = formataddr((recipient_name, recipient_addr))
    msg['Subject'] = Header(unicode(subject), header_charset)

    # Send the message via SMTP to localhost:25
    smtp = SMTP("localhost")
    smtp.sendmail(sender, recipient, msg.as_string())
    smtp.quit()
