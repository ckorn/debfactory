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
  When *_source.changes is found, it's contents are verified and
  the files are moved to the pre_build queue.
  
  The expected structure is ftp_incoming_dir/release_name, 
    eg: /home/ftp/incoming/jaunty
  
  Files will be verified with the following rules
	For each release directory		
		Get list of files into filelist
		...
		
   We use a file lock to aboid paralell runs		
  
"""
import os, sys, commands, shutil
import commands
from optparse import OptionParser
from configobj import ConfigObj
from localaux import *
import glob
import dpkg
import time

config_file = "%s/debfactory/etc/debfactory.conf" % os.environ['HOME']
config = ConfigObj(config_file)

# Load configuration
try:
	upload_status_email = config['upload_status_email']
	ftp_incoming_dir = config['ftp_incoming_dir']
	pre_build_dir = config['pre_build_dir']
except:
	print "Configuration error"
	print `sys.exc_info()[1]`
	sys.exit(3)
	
incoming_lock_file = '/tmp/check_incoming_lock_file.pid'

# Clean up all files older than 24h
CLEANUP_TIME = 24*3600

gpg_ops = '--no-options --no-default-keyring --keyring '+os.environ['HOME']+'/debfactory/keyrings/uploaders.gpg '
os.putenv('LANG', 'C') # We check system command replies, use a reliable language

Log = Logger()	

def check_source_changes(changes_file, release):
	"""	
	Check a _source.changes file and proceed as described in the script
	action flow . 
	"""
	target_mails = [upload_status_email]
	Log.log("Checking "+changes_file)	
	report_msg = "File: %s\n" % changes_file
	report_msg  += '-----------------\n'
	(rc, output) = commands.getstatusoutput('gpg '+gpg_ops+' --verify --logger-fd=1 '+changes_file)	
	output_lines = output.split("\n")
	sign_author = None
	for line in output_lines:		
		if line.startswith("gpg: Good signature from"):
			print line
			dummy, sign_author, dummy = line.split('"')	
	if rc<>0 or not sign_author:
		print output
		print "ERROR: Unable to verify GPG key for ", changes_file				
		return
	target_mails.append(sign_author)
	report_msg  += "Signed By: %s\n" % sign_author

		
	# Get list of files described on the changes
	report_title = "%s upload FAILED\n" % os.path.basename(changes_file)
	report_msg += "List of files:\n"	
	report_msg += "--------------\n"
	file_list = dpkg.get_files_list(changes_file)		
	base_dir = os.path.dirname(changes_file)
	
	filename_list = []	
	
	# Check if orig_file is available
	orig_file = dpkg.getOrigTarGzName(changes_file)	
	if not orig_file:		
		return
					
	if os.path.exists("%s/%s" % (base_dir, orig_file)):
		filename_list.append("%s/%s" % (base_dir,orig_file))
	else:
		if not os.path.exists("%s/%s/%s" % (pre_build_dir, release, orig_file)):
			print "ERROR: Missing %s for %s" % (orig_file, changes_file)
			report_msg += "ERROR: Missing %s for %s\n" % (orig_file, changes_file)
			send_mail_message(target_mails, report_title, report_msg)
			return
		else:
			Log.log('No orig.tar.gz, using the one already available '+ base_dir+"/"+orig_file)
	
	for file in file_list:
		report_msg += "%s - " % file[4]		
		filename = base_dir+"/"+file[4]
		filename_list.append(filename)		
		if not os.path.exists(filename):
			print 'ERROR: Could not find '+filename+" listed at ", changes_file			
			#send_error("err_file", package, sign_author)
			report_msg += "Missing\n"			
			send_mail_message(target_mails, report_title, report_msg)
			return
		md5sum = check_md5sum(filename, file[0])
		if md5sum:
			print md5sum
			print 'ERROR: File %s md5sum is %s, expected %s' % (filename, md5sum, file[0])
			report_msg += "MD5 mismatch\n"
			send_mail_message(target_mails, report_title, report_msg)
			return			
		report_msg += "OK\n"		

	# Source package passed all tests, let's move it to pre_build		
	target_dir = "%s/%s" % (pre_build_dir, release)
	if not os.path.exists(target_dir):
		os.mkdir(target_dir)
	for file in uniq(filename_list):
		print 'Moving ', file,'-> '+target_dir
		if os.path.exists("%s/%s" % (target_dir, os.path.basename(file))):
			os.unlink("%s/%s" % (target_dir, os.path.basename(file)))
		try:
			shutil.move(file, target_dir)
		except:
			print "FAILED: "+`sys.exc_info()[1]`
			return
			
	report_title = "%s upload SUCCESSFUL\n" % os.path.basename(changes_file)
	send_mail_message(target_mails, report_title, report_msg)	
				
def check_release_dir(releasedir):
	""" 
	Check a release directory and proceed as described in the script
	action flow . 
	"""
	Log.log("Checking "+releasedir)
	file_list = glob.glob(releasedir+"/*")
	release = os.path.basename(releasedir)
	change_list = []
	for fname in file_list:
		if fname.endswith("_source.changes"):
			check_source_changes(fname, release)	
			os.unlink(fname)
		else:
			if time.time() - os.path.getmtime(fname) > CLEANUP_TIME:
				print "Removing old file: %s", fname
				try:
					os.unlink(fname)
				except:
					print "FAILED: "+`sys.exc_info()[1]`			
	Log.log("Done")
	
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
			
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)

