#!/usr/bin/python
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
