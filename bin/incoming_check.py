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
import dpkg

prebuilddir = os.environ['HOME']+'/abs/pre_build'
incomingdir = '/home/ftp/incoming'
ready_dir=os.environ['HOME']+'/abs/post_build'

def send_error(error, package, dest):
  message = "Subject: Package Upload Failure - "+os.path.basename(package)+"\n\n"
  if error=="err_source":
    message += "You have uploaded "+package+"\n"
    message += "We need to build from a  _sources.changes file\n"
    message += "Generate a source changes file with: debuild -S -sa\n"
  elif error=="err_md5":
    message += "There as a md5sum mismatch on one of your files, please repeat the upload\n\n"
  elif error=="err_orig":
    message += "There is no orig.tar.gz file on the package, an orig.tar.gz file must be provided\n"
    message += "Then generate a source changes file with: debuild -S -sa\n\n"
  elif error=="err_file":
    message += "A file described on the changes file is missing, please try uploading\n\n"
  else:
    print "Fatal error, missing error code on send_error()"
    sys.exit(3)
  send_email(dest, message)

def send_email(toaddrs, message):
    fromaddr = '"GetDeb Automated Builder" <autobuild@getdeb.net>'
    server = smtplib.SMTP('localhost')
    server.sendmail(fromaddr, toaddrs, message)
    server.quit()

if len(sys.argv) != 2:
  print "Usage: "+sys.argv[0]+" release"
  sys.exit(2)

#os.system('sudo /home/build/sbin/incoming_chown.sh')

release=sys.argv[1]
incomingdir += '/'+release
prebuilddir += '/'+release
ready_dir += '/'+release
print "--- Checking incoming files for", release
packages=glob.glob(incomingdir+"/*.changes")
for package in packages:
  print package
  pgrep=os.popen('grep "Changed-By:" '+package,'r')
  author_line=pgrep.readline().strip('\r\n')
  if not author_line:
	pgrep.close()
	pgrep=os.popen('grep "Maintainer:" '+package,'r')
  	author_line=pgrep.readline().strip('\r\n')
  pgrep.close()
  dummy, change_author = author_line.split(":")
  pcheck=os.popen('gpg --verify --logger-fd=1 '+package)
  lines = pcheck.readlines()
  sign_author = None
  for line in lines:
    if line.find("gpg: Good signature from") != -1:
	dummy, sign_author, dummy = line.split('"')
  if not sign_author:
    print "Unsucessfull key validation"
    shutil.move(package, package+".failed")
    continue
  rc=pcheck.close()
  if rc != None:
    print "Failed security check"
    os.unlink(package)
    continue
  if package.find("_source.changes") == -1 :
    print "Skipping non source .changes", package
    send_error("err_source", package, sign_author)
    os.unlink(package)
    continue
  file_list = dpkg.get_files_list(package)
  orig_file = None
  skip_package = None
  for file in file_list:
     if file[4].find('orig.tar.gz') != -1: orig_file = file[4]
     filename = incomingdir+"/"+file[4]
     if not os.path.exists(filename):
        print "Skipping "+package+", file missing "+filename
        send_error("err_file", package, sign_author)
	skip_package = 1 ; continue
     md5pipe = os.popen('md5sum '+filename,"r")
     md5 = md5pipe.readline()
     (newmd5, dummy) = string.split(md5)
     newmd5 = newmd5.strip('\r\n')
     if newmd5 != file[0]:
	print "Integrity error!"
     	print "MD5 Mismatch:", file[4], file[0], newmd5
        send_error("err_md5", package, sign_author)
	skip_package = 1 ; continue
  if skip_package:
    os.unlink(package)
    continue

  if not orig_file:
    orig_file = dpkg.getOrigTarGzName(package)
    if not os.path.exists(ready_dir+"/"+orig_file):
      if not os.path.exists(prebuilddir+"/"+orig_file):
        print "Skipping "+package+" without a .orig.tar.gz file"
        os.unlink(package)
        send_error("err_orig", package, sign_author)  
        continue
      else:
        print prebuilddir+"/"+orig_file,' already exists'
    else:
      print 'Moving ',ready_dir+"/"+orig_file,'->',prebuilddir
      shutil.move(ready_dir+"/"+orig_file, prebuilddir)
	
  for file in file_list:
    print 'Moving ',incomingdir+'/'+file[4],'->',prebuilddir
    shutil.move(incomingdir+'/'+file[4], prebuilddir)
  shutil.move(package, prebuilddir)
  if os.path.exists(prebuilddir+"/"+os.path.basename(package)+".failed"):
    os.unlink(prebuilddir+"/"+os.path.basename(package)+".failed")
  message = "Subject: Package Upload Success - "+os.path.basename(package)
  message += "\n\nYour package was succesfully uploaded for "+release
  send_email(sign_author, message)

#os.system('sudo /home/build/sbin/incoming_unchown.sh')

print "Done"

