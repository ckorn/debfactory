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
"""
  This script will check the post_build directory
  When *_.changes is found, it's contents are verified and
  the files are included in the testing_repository
  
  The expected structure is post_build dir/release/component 
  
  Files will be verified with the following rules
		...		
  A lock file is used to prevent concurrent runs		
"""
import os
import sys
import time
import glob
from optparse import OptionParser
from configobj import ConfigObj
from localaux import *
from dpkg_control import *
from lockfile import *

config_file = "%s/debfactory/etc/debfactory.conf" % os.environ['HOME']
config = ConfigObj(config_file)

# Load configuration
try:
	archive_admin_email = config['archive_admin_email']	
	post_build_dir = config['post_build_dir']
except Exception:
	print "Configuration error"
	print `sys.exc_info()[1]`
	sys.exit(3)

Log = Logger()	

def check_changes(release, component, filename):
    """	
    Check a _.changes file and include it into the repository
    """
    target_mails = [archive_admin_email]
    Log.print_("Including %s/%s/%s" % (release, component, filename))	
        
    source_dir = "%s/%s/%s" \
        % (ftp_post_build_dir, release, component)
    changes_file = "%s/%s" % (source_dir, filename)
                
    control_file = DebianControlFile("%s/%s" % (source_dir, filename))

    gpg_sign_author = control_file.verify_gpg(os.environ['HOME'] \
        +'/debfactory/keyrings/uploaders.gpg ', Log.verbose)

    if not gpg_sign_author:
        Log.print_("ERROR: Unable to verify GPG key for %s" % changes_file)
        return

    name = control_file['Source'] 
    version = control_file.version()
    name_version = "%s_%s" % (control_file['Source'] \
        , control_file.version())

    report_title = "Include on testing for %s/%s/%s FAILED\n" \
        % (release, component, name_version)
    report_msg = "File: %s/%s/%s\n" % (release, component, filename)
    report_msg  += '-----------------\n'

    target_mails.append(gpg_sign_author)
    report_msg  += "Signed By: %s\n\n" % gpg_sign_author

    # Get list of files described on the changes	
    report_msg += "List of files:\n"	
    report_msg += "--------------\n"
    file_list = control_file.files_list()
    for file_info in file_list:
        report_msg += "%s (%s) MD5: %s \n" \
            % (file_info.name, file_info.size, file_info.md5sum)		
            
    if(filename.endswith("_source.changes")):
            os.system("reprepro removesrc %s %s" % (name,  version))
        rc = os.system("reprepro include -C %s %s-testing %s"
                  % (component,  release, changes_file))        
    report_title = "Include on testing %s/%s/%s SUCCESSFUL\n" \
        % (release, component, name_version)
    Log.print_(report_title)
    send_mail_message(target_mails, report_title, report_msg)	

def check_incoming_dir():
	"""
	Check the ftp incoming directory for release directories
	"""	
	file_list = glob.glob("%s/*" \
		% (ftp_incoming_dir))
	for file in file_list:
		if os.path.isdir(file):
			release = os.path.basename(file)
			check_release_dir(release)
	
def check_release_dir(release):
	"""
	Check a release directory for components
	"""
	file_list = glob.glob("%s/%s/*" \
		% (ftp_incoming_dir, release))	
	for file in file_list:
		if os.path.isdir(file):
			component = os.path.basename(file)
			check_release_component_dir(release, component)
	
def check_release_component_dir(release, component):
	""" 
	Check a release/component directory
		*_source.changes will triger a verification/move action
		files older than CLEANUP_TIME will be removed
	"""
	Log.log("Checking %s/%s" % (release, component))
	file_list = glob.glob("%s/%s/%s/*" \
		% (ftp_incoming_dir, release, component))
		
	for fname in file_list:
		if not os.path.exists(fname): # File was removed ???
			continue
		if fname.endswith("_source.changes"):
			check_source_changes(release, component, os.path.basename(fname))	
			# There could be an error, remove it anyway
			if os.path.exists(fname):
				os.unlink(fname)
		else:
			if time.time() - os.path.getmtime(fname) > CLEANUP_TIME:
				print "Removing old file: %s", fname
				os.unlink(fname)
	Log.log("Done")
	
def main():
	
	parser = OptionParser()
	parser.add_option("-q", "--quiet",
		action="store_false", dest="verbose", default=True,
        help="don't print status messages to stdout")
	(options, args) = parser.parse_args()
	Log.verbose=options.verbose	
	try:
		lock = LockFile("ftp_incoming")
	except LockFile.AlreadyLockedError:
		Log.log("Unable to acquire lock, exiting")
		return
	
	# Check and process the incoming directoy
	check_incoming_dir()
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)

