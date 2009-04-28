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

#  Validate all .changes from a given release
#   - Verify we can validate the signature
#   - Validate md5 of the include files
#   - Move related files to ~/var/prebuild
import sys
import glob
import os
import string
import shutil
import smtplib

prebuilddir = os.environ['HOME']+'/abs/pre_build'
build_package = os.environ['HOME']+'/debfactory/bin/build_package.py'

def send_email(toaddrs, message):
    fromaddr = "GetDeb Automated Builder <autobuild@getdeb.net>"
    server = smtplib.SMTP('localhost')
    server.sendmail(fromaddr, toaddrs, message)
    server.quit()

if len(sys.argv) != 2:
  print "Usage: "+sys.argv[0]+" release"
  sys.exit(2)

release=sys.argv[1]

if os.path.exists('/tmp/build_'+release+'.lock'):
  print "Another build is still running: /tmp/build_"+release+".lock"
  sys.exit(3)

open('/tmp/build_'+release+'.lock', 'w')

release=sys.argv[1]
prebuilddir += '/'+release
print "--- Checking prebuild files for", release
packages=glob.glob(prebuilddir+"/*_source.changes")
for package in packages:
  print package
  if os.path.exists(package+'.failed'):
	print "Warning: Skipping "+package+'.failed'
	continue
  os.system(build_package+' '+release+' '+package);
print "Done"

os.unlink('/tmp/build_'+release+'.lock')
