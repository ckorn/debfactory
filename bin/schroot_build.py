#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   (C) Copyright 2006-2009, GetDeb Team - https://launchpad.net/~getdeb
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
#

# This script automates some of tasks required to build a schroot for
# testing and building purposes.
# The script flow is:
#	- Install on the pre-required packagfes like fakeroot, schroot, etc
#	- Debootstrap the system to the version specific by the user
#	- Copy core system config files from the main system to the schroot
#	- Customize the configuration (eg. point the repositories to the proxy)

# Change Log
#	7 Mar 2009
#		Use the minbase variant to produce smaller chroots images
#	2 Aug 2008
#		Added the GPL-3 notice

your_mirror = 'pt.archive.ubuntu.com'

available_releases = ("hardy", "intrepid","jaunty")
available_archs = ("i386", "amd64")

"""
helper chroot build script
"""
import os, sys, shutil;
import string;

print "\n###### Helper schroot build script\n"
# We need root
if os.getuid() != 0:
  print 'This script needs to be run as root/sudo !'
  sys.exit(2)

lang = os.environ['LANG']
os.putenv('LANG', 'C') # We use popen, set a safe language

def check_and_install_package(package):
	has_package=int(os.popen('dpkg -l '+package+' 2>&1 | grep -c "^ii"').read())
	if not has_package:
		print "Package "+package+" is not installed, it needs to be installed"
		install = ""
		while install not in ("y", "n"):
			install = raw_input('Install it now ? (y/n)')
			if install == "n":
				sys.exit(1);
		os.system('sudo apt-get install -y '+package)
	else:
		print "Package "+package+" was found"

def get_host_release():
	release = os.popen('lsb_release -c| cut -f2').read().strip("\r\n")
	return release

def check_dir(name):
	"""
	Check if a given directory exists, create if not
	"""
	if os.path.exists(name):
		print name+" was found"
	else:
		print "Creating directory "+name
		os.mkdir(name)

def copy_to_chroot(fname, chrootdir):
	print os.path.join("/"+fname)+" -> "+os.path.join(chrootdir,fname)
	shutil.copyfile(os.path.join("/"+fname),os.path.join(chrootdir,fname))

# Check requirements
def check_requirements():
	"""
	Check script requirements
	"""
	print "Checking requirements"
	# Check for universe respository
	universe_enabled = int(os.popen('grep -v "#" /etc/apt/sources.list | grep -c "universe"').read())
	if not universe_enabled:
		print "The universe repository must be enabled, check /etc/apt/sources.list !"
		sys.exit(2)
	print "Repository universe is enabled"
#	multiverse_enabled = int(os.popen('grep -v "#" /etc/apt/sources.list | grep -c "multiverse"').read())
#	if not multiverse_enabled:
#		print "The multiverse repository must be enabled, check /etc/apt/sources.list !"
#		sys.exit(2)
#	print "Repository multiverse is enabled"
	# Check for dhcroot and debootstrap
	check_and_install_package("schroot")
	check_and_install_package("debootstrap")
	print

def check_base_dir():
	base_dir = "/home/schroot"
	new_base_dir = raw_input("Please enter the chroot base dir\n["+base_dir+"]: ")
	basedir = new_base_dir or base_dir
	check_dir(basedir)
	return basedir

def check_chroot_release(basedir):
	base_release = get_host_release()
	baserelease = ""
	while baserelease not in available_releases:
		new_base_release = raw_input("Please enter the chroot distro version, options are: "+string.join(available_releases)+"\n["+base_release+"]: ")
		baserelease = new_base_release or base_release
	base_arch = "i386"
	basearch = ""
	while basearch not in available_archs:
		new_base_arch = raw_input("Please enter the chroot architecture, options are: "+string.join(available_archs)+"\n["+base_arch+"]: ")
		basearch = new_base_arch or base_arch

	chrootdir = os.path.join(basedir, baserelease+"."+basearch)
	check_dir(chrootdir)
	return (baserelease, basearch, chrootdir)

def debootstrap(release, arch, chrootdir):
	varpath = os.path.join(chrootdir,"var")
	if os.path.exists(varpath):
		print varpath+" was already found.\n Base system will not be installed!"
		ccontinue = ""
		while ccontinue not in ("y","n"):
			ccontinue = raw_input('Continue ? (y/n)')
			if ccontinue == "n":
				sys.exit(1);
	else:
		print "Installing base system for "+release+" "+arch+" into "+ chrootdir
		os.system("debootstrap --variant=buildd --arch "+arch+" "+release+" "+chrootdir+" http://"+your_mirror+"/ubuntu/");

def chroot_config_files_update(chrootdir, release, arch):
	"""
	Updates config files fromt he chrootdir environment
	"""
	copy_to_chroot(os.path.join("etc/resolv.conf"), chrootdir);
	copy_to_chroot(os.path.join("etc/apt/sources.list"), chrootdir);
	copy_to_chroot(os.path.join("etc/passwd"), chrootdir);
	copy_to_chroot(os.path.join("etc/shadow"), chrootdir);
	copy_to_chroot(os.path.join("etc/group"), chrootdir);
	copy_to_chroot(os.path.join("etc/hosts"), chrootdir);
	copy_to_chroot(os.path.join("etc/sudoers"), chrootdir);
	copy_to_chroot(os.path.join("etc/timezone"), chrootdir);
	copy_to_chroot(os.path.join("etc/apt/trusted.gpg"), chrootdir);	
	os.system("sed -i s/"+my_release+"/"+release+"/g "+chrootdir+"/etc/apt/sources.list")
	os.system("+echo "+release+"."+arch+" > "+chrootdir+"/etc/debian_chroot")

def chroot_postinstall_update(chrootdir, release, arch):
	"""
	Perform postinstall update actions"
	"""
	print "Post install actions for the chrooted environment"
	print "Installing deb building support tools"
	os.system("chroot "+chrootdir+" apt-get -y update")
	os.system("chroot "+chrootdir+" apt-get -y --force-yes install gnupg apt-utils")
	os.system("chroot "+chrootdir+" apt-get -y update")
	#os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install devscripts sudo vim locales dialog language-pack-en-base")
	#os.system("chroot "+chrootdir+" locale-gen US.UTF-8 pt_PT.UTF-8")
	os.system("chroot "+chrootdir+" locale-gen "+lang)	
	os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install dh-make fakeroot cdbs sudo")
	#os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install build-essential")
	#os.system("chroot "+chrootdir+" sudo apt-get install -f")
	os.system("chroot "+chrootdir+" apt-get upgrade -y")
	os.system("chroot "+chrootdir+" apt-get clean")
	print "Creating schroot image "+chrootdir+".tar.gz, please be patient"
	os.system("tar -C "+chrootdir+" -czf "+chrootdir+".tar.gz .")
	print "You must manually edit /etc/schroot/schroot.conf  and add:"
	print "["+release+"."+arch+"]"
	print "type=file"
	print "file="+chrootdir+".tar.gz"
	print "groups=admin"
	print "root-groups=root,sbuild,admin"
	if arch=="i386":
		print "personality=linux32"
	print ""
	print "Then you can use your schroot with:\n\tschroot -c "+release+"."+arch
	# The following is required to disabled passwd overwritting
	if os.path.exists("/etc/schroot/setup.d/30passwd"):
	  os.system("mv /etc/schroot/setup.d/30passwd /etc/schroot/setup.d/disabled.30passwd")

my_release = get_host_release();
check_requirements()
basedir = check_base_dir()
(release, arch, chrootdir) = check_chroot_release(basedir)
debootstrap(release, arch, chrootdir)
chroot_config_files_update(chrootdir, release, arch)
chroot_postinstall_update(chrootdir, release, arch)

print "schroot "+release+" succesfully created"

