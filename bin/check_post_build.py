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
    target_mails = archive_admin_email.split(",")
    Log.print_("Including %s/%s/%s" % (release, component, filename))	
        
    source_dir = "%s/%s/%s" \
        % (post_build_dir, release, component)
    changes_file = "%s/%s" % (source_dir, filename)
                    
    # Remove previous failed status
    if os.path.exists('%s.failed' % changes_file):
        os.unlink('%s.failed' % changes_file)
    control_file = DebianControlFile(changes_file)

    #gpg_sign_author = control_file.verify_gpg(os.environ['HOME'] \
    #    +'/debfactory/keyrings/uploaders.gpg ', Log.verbose)
    #
    #if not gpg_sign_author:
    #    Log.print_("ERROR: Unable to verify GPG key for %s" % changes_file)
    #    return

    name = control_file['Source'] 
    version = control_file.version()
    name_version = "%s_%s" % (control_file['Source'] \
        , control_file.version())

    report_title = "Include on testing for %s/%s/%s FAILED\n" \
        % (release, component, name_version)
    report_msg = "File: %s/%s/%s\n" % (release, component, filename)
    report_msg  += '-----------------\n'

    #target_mails.append(control_file['Changed-By'])    
    report_msg  += "Signed By: %s\n\n" % control_file['Changed-By']

    # Get list of files described on the changes	
    report_msg += "List of files:\n"	
    report_msg += "--------------\n"
    file_list = control_file.files_list()
    for file_info in file_list:
        report_msg += "%s (%s) MD5: %s \n" \
            % (file_info.name, file_info.size, file_info.md5sum)		
    
    # Remove all packages related to source package
    if(filename.endswith("_source.changes")):
        os.system("reprepro removesrc %s-getdeb-testing %s %s" 
            % (release, name,  version))    
    # Include the package
    command = "reprepro -C %s include %s-getdeb-testing %s" \
        % (component,  release, changes_file)
    (rc, output) = commands.getstatusoutput(command)
    print output
    report_msg += output
    if rc==0:
        status = "SUCCESSFUL"
        control_file.remove()
    else:
        status = "FAILED"
        shutil.move(changes_file, "%s.failed" % changes_file)
        
        
    report_title = "Included on testing %s/%s/%s %s\n" \
        % (release, component, name_version, status)    
    Log.print_(status)
    Log.print_(report_title)  
    message(target_emails, report_title, output)    

def check_post_build_dir():
	"""
	Check the ftp incoming directory for release directories
	"""	
	file_list = glob.glob("%s/*" \
		% (post_build_dir))
	for file in file_list:
		if os.path.isdir(file):
			release = os.path.basename(file)
			check_release_dir(release)
	
def check_release_dir(release):
	"""
	Check a release directory for components
	"""
	file_list = glob.glob("%s/%s/*" \
		% (post_build_dir, release))	
	for file in file_list:
		if os.path.isdir(file):
			component = os.path.basename(file)
			check_release_component_dir(release, component)
	
def check_release_component_dir(release, component):
	""" 
	Check a release/component directory
	"""
	Log.log("Checking %s/%s" % (release, component))
	file_list = glob.glob("%s/%s/%s/*.changes" \
		% (post_build_dir, release, component))
		
    # First we process _source.changes to make sure existing packages
    # will be deleted from the repository before the binaries include
	for fname in file_list:
		if fname.endswith("_source.changes"):
			check_changes(release, component, os.path.basename(fname))
            
	for fname in file_list:
		if not fname.endswith("_source.changes"):
			check_changes(release, component, os.path.basename(fname))
                        
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
	check_post_build_dir()
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)

