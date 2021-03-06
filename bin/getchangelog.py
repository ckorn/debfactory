#!/usr/bin/python3
#
#  (C) Copyright 2012, GetDeb Team - https://launchpad.net/~getdeb
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
import argparse
import os
import re
import sys
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from gi.repository import GObject
import requests
import urllib
from urllib.parse import urlparse

releases=[{"release" : "xenial", "date": "16.04" }, {"release" : "yakkety", "date": "16.10" }]

def get_releases(url):
	r = requests.get(url)
	t=r.text[r.text.find('Packages are available for the following releases'):]
	t=t[:t.find('</p>')]
	# Ubuntu 15.10: 1:2016.02.27-1~getdeb1<br/>
	m=re.compile("Ubuntu (?P<date>[\d\.]+): (?P<version>\S+)")
	matches=m.finditer(t)
	releases=[ { "version": x.group("version"), "date": x.group("date") } for x in matches ]
	for rel in releases:
		v = rel["version"]
		v = v[:v.find("<")]
		rel["version"]=v.split(":")[-1].split("-")[0]
	return releases

def filter_releases(url, version):
	global releases
	rel=get_releases(url)
	dates=[x["date"] for x in rel if x["version"] == version]
	ret = [x["release"] for x in releases for y in dates if x["date"] == y]
	return ret

def quote_url_path(url):
	o = urlparse(url)
	r = "%s://%s%s"%(o.scheme, o.netloc, urllib.parse.quote(o.path))
	return r

def getChangelog(changelogFile, googleOutput, includeDescription, appURL, createGitCommitMsg, outputFile, showOutputFile, copyToClipboard):
	c=changelogFile
	if not os.path.exists(c):
		print("'%s' does not exist"%(c), file=sys.stderr)
		return 1

	"""
	the-powder-toy (84.2-1~getdeb1) precise; urgency=low

	  * New upstream version
	    Fixed: VIBR Fixes
	    Fixed: Spelling errors in game UI
	    Fixed: Make SC_SENSOR available in Lua API

	 -- Christoph Korn <christoph.korn@getdeb.net>  Thu, 15 Nov 2012 20:27:05 +0100
	"""

	f=open(c)
	lines=f.read().split("\n")
	f.close()

	matcher=re.compile("^(?P<name>[a-zA-Z0-9-+.]+) \((?P<version>[^)]+)\) (?P<release>[a-zA-Z]+); urgency=(?P<urgency>.+)$")
	# we save the indexes in "lines" where the message starts and ends
	start=2
	end=2
	for i, line in enumerate(lines):
		if i == 0:
			m=matcher.match(line)
			if not m:
				print("Could not match first line: %s"%(line), file=sys.stderr)
				return 2
		# the second line is empty
		if i == 1: continue
		# if the line starts with " -- " we are ready
		if line.startswith(" -- "):
			# the last line of the message is two lines before this line. because the last line should be empty.
			end=i-2
			break

	# the end is not included: l[0:1] <--> l[0]
	msg=lines[start:end+1]
	msg="\n".join(msg)

	output=""
	# create output for Google+
	if googleOutput:
		description=""
		if includeDescription:
			control=c.replace("changelog", "control")
			if not os.path.exists(control):
				print("'%s' does not exist"%(control), file=sys.stderr)
				return 3
			f=open(control)
			lines=f.read().split("\n")
			f.close()

			package_found = False
			matcher=re.compile("^Package: (?P<package>[a-zA-Z0-9-+.]+)$")
			matcher2=re.compile("^Description: (?P<description>.*)$")
			for line in lines:
				if package_found:
					m2=matcher2.match(line)
					if m2:
						description="(%s)\n"%(m2.group("description"))
						break
				m2=matcher.match(line)
				if m2 and m2.group("package") == m.group("name"):
					package_found = True
		name=appURL.split("/")[-1].replace("%20", " ")
		version=m.group("version").split(":")[-1].split("-")[0]
		releases="+".join(filter_releases(appURL, version))
		output = "*%s %s (%s)*\n"%(name, version, releases)
		output += description
		output += "\n"
		# add #twt tag for automatic twitter post (https://manageflitter.com/engage/sync)
		output += msg + " #twt"
		output += "\n"
		output += "\n"
		output += quote_url_path(appURL)
	# create output for git commit msg
	elif createGitCommitMsg:
		name = m.group("name")
		version = m.group("version").split(":")[-1]
		output = "%s: %s\n"%(name, version)
		output += "\n"
		output += msg

	out = sys.stdout
	if outputFile: out=open(outputFile, "w")
	print(output, file=out)
	if outputFile: out.close()

	if showOutputFile and outputFile:
		subprocess.call(["xdg-open", outputFile])

	if copyToClipboard:
		clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
		clipboard.set_text(output, -1)
		GObject.timeout_add(100, Gtk.main_quit)
		Gtk.main()

def main():
	parser = argparse.ArgumentParser(description="parses a debian/changelog file for a commit msg or Google+")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-g", "--google", metavar="URL", help="Create output for a post on Google+. The link to the download page has to be given")
	group.add_argument("-m", "--message", action="store_true", help="Create output for a git commit msg. Use --output to specify the file for the commit message")
	group = parser.add_argument_group()
	group.add_argument("-s", "--show", action="store_true", help="Show the created file in a text editor")
	group.add_argument("-o", "--output", metavar="file", help="The output will be written to this file. If not given it is written to stdout")
	group.add_argument("-d", "--description", action="store_true", help="Add a description in the output. Will be read from control file in same directory.")
	group.add_argument("-c", "--clipboard", action="store_true", help="Copy the output to the clipboard")
	parser.add_argument("changelog", help="path to debian/changelog file")
	args = parser.parse_args()

	getChangelog(args.changelog, args.google, args.description, args.google, args.message, args.output, args.show, args.clipboard)


if __name__ == "__main__":
	main()
