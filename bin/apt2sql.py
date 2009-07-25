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
#  This file provides several functions to handle debian packages
#  control files.

"""
Usage:
    apt2sql.py [--database mysql://user:password@localhost/apt2sql] \
        [archive_root_url suite [component1[, component2] ]]
        
Example:
    apt2sql.py http://archive.ubuntu.com/ubuntu jaunty
    
"""

# sqlalchemy uses a deprecated module
import warnings
warnings.simplefilter("ignore",DeprecationWarning)

import sys
import os
import socket
import urllib2
import zlib
import gzip
import tempfile
import re
from datetime import datetime
from optparse import OptionParser
from urllib2 import Request, urlopen, URLError, HTTPError
from localaux import *
from packages_model import *
from dpkg_control import *
from lockfile import *
    
Log = Logger()
#global force_rpool
force_rpool = False

	
def get_last_mofified_time(file_url):
	"""
	Returns the last mofidifed time for the specified url
	"""
	try:
		f = urllib2.urlopen(file_url)
	except HTTPError, e:        
		log.print_("Error %s : %s" % (e.code, file_url))
		return None	
	last_modified = f.info()['Last-Modified']		
	f.close()	
	d_last_modified = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
	return d_last_modified	
	
def import_repository(archive_url, suite, requested_components \
        , requested_architectures):
	"""
	Import a repository into the dabase
	"""
	# Get the base release file to check the list of available 
	# architectures and components
	Log.log("Importing repository: %s %s [%s] [%s]" \
		% (archive_url, suite, requested_components or "all" \
			, requested_architectures or "all"))
	release_file = "%s/dists/%s/Release" % (archive_url, suite)
	Log.log("Downloading %s" % release_file)
	try:
		f = urllib2.urlopen(release_file)
	except HTTPError, e:        
		print "Error %s : %s" % (e.code, release_file)    
		return 1
	Release = DebianControlFile(contents = f.read())    
	f.close()

	architectures = Release['Architectures'].split()
	components = Release['Components'].split()
	Log.log ("Available architectures: %s" % architectures)
	Log.log ("Available components: %s" % components)

	# Check if the requested components are available
	if requested_components:
		for component in requested_components[:]:
			if component not in components:
				Log.print_("Requested unavailable component %s" 
					% component)
				return 2 

	# Check if the requested architectures are available
	if requested_architectures:
		for architecture in requested_architectures[:]:
			if architecture not in architectures:
				Log.print_("Requested unavailable architecture" \
					, architecture)
				return 2 
				
	components = requested_components or components
	architectures = requested_architectures or architectures
	version = Release['Version'] or suite
    
	# Now let's import the Packages file for each architecture
	for arch in architectures:
		for component in components:
			packagelist = \
				PackageList.query.filter_by( \
					suite = suite, \
					version = version, \
					component = component, \
					architecture = arch).first() \
				or \
				PackageList( \
					suite = suite, \
					version = version, \
					component = component, \
					origin = Release['Origin'], \
					label = Release['Label'], \
					architecture = arch, \
					description = Release['Description'], \
					date = Release['Date'] \
					)            
			packages_file = "%s/dists/%s/%s/binary-%s/Packages.gz" \
				% (archive_url, suite, component, arch)
			import_packages_file(archive_url, packagelist, packages_file)
			packagelist = None


def import_packages_file(archive_url, packagelist, packages_file):
	"""
        Imports packages information from a packages file
	"""
	global force_rpool	
	Log.log("Downloading %s" % packages_file)
	try:
		f = urllib2.urlopen(packages_file)
	except HTTPError, e:
		session.rollback() # Rollback the suite insert
		print "%s : %s" % (e.code, packages_file)
		return -1
	data = f.read()
	f.close()      
	
    # Decompress the file contents
	tmpfile = tempfile.NamedTemporaryFile(delete = False)
	tmpfile.write(data)
	tmpfile.close()
	f = gzip.open(tmpfile.name)
	data = f.read()
	f.close()
	os.unlink(tmpfile.name)
	packages = []
	
	for package_info in data.split("\n\n"):
		if not package_info: # happens at the end of the file
			continue
		control = DebianControlFile(contents = package_info)
		package_name = control['Package']
		source = control['Source']
		version = control['Version']
		architecture = control['Architecture']
		description = 	control['Description'][0]
		homepage = 	control['homepage']	
		package = Package.query.filter_by( \
			package = package_name, \
			version = version, \
			architecture = architecture).first()
		if not package: # New package			
			deb_filename = "%s/%s" % (archive_url, control['Filename'])
			if force_rpool:
				deb_filename = deb_filename.replace("pool", "rpool", 1)
			last_modified = get_last_mofified_time(deb_filename)
			Log.print_("Inserting %s %s %s %s" % (package_name, source \
				, version, architecture))
			package = Package( 
				package = package_name \
				, source = source \
				, version = version \
				, architecture = architecture \
				, last_modified = last_modified \
				, description = description \
				, homepage = homepage \
			)
		# Create relation if needed
		if not packagelist in package.lists:
			Log.print_("Including %s -> %s" % (package, packagelist))
			package.lists.append(packagelist)
		# Add to in memory list to skip removal
		packages.append("%s %s %s" % 
			(package.package, package.version, package.architecture))            
	# Remove all relations to packages which were not imported
	# on the loop above
	must_remove = []
	for package in packagelist.packages:
		list_item = "%s %s %s" % (package.package, package.version \
			, package.architecture)			
		try:
			packages.remove(list_item)
		except KeyError:
			Log._print("Removing %s" % `package`)
			must_remove.append(package)        
	for package in must_remove:
		packagelist.packages.remove(package)
	session.commit()
	del packages
	del data
	
	
def main():
	global force_rpool
	parser = OptionParser()
	parser.add_option("-d", "--database",
		action = "store", type="string", dest="database",
		help = "specificy the database URI\n\n" \
		"Examples\n\n" \
		"   mysql://user:password@localhost/apt2sql" \
		"   sqlite:///apt2sql.db" \
	)
	parser.add_option("-f", "--force-rpool",
		action = "store_true", dest="rpool", default=False,
		help = "force to use rpool path instead of pool")				
	parser.add_option("-q", "--quiet",
		action = "store_false", dest="verbose", default=True,
		help = "don't print status messages to stdout")
	parser.add_option("-r", "--recreate-tables",
		action = "store_true", dest="recreate_tables", default=False,
		help = "recreate db tables")            		
	parser.add_option("-s", "--sql-echo",
		action = "store_true", dest="sql_echo", default=False,
		help = "echo the sql statements")
	(options, args) = parser.parse_args()
	db_url = options.database or "sqlite:///apt2sql.db"
	if len(args) < 2:
		print "Usage: %s " \
			"archive_root_url suite [component1[, component2] ]" \
			% os.path.basename(__file__)
		sys.exit(2)

	archive_url = args[0]
	suite = args[1]
	components = None
	architectures = None
	if len(args) > 2:
		components = args[2].split(",")    
	if len(args) > 3:
		architectures = args[3].split(",")    

	Log.verbose = options.verbose	    
	force_rpool = options.rpool
	try:
		lock = LockFile("apt2sql")
	except LockFile.AlreadyLockedError:
		Log.log("Unable to acquire lock, exiting")
		return

	# We set the database engine here
	metadata.bind = db_url        
	metadata.bind.echo = options.sql_echo    
	setup_all(True)
	if options.recreate_tables:
		drop_all()
		setup_all(True)

	import_repository(archive_url, suite, components, architectures)
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)
