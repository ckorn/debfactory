#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  (C) Copyright 2010, GetDeb Team - https://launchpad.net/~getdeb
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
# Compares the source packages and versions of source repository (e.g. getdeb-lucid)
# with the versions in the target repository (e.g. getdeb-maverick) and with the versions
# found in the official Ubuntu repositories.
# The Ubuntu versions are determined via apt-get policy therefore the script should be run
# on a system with the target release (e.g. maverick) installed.
#
import os
import commands
import random
import time
import sys

source_to_binary = {
	"dynamica": "dynamica-dev",
	"freeciv": "freeciv-client-gtk",
	"gigi-freeorion": "libgigi-dev",
	"jngl": "libjngl-dev",
	"libbullet": "libbullet-dev",
	"libelfhacks": "libelfhacks-dev",
	"libpacketstream": "libpacketstream-dev",
	"libsfml2": "libsfml2.4-dev",
	"libspidermonkey": "libspidermonkey-dev",
	"mygui": "libmygui-dev",
	"raydium": "libraydium-dev",
	"simgear": "libsimgear-dev",
	"vulture": "vulture-slashem",
	"wiiuse": "libwiiuse-dev",
	"d0-blind-id": "libd0-blind-id0-dev",
	"c++-gtk-utils": "libcxx-gtk-utils-dev",
	"comex-base": "libcomex-base-cil-dev",
	"glclib": "glclib-dev",
	"libclastfm": "libclastfm0-dev",
	"libqtwit": "libqtwit-dev",
	"libroadnav": "libroadnav-dev",
	"libxcm": "libxcm-dev",
	"livestreamer": "python-livestreamer",
	"livestreamer-ui": "python-livestreamer-ui",
	"qrcode": "python-qrcode",
	"rabbitvcs": "rabbitvcs-nautilus",
	"speedtest-cli": "python-speedtest-cli",
	"sphlib": "libsph-dev",
	"libzenxml": "libzenxml2.0-dev",
	"netmaumau": "netmaumau-client",
	"libjoyrumble": "libjoyrumble-dev",
	"vbam": "vbam-gtk",
	"avidemux2.6": "avidemux2.6-plugins-qt",
	"dtags": "python-dtags",
	"libqtav": "libqtav-dev",
	"flightgear-data": "flightgear-data-all",
	"libgames-support": "libgames-support2",
	"libfilezilla": "libfilezilla-dev",
	"pyaes": "python-pyaes",
	"zbarlight": "python-zbarlight"
}

def run(c):
	print c
	os.system(c)

### Extract the upstream version from a complete version
### Input 1:2.7.4-1~getdeb2 -> Output: 2.7.4
def upstreamVersion(v):
	if not v: return None
	version = v
	if version.find("-") != -1:
		version = version.rsplit("-", 1)[0]
	if version.find(":") != -1:
		version = version.split(":")[1]

	return version

### Input: a list of dicts. Keys: "Package" and "Version" and package name
### Output: Version of that package
def getVersion(data, package):
	for x in data:
		if x["Package"] == package:
			return x["Version"]
	return None

### Get the version of 
### a) the package in the Ubuntu repositories (parses output of apt-get policy)
### b) the package in a second repository (i.e. the target repository to see if the package already has been copied)
### c) the package in the source repository
### Input: package name, the data of the second repository. Output: (ubuntu_version, source_version, target_version)
def getRepositoryVersions(package, source_data, target_data):
	p_real=realPackageName(package)
	(rc, output) = commands.getstatusoutput("LANG=C apt-cache policy %(p_real)s"%locals())
	output_lines = output.split("\n")
	in_version_table = False
	ubuntu_version = None
	# Data contains "Package" and "Version" keys
	source_version = upstreamVersion(getVersion(source_data, package))
	target_version = upstreamVersion(getVersion(target_data, package))
	for line in output_lines:
		line = line.strip("\r\n")
		# Maybe the candidate is already a non-Getdeb version
		if line.startswith("  Candidate: "):
			version = line[13:]
			# "none" means there is no candidate
			if version.find("none") != -1:
				break
			# we do not want to get GetDeb versions here
			if version.find("getdeb") == -1:
				ubuntu_version = upstreamVersion(version)
		# Package not found
		elif line.startswith("W: Unable to locate package "):
			break
		# If no candidate is found we have to look at the version table
		elif line.startswith("  Version table:"):
			in_version_table = True
		elif in_version_table:
			if (line.startswith("     ") and not line.startswith("        ")) or line.startswith(" *** "):
				version = line[5:].split(" ")[0]
				# we also don't want GetDeb versions here.
				if version.find("getdeb") == -1:
					ubuntu_version = upstreamVersion(version)
					return (ubuntu_version, source_version, target_version)
	# if one version was found return the tuple
	if ubuntu_version or target_version:
		return (ubuntu_version, source_version, target_version)
	# Else None to make a difference if the package was not found at all.
	return None

### Parse a Sources file. Extracts the package name and version
### Input: Path to the Sources File; Output: a list of dicts. Keys: "Package" and "Version"
def readSourcesFile(sourcesFile):
	data = []
	source = {}
	infiles = False

	sources = open(sourcesFile, "r")
	for line in sources.readlines():
		line = line.strip("\n\r")
		# An empty line marks the end of a package entry.
		if line == "":
			data.append(source)
			infiles = False
			source = {}
		# Syntax: Package: packagename
		if line.startswith("Package:"):
			source["Package"] = line.split(" ")[1]
		# Syntax: Version: 1:1.2.3.4-1~getdeb2
		if line.startswith("Version:"):
			source["Version"] = line.split(" ")[1]
			#if source["Package"] == "argouml": print source["Version"]
	sources.close()
	return data

### Simulates the installation of the package with apt-get -s install
### Input: package name; Output: Return code of apt-get. 0 on successfull installation.
def simulateInstall(package):
	(rc, output) = commands.getstatusoutput("LANG=C apt-get -s install %s" % (realPackageName(package)))
	return rc

### creates a file for reprepro to copy the package from source to destination
def createRepreproCopyFile(package, source, dest, version):
        ###"c_korn@gmx.de copy raring-getdeb quantal-getdeb jnetmap 0.5.2-1~getdeb1" (no new line)
	action = "%s %s %s %s %s %s" % ("christoph.korn@posteo.de", "copy" \
		, dest, source, package, version)
			
	time_now = time.strftime("%Y%m%d.%H%M%S", time.localtime())
	filename = "%s_%s_%s" % (package, version, time_now)
	full_repos_cmd_dir  = os.path.join('/', 'tmp', 'reprepro')
	if not os.path.isdir(full_repos_cmd_dir):
		return "%s directory is not available, " \
			"repository commands are not supported" % \
			full_repos_cmd_dir
	os.umask(002)
	f = open(os.path.join(full_repos_cmd_dir, filename), 'w')
	os.umask(022)
	f.write(action)
	f.close()

### actually we hope that the binary package has the same name as the
### source package. This function outputs the binary package name for
### a source package. It is hard coded because I do not know how to get the
### binary package from a source package
def realPackageName(p):
	global source_to_binary
	if p in source_to_binary.keys():
		return source_to_binary[p]
	return p

### writes the binary package name behind the source package name
### (only if it is different)
def packageLine(p):
	s=p
	x=realPackageName(p)
	if x != p:
		s+=" (%s)"%(x)
	return s

### Compare the versions with dpkg. Return 0 if compare is true.
### returns (rc, output)
def compareVersions(version1, compare, version2):
	return commands.getstatusoutput("LANG=C dpkg --compare-versions %(version1)s %(compare)s %(version2)s "%locals())

if __name__ == "__main__":
	host = "http://archive.getdeb.net/getdeb"
	useArgs = ( len(sys.argv) == 4 )
	source_release = sys.argv[1] if useArgs else "wily"
	target_release = sys.argv[2] if useArgs else "xenial"
	component = sys.argv[3] if useArgs else "games"
	link = "http://www.getdeb.net" if component == "apps" else "http://www.playdeb.net"
	source_rep = "%(host)s/ubuntu/dists/%(source_release)s-getdeb/%(component)s/source/Sources.gz"%locals()
	target_rep = "%(host)s/ubuntu/dists/%(target_release)s-getdeb/%(component)s/source/Sources.gz"%locals()

	# Get the .gz file and extract it. Parse it.
	os.chdir("/tmp")
	if os.path.isfile("/tmp/Sources.gz"): os.remove("/tmp/Sources.gz")
	if os.path.isfile("/tmp/Sources"): os.remove("/tmp/Sources")
	run("wget -q "+source_rep+" > /dev/null")
	run("gunzip -d Sources.gz")
	source_data = readSourcesFile("Sources")

	# Get the .gz file and extract it. Parse it.
	os.chdir("/tmp")
	if os.path.isfile("/tmp/Sources.gz"): os.remove("/tmp/Sources.gz")
	if os.path.isfile("/tmp/Sources"): os.remove("/tmp/Sources")
	run("wget -q "+target_rep+" > /dev/null")
	run("gunzip -d Sources.gz")
	target_data = readSourcesFile("Sources")

	# Save the data in lists for HTML-File generation
	not_found = []
	greater_ubuntu_version = []
	greater_getdeb_version = []
	only_getdeb = []

	for source in source_data:
		r = getRepositoryVersions(source["Package"], source_data, target_data)
		if not r:
			# Not in Ubuntu or destination repository
			s = simulateInstall(source["Package"])
			print source["Package"],s
			not_found.append((source["Package"],s))
		else:
			ubuntu_version, source_version, target_version = r
			# there may be a newer version in source as in target
			greater_in_source = False
			if source_version and target_version:
				(rc, output) = compareVersions(source_version, "gt", target_version)
				if rc == 0: greater_in_source = True
			if ubuntu_version:
				# In Ubuntu repository. May also already be in destination repository.
				# Compare Ubuntu and GetDeb version
				(rc, output) = compareVersions(ubuntu_version, "ge", source_version)
				if rc == 0:
					print "Ubuntu version is greater or equal: %s; Ubuntu-Version: %s; Source-Version: %s; Target-Version: %s" \
					      % (source["Package"],ubuntu_version,source_version, target_version)
					greater_ubuntu_version.append(((source["Package"],ubuntu_version,source_version, target_version or "")))
				else:
					# Also try to install the GetDeb package here
					s=simulateInstall(source["Package"])
					print "GetDeb version is greater: %s; Ubuntu-Version: %s; Source-Version: %s; Target-Version: %s; apt-get -s install: %s" \
					      % (source["Package"],ubuntu_version,source_version, target_version, s)
					greater_getdeb_version.append((source["Package"],ubuntu_version,source_version, target_version or "", s))
			else:
				# Not in Ubuntu but already in destination repository.
				# We already checked that r is not None. Now either the GetDeb or Ubuntu version has to be not None.
				# if the ubuntu_version is None then the getdeb_repository_version is not None
				s=simulateInstall(source["Package"])
				print "%s; Source-Version: %s; Target-Version: %s; apt-get -s install: %s" % (source["Package"], source_version, target_version, s)
				# if the source version is greater append it to not_found because it is top of the list.
				if greater_in_source:
					not_found.append((source["Package"], s))
				else:
					only_getdeb.append((source["Package"], target_version, s))

	anz=len(not_found)+len(greater_ubuntu_version)+len(greater_getdeb_version)+len(only_getdeb)
	if anz != len(source_data):
		print "wrong package count: %s != %s"%(anz, len(source_data))
		sys.exit()
	# Create a nice HTML file
	htmlfile = "/tmp/repository_"+str(random.randint(0,1000))+".html"
	if os.path.isfile(htmlfile): os.remove(htmlfile)
	html = open(htmlfile, "w+")
	html.write("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">")
	html.write("<html xmlns=\"http://www.w3.org/1999/xhtml\">\n")
	html.write("<head>\n")
	html.write("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />\n")
	html.write("<title>Repository-Updatestatus (%s)</title>\n"%(anz))
	html.write("<style type=\"text/css\">\n")
	html.write("table,td { border: solid 1px black ; border-collapse: collapse ; }\n")
	html.write("tr:hover { background-color: #ffff99; }\n")
	html.write("</style>\n")
	html.write("</head>\n")
	html.write("<body>\n")
	html.write("<h1>Neither in target repository nor Ubuntu ("+str(len(not_found))+")</h1><br/>\n")
	html.write("<table>\n")
	html.write("<tr><td>Package</td><td>apt-get -s install</td></tr>\n")
	for (p,i) in not_found:
		html.write("<tr>\n")
		html.write("    <td>"+packageLine(p)+"</td>\n")
		html.write("    <td><a href='"+link+"/packages/?q="+realPackageName(p)+"'>"+str(i)+"</a></td>\n")
		html.write("</tr>\n")
                #### create the file for reprepro copy
                if i == 0: createRepreproCopyFile(p, "%(source_release)s-getdeb"%locals(), "%(target_release)s-getdeb"%locals(), getVersion(source_data, p))
	html.write("</table>")

	html.write("<br/><br/><br/>\n")
	html.write("<h1>Versions greater in Ubuntu ("+str(len(greater_ubuntu_version))+")</h1><br/>\n")
	html.write("<table>\n")
	html.write("<tr><td>Package</td><td>Ubuntu version</td><td>GetDeb (source repository) version</td><td>GetDeb (target repository) version</td></tr>\n")
	for (p,u,s,t) in greater_ubuntu_version:
		html.write("<tr>\n")
		html.write("    <td>"+packageLine(p)+"</td>\n")
		html.write("    <td>"+u+"</td>\n")
		html.write("    <td>"+s+"</td>\n")
		html.write("    <td>"+t+"</td>\n")
		html.write("</tr>\n")
	html.write("</table>")

	html.write("<br/><br/><br/>\n")
	html.write("<h1>Versions greater in GetDeb ("+str(len(greater_getdeb_version))+")</h1><br/>\n")
	html.write("<table>\n")
	html.write("<tr><td>Package</td><td>Ubuntu version</td><td>GetDeb (source repository) version</td><td>GetDeb (target repository) version</td><td>apt-get -s install</td></tr>\n")
	for (p,u,s,t,i) in greater_getdeb_version:
		# either target does not exist or source has a newer version. highlight both
		if s != t:
			s = "<b>%(s)s</b>"%locals()
		html.write("<tr>\n")
		html.write("    <td>"+packageLine(p)+"</td>\n")
		html.write("    <td>"+u+"</td>\n")
		html.write("    <td>"+s+"</td>\n")
		html.write("    <td>"+t+"</td>\n")
		html.write("    <td><a href='"+link+"/packages/?q="+realPackageName(p)+"'>"+str(i)+"</a></td>\n")
		html.write("</tr>\n")
                #### create the file for reprepro copy
                if i == 0: createRepreproCopyFile(p, "%(source_release)s-getdeb"%locals(), "%(target_release)s-getdeb"%locals(), getVersion(source_data, p))
	html.write("</table>")

	html.write("<br/><br/><br/>\n")
	html.write("<h1>Already in target repository but not in Ubuntu ("+str(len(only_getdeb))+")</h1><br/>\n")
	html.write("<table>\n")
	html.write("<tr><td>Package</td><td>GetDeb (target repository) version</td><td>apt-get -s install</td></tr>\n")
	for (p,t,i) in only_getdeb:
		html.write("<tr>\n")
		html.write("    <td>"+packageLine(p)+"</td>\n")
		html.write("    <td>"+t+"</td>\n")
		html.write("    <td>"+str(i)+"</td>\n")
		html.write("</tr>\n")
	html.write("</table>\n")

	html.write("</body></html>\n\n")
	html.close()

	os.system("x-www-browser "+htmlfile)
