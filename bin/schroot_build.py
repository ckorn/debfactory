#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   (C) Copyright 2006-2010, GetDeb Team - https://launchpad.net/~getdeb
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
"""
chroot build helper script

This script automates the creation of a file based schroot image

 The script performs the following actions:
	- Check/install the pre-required packages (fakeroot, schroot, etc)
	- Install a base system into the specified directory using debootstrap
	- Copy required system config files into the chroot
	- Customize the configuration (eg. point the repositories to apt-cacher)
	- Append the schroot configuration entry to /etc/schroot/schoot.conf
"""
import os
import sys
import shutil
import string
import commands
import glob


available_archs = ("i386", "amd64")

apt_mirror = 'localhost:3142'

class Config(object):
	chrootDirectory = None
	releaseVersion = None
	architecture = None
	usingSbuild = 0
	provider = "ubuntu"

appConfig = Config()

print 
print "###### schroot build helper script"
print

# We need root
if os.getuid() != 0 :
	print 'This script needs to be run as root/sudo !'
	sys.exit(2)

lang = os.environ['LANG']
os.putenv('LANG', 'C') # We use system commands, use a reliable language

def parse_options():
	global appConfig
	for args in sys.argv:
		if args.find('-c=') != -1:
			appConfig.chrootDirectory = args.replace('-c=', '')
			print "Using chroot directory:", appConfig.chrootDirectory
			continue
		if args.find('-r=') != -1:
			appConfig.releaseVersion = args.replace('-r=', '')
			print "Trying release:", appConfig.releaseVersion
			continue
		if args.find('-a=') != -1:
			appConfig.architecture = args.replace('-a=', '')
			print "Trying architecture:", appConfig.architecture
			continue
		if args == '-b':
			appConfig.usingSbuild = 1
			print "sBuild options enabled"
			continue
		if args.find('-p=') != -1:
			appConfig.provider = args.replace('-p=', '')
			print "Replacing provider"
			continue		

def check_and_install_package(package):
	""" 
	check if a package is installed, if not present the option to install it
	"""
	is_installed = int(commands.getoutput('dpkg -l '+package+' 2>&1 | grep -c "^ii"'))
	if is_installed:
		print "Package "+package+" is installed."
	else:
		print "Package "+package+" is required but not installed."
		install = ""
		while install not in ("y", "n"):
			install = raw_input('Install it now ? (y/n)')
			if install == "n":
				print "Exiting on missing package."
				sys.exit(1);
		os.system('sudo apt-get install -y '+package)

def get_host_release():
	"""
	Get the system release (lsb_release -cs)
	"""
	release = commands.getoutput('lsb_release -cs').strip("\r\n")
	return release

def check_create_dir(name):
	"""
	Check if a given directory exists, create it if not
	"""
	if os.path.exists(name):
		print name+" was found"
	else:
		print "Creating directory "+name
		os.mkdir(name)

def copy_to_chroot(fname, chrootdir):
	print "/"+fname+" -> "+os.path.join(chrootdir,fname)
	shutil.copyfile("/"+fname, os.path.join(chrootdir,fname))

# Check requirements
def check_requirements():
	global appConfig
	"""
	Check script requirements
	"""
	print "Checking system requirements"
	# Check for dhcroot and debootstrap
	check_and_install_package("schroot")
	check_and_install_package("debootstrap")
	check_and_install_package("apt-cacher-ng")
	if appConfig.usingSbuild == 1:
		check_and_install_package("sbuild")
	print

def check_base_dir():
	global appConfig
	if appConfig.chrootDirectory:
		check_create_dir(appConfig.chrootDirectory)
		return appConfig.chrootDirectory
	base_dir = "/home/schroot"
	new_base_dir = raw_input("Please enter the chroot install base directory\n["+base_dir+"]: ")
	basedir = new_base_dir or base_dir
	check_create_dir(basedir)
	return basedir

def check_chroot_release(basedir):
	scripts_dir = '/usr/share/debootstrap/scripts/'
	global appConfig , available_releases
	baserelease = ''
	base_release = appConfig.releaseVersion or get_host_release()
	available_releases = [x.replace(scripts_dir,'') \
						 for x in glob.glob(scripts_dir+"*") if '.' not in x]
	print 'Available releases (fount at %s):\n %s' % (scripts_dir, ','.join(available_releases))
	while baserelease not in available_releases:
		new_base_release = raw_input("Please enter the chroot release version ["+base_release+"]: ")
		baserelease = new_base_release or base_release
	base_arch = "i386"
	basearch = ""
	if appConfig.architecture:
		basearch = appConfig.architecture
	while basearch not in available_archs:
		new_base_arch = raw_input("Please enter the chroot architecture, options are: "+','.join(available_archs)+"\n["+base_arch+"]: ")
		basearch = new_base_arch or base_arch

	chrootdir = os.path.join(basedir, baserelease+"."+basearch)
	check_create_dir(chrootdir)
	return (baserelease, basearch, chrootdir)

def debootstrap(release, arch, chrootdir):
	global appConfig
	print "provider=", appConfig.provider
	print "Installing base system for "+release+" ["+arch+"] into "+ chrootdir	
	return os.system("debootstrap --variant=buildd --arch "+arch+" "+release+\
		" "+chrootdir+" http://"+apt_mirror+"/"+appConfig.provider+"/");

def chroot_config_files_update(chrootdir, release, arch):
	"""
	Updates config files fromt he chrootdir environment
	"""
	default_sources="""
deb http://mirror/ubuntu/ release main restricted
deb-src http://mirror/ubuntu/ release main restricted
deb http://mirror/ubuntu/ release-updates main restricted
deb-src http://mirror/ubuntu/ release-updates main restricted

deb http://mirror/ubuntu/ release universe
deb-src http://mirror/ubuntu/ release universe
deb http://mirror/ubuntu/ release-updates universe
deb-src http://mirror/ubuntu/ release-updates universe

deb http://mirror/ubuntu/ release multiverse
deb-src http://mirror/ubuntu/ release multiverse
deb http://mirror/ubuntu/ release-updates multiverse
deb-src http://mirror/ubuntu/ release-updates multiverse

deb http://mirror/ubuntu release-security main restricted
deb-src http://mirror/ubuntu release-security main restricted
deb http://mirror/ubuntu release-security universe
deb-src http://mirror/ubuntu release-security universe
deb http://mirror/ubuntu release-security multiverse
deb-src http://mirror/ubuntu release-security multiverse
	"""
	apt_mirror = "localhost:3142" 
	default_sources = default_sources.replace("mirror", apt_mirror)
	default_sources = default_sources.replace("release", release)
	FILE = open(chrootdir+"/etc/apt/sources.list","w")
	FILE.writelines(default_sources)
	FILE.close()
	copy_to_chroot("etc/resolv.conf", chrootdir);
	copy_to_chroot("etc/hosts", chrootdir);
	copy_to_chroot("etc/sudoers", chrootdir);

	os.system("echo "+release+"."+arch+" > "+chrootdir+"/etc/debian_chroot")

def chroot_postinstall_update(chrootdir, release, arch):
	global appConfig
	"""
	Perform post-install update actions"
	"""
	print "Post install actions for the chroot image"
	print "Installing some support tools"
	os.system("chroot "+chrootdir+" apt-get -y update")
	os.system("chroot "+chrootdir+" apt-get -y --force-yes install gnupg apt-utils")
	os.system("chroot "+chrootdir+" apt-get -y update")
	os.system("chroot "+chrootdir+" locale-gen "+lang)	
	os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install wget dh-make fakeroot cdbs sudo")
	os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install devscripts vim")
	os.system("mount --bind /proc "+chrootdir +"/proc")
	os.system("chroot "+chrootdir+" sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install console-setup")
	os.system("umount "+chrootdir +"/proc")
	# We need to install build-essential for hardy, it is not contained on the buildd variant
	os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends install build-essential")
	os.system("chroot "+chrootdir+" apt-get -y --no-install-recommends upgrade")
	os.system("chroot "+chrootdir+" apt-get clean")
	print "Creating the schroot image "+chrootdir+".tar.gz, please be patient..."
	os.system("tar -C "+chrootdir+" -czf "+chrootdir+".tar.gz .")
	os.system("du -sh "+chrootdir+".tar.gz")
	shutil.rmtree(chrootdir)
	is_configured = int(commands.getoutput("grep -v '#' /etc/schroot/schroot.conf | grep -c "+release+"."+arch))
	if is_configured==0:
		schroot_conf = "\n"
		schroot_conf += "["+release+"."+arch+"]"+"\n"
		schroot_conf += "type=file\n"
		schroot_conf += "file="+chrootdir+".tar.gz\n"
		schroot_conf += "groups=admin\n"
		if appConfig.usingSbuild == 1:
			schroot_conf += "root-groups=sbuild\n"
		if arch=="i386":
			schroot_conf += "personality=linux32\n" 
		FILE = open("/etc/schroot/schroot.conf","a")
		FILE.writelines(schroot_conf)
		FILE.close()
		#print "root-groups=root,sbuild,admin"
	print ""
	print "You can now use your schroot with:\n\tschroot -c "+release+"."+arch+" -p"

# This is the main app
parse_options()
my_release = get_host_release()
check_requirements()
basedir = check_base_dir()
(release, arch, chrootdir) = check_chroot_release(basedir)
rc = debootstrap(release, arch, chrootdir)
if rc != 0:
	print "Debootstrap failed!"
	sys.exit(1)
chroot_config_files_update(chrootdir, release, arch)
chroot_postinstall_update(chrootdir, release, arch)

print 
print "schroot for "+release+" successfully created."

