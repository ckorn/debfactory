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
  This script will check the pre_build directory for packages that need
  to be build.
  When a *_source.changes is found, it's contents are verified, files
  are copied to /tmp/release-build and sbuild is called to build the
  package.
  
  The build result is sent via email to the sign author.
  A lock file is used to prevent concurrent runs		
  
"""
import os
import sys
import time
import datetime
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
    pre_build_dir = config['pre_build_dir']
    post_build_dir = config['post_build_dir']
    logs_dir = config['logs_dir']
    base_url = config['base_url']
except Exception:
	print "Configuration error"
	print `sys.exc_info()[1]`
	sys.exit(3)

Log = Logger()

def check_pre_build_dir():
	"""
	Check the pre build directory for release directories
	"""	
	file_list = glob.glob("%s/*" \
		% (pre_build_dir))
	for file in file_list:
		if os.path.isdir(file):
			release = os.path.basename(file)
			check_release_dir(release)
	
def check_release_dir(release):
	"""
	Check a release directory for components
	"""
	file_list = glob.glob("%s/%s/*" \
		% (pre_build_dir, release))	
	for file in file_list:
		if os.path.isdir(file):
			component = os.path.basename(file)
			check_release_component_dir(release, component)
            
def check_release_component_dir(release, component):
	""" 
	Check a release/component directory
		*_source.changes will triger a verification/build action
	"""
	Log.log("Checking %s/%s" % (release, component))
	file_list = glob.glob("%s/%s/%s/*_source.changes" \
		% (pre_build_dir, release, component))
		
	for fname in file_list:
		check_source_changes(release, component \
            , os.path.basename(fname))
            
	Log.log("Done")

def check_source_changes(release, component, filename):
    """	
    Check a _source.changes file and proceed as described in the script
    action flow . 
    """
    target_mails = [archive_admin_email]
    Log.print_("Building %s/%s/%s" % (release, component, filename))	
    
    source_dir = "%s/%s/%s" \
        % (pre_build_dir, release, component)	    
    destination_dir = "/tmp/build-%s-%s" % (release, component)    
    changes_file = "%s/%s" % (source_dir, filename)
    
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir, 0755)

    control_file = DebianControlFile("%s/%s" % (source_dir, filename))
    gpg_sign_author = control_file.verify_gpg(os.environ['HOME'] \
        +'/debfactory/keyrings/uploaders.gpg ', Log.verbose)

    if not gpg_sign_author:
        Log.print_("ERROR: Unable to verify GPG key for %s" % changes_file)
        return
        
    report_title = "%s/%s/%s build FAILED\n" \
        % (release, component, filename)
        
    try:		
        control_file.copy(destination_dir)        
    except DebianControlFile.MD5Error as e:
        report_msg = "MD5 mismatch: Expected %s, got %s, file: %s\n" \
            % (e.expected_md5, e.found_md5, e.name)	
        Log.print_(report_msg)
        send_mail_message(target_mails, report_title, report_msg)
        control_file.remove()
        return
    except DebianControlFile.FileNotFoundError as e:
        report_msg = "File not found: %s\n" % (e.filename)			
        Log.print_(report_msg)
        send_mail_message(target_mails, report_title, report_msg)
        control_file.remove()
        return
    dsc_file = "%s/%s_%s.dsc" \
        % (destination_dir, control_file['Source'] \
        , control_file.version())        
    if not os.path.exists(dsc_file):
        report_msg = ".dsc file not found: %s\n" % (dsc_file)
        Log.print_(report_msg)
        send_mail_message(target_mails, report_title, report_msg)
        control_file.remove()
        return
    
    # Remove previous failed status
    if os.path.exists('%s.failed' % changes_file):
        os.unlink('%s.failed' % changes_file)
        
    version = control_file.version()     
    os.chdir(destination_dir)
    i386_rc = sbuild_package(release, component, control_file, 'i386',  gpg_sign_author)
    if i386_rc == 0:
        sbuild_package(release, component, control_file, 'amd64',  gpg_sign_author)
        control_file.remove()
    else:
        shutil.move(changes_file ,  "%s.failed" %  changes_file)
        
def sbuild_package(release, component, control_file, arch, gpg_sign_author):
    """Attempt to build package using sbuild """        
    
    target_mails = [archive_admin_email,  gpg_sign_author]      
    name_version = "%s_%s" % (control_file['Source']
        , control_file.version())
    dsc_file = "%s.dsc" % name_version
    destination_dir = "%s/%s/%s" % (post_build_dir,  release,  component)        
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir, 0755)                        
    print "Building: %s" % dsc_file
    log_name = "%s_%s_%s.log" % (control_file['Source'] \
        , datetime.datetime.now().strftime("%Y_%M_%d_%m_%s"), arch)        
    start_time = time.time()
    if arch == "i386":
        arch_str = "i386 -A"
        arch_list = ['i386','all']
    else:
        arch_str = arch
        arch_list = ['amd64']
    rc = os.system('sbuild -d %s -c %s.%s %s' % 
        (release, release, arch_str, dsc_file))
    log_filename = "%s/%s" % (logs_dir, log_name)
    shutil.copyfile('current', log_filename)    
    elapsed_time = `int(time.time() - start_time)`
    report_msg = "List of files:\n"	
    report_msg += "--------------\n"
    if rc==0:
        status = "SUCCESSFUL"
        for arch_str in arch_list:
            # We really need the "./" because we have no base dir
            arch_changes = "./%s_%s.changes" % (name_version,  arch_str)
            report_title = "Build: %s/%s/%s (%s) %s\n" \
                % (release, component, name_version, arch, "FAILED")
            if os.path.exists(arch_changes):
                changes_file = DebianControlFile(arch_changes)
                file_list = changes_file.files_list()
                for file_info in file_list:
                    report_msg += "%s (%s) MD5: %s \n" \
                        % (file_info.name, file_info.size, file_info.md5sum)                
                try:
                    changes_file.move(destination_dir)
                except DebianControlFile.MD5Error as e:
                    report_msg = "MD5 mismatch: Expected %s, got %s, file: %s\n" \
                        % (e.expected_md5, e.found_md5, e.name)	
                    Log.print_(report_msg)
                    send_mail_message(target_mails, report_title, report_msg)
                    return
                except DebianControlFile.FileNotFoundError as e:
                    report_msg = "File not found: %s" % (e.filename)			
                    Log.print_(report_msg)
                    send_mail_message(target_mails, report_title, report_msg)
                    return			
                finally:
                    changes_file.remove()
    else:
        status = "FAILED"
    report_title = "Build: %s/%s/%s (%s) %s\n" \
        % (release, component, name_version, arch, status)
    report_msg += "\nElapsed Time: %s second(s)\n" % elapsed_time        
    report_msg += "Log file: %s%s\n" %  (base_url,  log_filename)
    Log.print_(report_title)
    send_mail_message(target_mails, report_title, report_msg)	
    return rc
    
def main():

	parser = OptionParser()
	parser.add_option("-q", "--quiet",
		action="store_false", dest="verbose", default=True,
        help="don't print status messages to stdout")
	(options, args) = parser.parse_args()
	Log.verbose=options.verbose	
	try:
		lock = LockFile("build")
	except LockFile.AlreadyLockedError:
		Log.log("Unable to acquire lock, exiting")
		return
	
	# Check and process the incoming directoy
	check_pre_build_dir()
    
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)
