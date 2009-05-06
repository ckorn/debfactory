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
Local auxiliary functions library
"""
import os
import sys

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
		Log.log('Acquiring lock on file ' + lock_filename)	

		oflags = os.O_WRONLY|os.O_NONBLOCK|os.O_CREAT
		try:	
			self.lock_fd = os.open(lock_filename, oflags, 0007)
		except:
			Log.log("FAILED: "+`sys.exc_info()[1]`)
			sys.exit(2)
	def Close(self):
		os.close(self.lock_fd)
		os.unlink(self.lock_filename)
		
def check_md5sum(filename, expected_md5sum):
	"""
	"""
	md5sum=commands.getoutput('md5sum '+filename,"r")
	(newmd5, dummy) = string.split(md5sum)
	#newmd5 = newmd5.strip('\r\n')
	if newmd5 != expected_md5sum:     	
		return newmd5
	return None
