#!/usr/bin/python
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
import os
import sys
import commands
import smtplib
import atexit

def uniq(alist):
    set = {}
    return [set.setdefault(e,e) for e in alist if e not in set]

""" Small helper class for logging """
class Logger:
	def __init__(self, verbose=True):
		self.verbose = verbose
	def log(self, message):
		if self.verbose:
			print message	

		
""" Lock file management class"""
class LockFile:
	def __init__(self, Log, lock_filename):
		self.log = Log
		self.lock_filename = lock_filename
		if os.path.islink(lock_filename):
			print 'FATAL ERROR: symlink '+lock_filename
			sys.exit(2)
		#oflags = os.O_EXCL | os.O_RDWR |os.O_NONBLOCK| os.O_CREAT
		oflags = os.O_RDWR |os.O_NONBLOCK| os.O_CREAT | os.O_EXCL
		try:	
			self.lock_fd = os.open(lock_filename, oflags)
			os.write(self.lock_fd, "%d\n" % os.getpid())
		except:
			Log.log("Unable to acquire lock %s" % lock_filename)
			Log.log("FAILED: "+`sys.exc_info()[1]`)
			sys.exit(2)
		atexit.register(self.lock_remove, lock_filename, self.lock_fd)
	def lock_remove(self, fname, lock_fd):
		try:
			os.close(lock_fd)
			os.unlink(fname)
		except:
			pass

		
def check_md5sum(filename, expected_md5sum):
	"""
	"""
	md5sum=commands.getoutput('md5sum '+filename)
	(newmd5, dummy) = md5sum.split()
	#newmd5 = newmd5.strip('\r\n')
	if newmd5 != expected_md5sum:     	
		return newmd5
	return None

def send_email(toaddrs, message):
    fromaddr = '"GetDeb Automated Builder" <autobuild@getdeb.net>'
    server = smtplib.SMTP('localhost')
    server.sendmail(fromaddr, toaddrs, message)
    server.quit()
	
def send_mail_message(destination, subject, body):
	"""
	Sends a mail message
	"""
	
	message = "Subject: %s\n\n" % subject
	message += body
	if type(destination) is list:
		for dest in destination:
			send_email(dest, message)		
	else:
		send_email(destination, message)		
