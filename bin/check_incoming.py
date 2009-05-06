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
  This script will check the ftp incoming directoy for debian source
  packages. 
  The expected structure is ftp_incoming_dir/release_name, 
    eg: /home/ftp/incoming/jaunty
  Files will be verified with the following rules
  Acquire exclusive lock incoming_lock_file, exit on failure
	For each release directory		
		Get list of files into filelist
		For every *_source.changes
			Create a sub list of files described on the _source.changes
			Append the _soure.changes to the sublist
			Verify GPG signature using ~/debfactory/keyrings/uploaders.gpg
			If GPG is ok, action=move else action=delete, log failure
			For each file on the sublist:
				Verify MD5
				If MD5 fails, action=delete, log md5 failure
			For each file on the sublist:
				Apply and log action 
			If GPG is ok, send email to GPG signer with the action log			
		For every file on filelist
			If file is older than 10s, try do delete it			
   Close and release lock /tmp/check_incoming.lock
"""
import os, sys, commands
import commands
from optparse import OptionParser
from localaux import *
import glob
import dpkg

ftp_incoming_dir = '/home/ftp/incoming'
pre_build_dir = "/build/pre_build"
incoming_lock_file = '/tmp/check_incoming_lock_file.lock'

gpg_ops = '--no-options --no-default-keyring --keyring '+os.environ['HOME']+'/debfactory/keyrings/uploaders.gpg '
os.putenv('LANG', 'C') # We check system command replies, use a reliable language

Log = Logger()	

def check_source_changes(changes_file):
	"""	
	Check a _source.changes file and proceed as described in the script
	action flow . 
	"""
	Log.log("Checking "+changes_file)	
	(rc, output) = commands.getstatusoutput('gpg '+gpg_ops+' --verify --logger-fd=1 '+changes_file)
	output_lines = output.split("\n")
	sign_author = None
	for line in output_lines:		
		if line.startswith("gpg: Good signature from"):
			print line
			dummy, sign_author, dummy = line.split('"')	
	if rc<>0 or sign_author==None:
		print "ERROR: Unable to verify GPG key for ",changes_file		
		return
	file_list = dpkg.get_files_list(changes_file)		
	base_dir = os.path.dirname(changes_file)
	for file in file_list:
		filename = base_dir+"/"+file[4]
		if not os.path.exists(filename):
			print 'ERROR: Could not find '+filename+" listed at ", changes_file
			#send_error("err_file", package, sign_author)
			return
		md5sum = check_md5sum(filename, file[0])
		if md5sum:
			print 'ERROR: File '+filename,+' has md5sum '+md5sm+' expected '+file[0]
			return			
	orig_file = dpkg.getOrigTarGzName(changes_file)
	
	if not orig_file:
		return
	if os.path.exists(base_dir+"/"+orig_file):
		file_list.append(orig_file)
	else:
		if not os.path.exists(pre_build_dir+"/"+orig_file):
			print 'ERROR: Missing  '+orig_file+' for '+changes_file		
			return
		else:
			Log.log('No orig.tar.gz, using the one already available '+ base_dir+"/"+orig_file)
			
	# Source package passed all tests, let's move it to pre_build	
	for file in uniq(ile_list):
		print 'Moving ',base_dir+"/"+file,'->',pre_build_dir
		try:
			shutil.move(base_dir+"/"+file, pre_build_dir)
		except:
			print "FAILED: "+`sys.exc_info()[1]`
			return
				
def check_release_dir(releasedir):
	""" 
	Check a release directory and proceed as described in the script
	action flow . 
	"""
	Log.log("Checking "+releasedir)
	file_list = glob.glob(releasedir+"/*")
	change_list = []
	for fname in file_list:
		if fname.endswith("_source.changes"):
			check_source_changes(fname)	
	
def main():
	parser = OptionParser()
	parser.add_option("-q", "--quiet",
		action="store_false", dest="verbose", default=True,
        help="don't print status messages to stdout")
	(options, args) = parser.parse_args()
	Log.verbose=options.verbose
	
	lock = LockFile(Log, incoming_lock_file)
	
	# Get list of releases
	releases = glob.glob(ftp_incoming_dir+'/[a-z]*')
	for release in releases:
		check_release_dir(release)
	# Release the lock file
	lock.Close()
			
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)

