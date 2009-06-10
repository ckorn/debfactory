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
from optparse import OptionParser
from configobj import ConfigObj
from urllib2 import Request, urlopen, URLError, HTTPError
from localaux import *
from db_model import *
from dpkg_control import *
from lockfile import *
from sqlalchemy.exceptions import InvalidRequestError

config_file = "%s/debfactory/etc/debfactory.conf" % os.environ['HOME']
config = ConfigObj(config_file)

# Load configuration
try:
	db_url = config['db_url']
except Exception:
	print "Configuration error"
	print `sys.exc_info()[1]`
	sys.exit(3)
    
Log = Logger()    


def import_repository(repository):
    # Get the base release file to check for available architectures
    Log.log("Importing repository: %s" % repository)
    (rep_archive, rep_release, rep_component) = repository.split()    
    main_release_file = "%s/dists/%s/Release" % (rep_archive, rep_release)
    Log.log("Downloading %s" % main_release_file)
    try:
        f = urllib2.urlopen(main_release_file)
    except HTTPError, e:
        print "Error %s : %s" % (e.code, main_release_file)    
        return
    base_release = DebianControlFile(contents = f.read())    
    f.close()
    
    # Now let's import the Packages file for each architecture
    for arch in base_release['Architectures'].split():
        arch_release_file = "%s/dists/%s/%s/binary-%s/Release" \
            % (rep_archive, rep_release, rep_component, arch)
        Log.log("Downloading %s" % arch_release_file)
        try:
            f = urllib2.urlopen(arch_release_file)
        except HTTPError, e:
            print "Error: %s : %s" % (e.code, arch_release_file)    
            continue
        release = DebianControlFile()    
        release.load_contents(contents = f.read())
        f.close()
        archive = release['Archive']
        version = release['Version']
        component = release['Component']        
        origin = release['Origin']
        label = release['Label']
        architecture = release['Architecture']
        description = release['Description']        
        try:
            packagelist = PackageList.query.filter_by( \
                archive = archive, \
                version = version, \
                component = component, \
                architecture = architecture).one()
        # If we get "No rows returned for one()" insert it
        except InvalidRequestError:
            packagelist = PackageList( \
                archive = archive, \
                version = version, \
                component = component, \
                origin = release['Origin'], \
                label = release['Label'], \
                architecture = release['Architecture'], \
                description = release['Description'], \
                )
            pass
        packages_file = "%s/dists/%s/%s/binary-%s/Packages.gz" \
            % (rep_archive, rep_release, rep_component, arch)
        import_packages_file(packagelist, packages_file)


def import_packages_file(packagelist, packages_file):
    """
        Imports packages information from a packages file
    """
    Log.log("Downloading %s" % packages_file)
    try:
        f = urllib2.urlopen(packages_file)
    except HTTPError, e:
        return "%s : %s" % (e.code, packages_file)
    data = f.read()
    f.close()      
    
    # Decompress the file contents
    tmpfile = tempfile.NamedTemporaryFile(delete = False)
    tmpfile.write(data)
    tmpfile.close()
    f=gzip.open(tmpfile.name)
    data=f.read()
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
        package = Package.query.filter_by( \
                package = package_name, \
                version = version, \
                architecture = architecture).first()
        if not package:
            Log.print_("Inserting %s %s %s %s" % (package_name, source \
                , version, architecture))
            package = Package( 
                package = package_name, \
                source = source, \
                version = version, \
                architecture = architecture)                     
        # Create relation if needed
        if not packagelist in package.lists:
            Log.print_("Including %s -> %s" % (package, packagelist))
            package.lists.append(packagelist)
        # Add to in memory list to skip removal
        packages.append("%s %s %s" % 
            (package.package, package.version, package.architecture))            
    # Remove all relations to packages which were not import
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
    
    
def main():
    parser = OptionParser()
    parser.add_option("-q", "--quiet",
        action="store_false", dest="verbose", default=True,
        help="don't print status messages to stdout")
    parser.add_option("-t", "--create-tables",
        action="store_true", dest="create_tables", default=False,
        help="create the databas etables")        
    parser.add_option("-s", "--sql-echo",
        action="store_true", dest="sql_echo", default=False,
        help="echo the sql statements")                
    (options, args) = parser.parse_args()

    
    if len(args) > 2:
        repository = ' '.join(args)
    else:
        repository = 'http://www.getdeb.net/getdeb jaunty-getdeb-testing apps'
        
    Log.verbose=options.verbose	    
    try:
        lock = LockFile("apt2sql")
    except LockFile.AlreadyLockedError:
        Log.log("Unable to acquire lock, exiting")
        return
    metadata.bind = db_url        
    metadata.bind.echo = options.sql_echo    
    #setup_all(options.create_tables)
    setup_all(True)
    
    import_repository(repository)
    #PackageList.query.all()
    #for p in Package.query.filter_by(package='pidgin').all():
    #    print p.lists

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print 'User requested interrupt'
		sys.exit(1)

