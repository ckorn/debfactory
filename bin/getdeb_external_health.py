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
#
#  This file provides several functions to handle debian packages
#  control files.
import sys
import os
import re
import time
import random
import operator
import cgi
from threading import Thread
from xml.dom import minidom
from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions
LAUNCH_DIR = os.path.abspath(sys.path[0])
LIB_DIR = os.path.join(LAUNCH_DIR, '..', 'lib')
sys.path.insert(0, LIB_DIR)
from mail import send_mail

SETTINGS_FILE = LAUNCH_DIR + "/getdeb_external_health.json"
SENDER_MAIL=""
RECV_MAIL=""

data = []
archiveUrl = ""
nowatch = []
warning = []
ignored = []
uptodate = []
needsupdate = []

mylookup = TemplateLookup(directories=['templates'])

def loadSettings():
	global SETTINGS_FILE
	settings_file=Path(os.path.expanduser(SETTINGS_FILE))
	if settings_file.is_file():
		return json.loads(settings_file.read_text())
	return {}

def saveSettings(settings):
	global SETTINGS_FILE
	json_settings = json.dumps(settings, sort_keys=True, indent=4, separators=(',', ': '))
	settings_file=Path(os.path.expanduser(SETTINGS_FILE))
	settings_file.write_text(json_settings)

def serve_template(templatename, **kwargs):
    mytemplate = mylookup.get_template(templatename)
    return mytemplate.render(**kwargs)

class testit(Thread):
	def __init__ (self,source):
		Thread.__init__(self)
		self._source = source
	def exe(self, command):
		#print command
		os.system(command)
	def run(self):
		global archiveUrl, nowatch, warning, uptodate, needsupdate
		self._source["Warning"] = []

		rand = random.randint(0,9999999)
		directory = self._source["Package"] + str(rand)
		diff = "/tmp/"+directory+"/bla.diff.gz"
		# Always name the file debian.tar.gz (Although it may be a debian.tar.bz2)
		debianTarGz = "/tmp/"+directory+"/"+directory+"/debian.tar.gz"
		xmlfile = "/tmp/"+directory+"/dehs.xml"

		self.exe("cd /tmp ; rm -rf "+directory)

		self.exe("cd /tmp ; mkdir "+directory)
		if self._source["patch"][1].endswith("diff.gz"):
			self.exe("cd /tmp/"+directory+" ; wget -q -O "+diff+" "+archiveUrl+self._source["Directory"]+"/"+self._source["patch"][1])
			p = os.popen("cd /tmp/"+directory+" ; lsdiff -z "+diff+" | grep debian/watch")
			watch = p.readline().strip('\r\n')
			p.close()
			if watch == "":
				#print "No debian/watch file found. Skipping."
				#print
				nowatch.append(self._source)
				self.exe("cd /tmp/ ; rm -rf "+directory)
				return

			self.exe("cd /tmp/"+directory+" ; mkdir "+directory)
			self.exe("cd /tmp/"+directory+"/"+directory+" ; filterdiff -z -i\"*/debian/*\" "+diff+" | patch -f -s -p1 2>&1 > /dev/null")
		else:
			if self._source["patch"][1].endswith("debian.tar.bz2"):
				extractFlag = 'j'
			elif self._source["patch"][1].endswith("debian.tar.xz"):
				extractFlag = 'J'
			else:
				extractFlag = 'z'
			self.exe("cd /tmp/"+directory+" ; mkdir "+directory)
			self.exe("cd /tmp/"+directory+"/"+directory+" ; wget -q -O "+debianTarGz+" "+archiveUrl+self._source["Directory"]+"/"+self._source["patch"][1] + " ; tar x"+extractFlag+"f " + debianTarGz)
			p = os.popen("cd /tmp/"+directory+"/"+directory+" ; ls debian/watch 2>/dev/null")
			watch = p.readline().strip('\r\n')
			p.close()
			if watch == "":
				#print "No debian/watch file found. Skipping."
				#print
				nowatch.append(self._source)
				self.exe("cd /tmp/ ; rm -rf "+directory)
				return
		p = os.popen("cd /tmp/"+directory+"/"+directory+" ; uscan --report-status --dehs > "+xmlfile)
		p.close()

		xmldoc = minidom.parse(xmlfile)

		testAdded = False

		#print self._source["Package"]


		if len(xmldoc.firstChild.childNodes) == 1:
			self._source["Warning"].append("Unknown warning. Uscan reports nothing.")
		else:
			for entry in xmldoc.firstChild.childNodes:
				if entry.nodeName == "status":
					status = entry.firstChild.data
					self._source["Status"] = status
					if status == "Newer version available":
						needsupdate.append(self._source)
						testAdded = True
					elif status == "up to date":
						uptodate.append(self._source)
						testAdded = True
					else:
						self._source["Warning"].append("Unknown status: %s" % status)
				if entry.nodeName == "debian-uversion":
					self._source["DebianUVersion"] = entry.firstChild.data
				if entry.nodeName == "debian-mangled-uversion":
					self._source["DebianMangledUVersion"] = entry.firstChild.data
				if entry.nodeName == "upstream-version":
					if not entry.firstChild:
						self._source["UpstreamVersion"] = "0"
						self._source["Warning"].append("UpstreamVersion=0")
						os.system("cat " + xmlfile)
					else:
						self._source["UpstreamVersion"] = entry.firstChild.data
				if entry.nodeName == "upstream-url":
					self._source["UpstreamURL"] = entry.firstChild.data
				if entry.nodeName == "warnings":
					self._source["Warning"].append(entry.firstChild.data)

		if len(self._source["Warning"]) > 0:
			ignore = False
			# Google just down their code hosting. Just too lazy to fix all packages.
			for w in self._source["Warning"]:
				if "no matching hrefs for watch line" in w and "code.google.com" in w:
					ignore = True
			if ignore:
				ignored.append(self._source)
			else:
				warning.append(self._source)
			testAdded = True

		if not testAdded:
			print self._source["Package"]
			os.system("cat " + xmlfile)

		self.exe("cd /tmp ; rm -rf "+directory)

if __name__ == "__main__":
	global SENDER_MAIL, RECV_MAIL
	if len(sys.argv) == 1:
		print "Usage: "+sys.argv[0]+" <archiveUrl> <Sources.gz> <HTML-File>"
		print "Example: "+sys.argv[0]+" \"http://archive.getdeb.net/getdeb/ubuntu/\""+ \
		      " \"http://archive.getdeb.net/getdeb/ubuntu/dists/karmic-getdeb/apps/source/Sources.gz\""+ \
		      " getdeb.html"
		sys.exit(1)

	archiveUrl = sys.argv[1]
	sources = sys.argv[2]
	htmlfile = sys.argv[3]
	numberOfThreads = 7
	threads = []

	# Remember cwd and change back later to find the templates
	curdir = os.getcwd()

	os.chdir("/tmp")
	if os.path.isfile("/tmp/Sources.gz"): os.remove("/tmp/Sources.gz")
	if os.path.isfile("/tmp/Sources"): os.remove("/tmp/Sources")
	os.system("wget -q "+sources+" > /dev/null")
	os.system("gunzip -d Sources.gz")

	source = {}
	infiles = False

	sources = open("Sources", "r")
	for line in sources.readlines():
		line = line.strip("\n\r")
		if line == "":
			data.append(source)
			infiles = False
			source = {}
		if line.startswith("Package:"):
			source["Package"] = line.split(" ")[1]
		if line.startswith("Version:"):
			source["Version"] = line.split(" ")[1]
		if line.startswith("Directory:"):
			source["Directory"] = line.split(" ")[1]
		if line.startswith("Files:"):
			infiles = True
			continue
		if line.startswith(" ") and infiles:
			parts = line.split(" ")
			md5sum = parts[1]
			filename = parts[3]
			if filename.endswith("tar.gz"): source["tar.gz"] = (md5sum, filename)
			if filename.endswith("diff.gz"): source["patch"] = (md5sum, filename)
			if filename.endswith("debian.tar.gz"): source["patch"] = (md5sum, filename)
			if filename.endswith("debian.tar.bz2"): source["patch"] = (md5sum, filename)
			if filename.endswith("debian.tar.xz"): source["patch"] = (md5sum, filename)
			if filename.endswith("dsc"): source["dsc"] = (md5sum, filename)
		if infiles and line.find(":") != -1: infiles = False

	sources.close()

	if os.path.isfile("/tmp/Sources.gz"): os.remove("/tmp/Sources.gz")
	if os.path.isfile("/tmp/Sources"): os.remove("/tmp/Sources")

	for source in data:
		if len(threads) < numberOfThreads:
			thread = testit(source)
			thread.start()
			threads.append(thread)
		else:
			threadAdded = False
			while not threadAdded:
				for i,t in enumerate(threads):
					if not t.isAlive():
						thread = testit(source)
						thread.start()
						threads[i] = thread
						threadAdded = True
						break
				if not threadAdded: time.sleep(0.010)

	threadsFinished = False
	while not threadsFinished:
		threadsFinished = True
		for t in threads:
			if t.isAlive():
				threadsFinished = False
		if not threadsFinished: time.sleep(0.1)

	nowatch.sort(key=operator.itemgetter('Package'))
	warning.sort(key=operator.itemgetter('Package'))
	needsupdate.sort(key=operator.itemgetter('Package'))
	uptodate.sort(key=operator.itemgetter('Package'))

	if needsupdate is not None and SENDER_MAIL != "" and RECV_MAIL != "":
		settings=loadSettings()
		for source in needsupdate:
			settingsPackage=settings.get(source['Package'])
			if settingsPackage is None or settingsPackage['Version'] != source['UpstreamVersion']:
				send_mail(SENDER_MAIL, RECV_MAIL, source['Package'] + " (" + source['UpstreamVersion'] + ")", "")
				settings[source['Package']] = {}
				settings[source['Package']]['Version'] = source['UpstreamVersion']
				saveSettings(settings)

	os.chdir(curdir)

	render_args = { 'data': data, 'needsupdate': needsupdate, 'archiveUrl': archiveUrl, 'warning': warning, 'ignored': ignored, 'nowatch': nowatch, 'uptodate': uptodate }
	try:
		#html_code = serve_template('templ.html', data = data, needsupdate = needsupdate, archiveUrl = archiveUrl, warning = warning, nowatch = nowatch, uptodate = uptodate )
		html_code = serve_template('templ.html', render_args = render_args)
	except:
		html_code = exceptions.text_error_template().render()

	with open(os.getenv('PWD')+"/"+htmlfile, 'w') as f:
		f.write(html_code)
		f.close()
