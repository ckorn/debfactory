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

import os
import commands	 # We need it for the GPG signature verification
import shutil

class DebianControlFile:
	"""
	This class holds all the information from a debian control file.
	It also provides some methods to operate with that information.
	"""
	class FileInfo:
		def __init__(self, md5sum, size, name):			
			self.size = size
			self.md5sum = md5sum
			self.name = name
			
	class FileNotFoundError(Exception):
		""" 
		A file operation was requested an a listed file was not found
		"""
		def __init__(self, filename):
			self.filename = filename
		def __str__(self):
			return repr(self.filename)

	class MD5Error(Exception):
		"""
		The MD5 checksum verification failed during a file copy/move
		operation.
		"""
		def __init__(self, expected_md5, found_md5, name):
			self.expected_md5 = expected_md5
			self.found_md5 = found_md5
			self.name = name
		def __str__(self):
			return repr(self.value1, self.value2, self.value3)


	def __init__(self, filename=None, contents=None):
		self._filename = filename		
		self.load_contents(filename, contents)
			
	def load_contents(self, filename=None, contents=None):
		"""
		Opens the control file and load it's contents into the data
		attribute.
		"""
		self._data = []
		self._deb_info = {}
		last_data = []
		if filename is not None:
			self._filename = filename
			control_file = open(self._filename, 'r')
			self._data = control_file.readlines()
			control_file.close()
		if contents is not None:
			self._data = contents.split("\n")
		last_data = []
		deb_info = {}
		field = None
		for line in self._data:
			try:
				line = unicode(line, 'utf-8')
			except UnicodeDecodeError:
				print "WARNING: Package info contains non utf-8 data, replacing"
				line = unicode(line, 'utf-8', errors='replace')
			line = line.strip("\r\n")
			if not line:
				continue
			if line == '-----BEGIN PGP SIGNATURE-----':
				break
			if line[0] == " ":
				last_data.append(line)
			else:
				if field and len(last_data) > 1:					
					deb_info[field] = last_data
				last_data = []
				(field, sep, value) = line.partition(": ") 
				if sep == ": ":
					last_data = [value]
					deb_info[field] = value
		if field and len(last_data) > 1:					
			deb_info[field] = last_data					
		self._deb_info = deb_info
		
	def files_list(self):
		files = self['Files'][1:]
		file_info_list = []
		for file in files:
			file_parts = file.split(" ")
			file_info = self.FileInfo(file_parts[0], file_parts[1], \
				file_parts[len(file_parts)-1])
			file_info_list.append(file_info)
		return file_info_list

	def version(self):
		""" 
		Returns the package version after removing the epoch part
		"""
		version = self['Version']
		epoch, sep, version = version.partition(":")
		return version or epoch
		   
	def upstream_version(self):
		""" 
		Returns the upstream version contained on the Version field
		"""                
		version_list = self.version().split("-")
		version_list.pop()        
		version = '-'.join(version_list)
		return version

	def verify_gpg(self, keyring, verbose=False):
		"""Verifies the file GPG signature using the specified keyring
		file.
		
		@param keyring: they keyring to be used for verification
		@return: the signature author or None
		"""
		gpg_cmd = "LANG=C gpg --no-options --no-default-keyring "\
			"--keyring %s --verify --logger-fd=1 %s" \
			% (keyring, self._filename)

		sign_author = None
		(rc, output) = commands.getstatusoutput(gpg_cmd)	
		if verbose:
			print output
		output_lines = output.split("\n")		
		if rc==0:
			for line in output_lines:		
				if line.startswith("gpg: Good signature from"):
					dummy, sign_author, dummy = line.split('"')	
		return sign_author
		
	def verify_md5sum(self, source_dir=None):
		"""
		Verify the MD5 checksum for all the files
		Returns:
			None: on success
			(expected_md5, found_md5, filename): on failure
		"""
		source_dir = source_dir or os.path.dirname(self._filename)
		for file in self.files_list():
			full_filename = "%s/%s" % (source_dir, file.name)
			if not os.path.exists(full_filename):
				return (file.md5sum, "FILE_NOT_FOUND", file.name)
			else:
				md5sum=commands.getoutput("md5sum %s" % full_filename)								
				(found_md5, dummy) = md5sum.split()
				if found_md5 != file.md5sum:
					return (file.md5sum, found_md5, file.name)
		return None	
		
	def copy(self, destination_dir=None, source_dir=None, md5check=True):
		"""
		Copies the files listed on the control file
		The control file is also copied at the end
		"""
		source_dir = source_dir or os.path.dirname(self._filename)
		if not os.path.isdir(destination_dir):
			raise Exception
			return
			
		file_list = self.files_list()
		file_list.append(self.FileInfo(None, None, \
			os.path.basename(self._filename)))
		for file in file_list:
			source_filename = "%s/%s" % (source_dir, file.name)
			target_filename = "%s/%s" % (destination_dir, file.name)
			if not os.path.exists(source_filename):
				raise self.FileNotFoundError(source_filename)
				return
			shutil.copy2(source_filename, target_filename)
			if md5check and file.md5sum:
				md5sum = commands.getoutput("md5sum %s" % target_filename)								
				(found_md5, dummy) = md5sum.split()
				if found_md5 != file.md5sum:
					raise self.MD5Error(file.md5sum, found_md5, file.name)                    
					return        
		return None

	def move(self, destination_dir=None, source_dir=None, md5check=True):
		"""
		Moves the files listed on the control file
		The control file is also moved at the end
		Returns:
			None: on success
			(expected_md5, found_md5, filename): on failure
		"""
		source_dir = source_dir or os.path.dirname(self._filename)
		if not os.path.isdir(destination_dir):
			raise Exception
			return

		file_list = self.files_list()
		file_list.append(self.FileInfo(None, None, \
			os.path.basename(self._filename)))
		for file in file_list:
			source_filename = "%s/%s" % (source_dir, file.name)
			target_filename = "%s/%s" % (destination_dir, file.name)
			if not os.path.exists(source_filename):
				raise self.FileNotFoundError(source_filename)
				return
			if os.path.exists(target_filename):
				os.unlink(target_filename)
			shutil.move(source_filename, target_filename)
			if md5check and file.md5sum:
				md5sum = commands.getoutput("md5sum %s" % target_filename)								
				(found_md5, dummy) = md5sum.split()
				if found_md5 != file.md5sum:
					raise self.MD5Error(file.md5sum, found_md5, file.name)                
					return
					
		return None

	def remove(self, source_dir=None):
		"""
		Removes all files listed and the control file itself
		Returns:
			None: on success
			(expected_md5, found_md5, filename): on failure
		"""
		source_dir = source_dir or os.path.dirname(self._filename)
		
		file_list = self.files_list()
		file_list.append(self.FileInfo(None, None, \
			os.path.basename(self._filename)))
		for file in file_list:
			full_filename = "%s/%s" % (source_dir, file.name)
			if os.path.exists(full_filename):
				os.unlink(full_filename)

	def __getitem__(self, item):
		try:
			item = self._deb_info[item]
		except KeyError:
			item = None
		return item
		
	def __str__(self):
		return `self._deb_info`

if __name__ == '__main__':
	sample_control_file = """	
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Format: 1.8
Date: Tue, 07 Jul 2009 02:28:23 +0200
Source: yofrankie
Binary: yofrankie
Architecture: source
Version: 1.1b-1~getdeb1
Distribution: karmic
Urgency: low
Maintainer: Christoph Korn <c_korn@gmx.de>
Changed-By: Christoph Korn <c_korn@gmx.de>
Description: 
 yofrankie  - 3D current generation platform game
Changes: 
 yofrankie (1.1b-1~getdeb1) karmic; urgency=low
 .
   * New upstream version.
Checksums-Sha1: 
 a7ddedc0718746e84dee4abbf5a9349dc2298f77 1715 yofrankie_1.1b-1~getdeb1.dsc
 eb295b42a4a14dcbcab26e0df8077267625cfca7 126347423 yofrankie_1.1b.orig.tar.gz
 1e5d54930757965d74b605f58e03f40242894e36 7312 yofrankie_1.1b-1~getdeb1.diff.gz
Checksums-Sha256: 
 5e9ce202abb68a3c0b08d65c73062458651f3123211131ed02886759408ab24a 1715 yofrankie_1.1b-1~getdeb1.dsc
 cacb84f14de130780fab0b361b73a7429f9a69c7a9ae71f0d1ac8a15f7cb6cb8 126347423 yofrankie_1.1b.orig.tar.gz
 631a5428dbc26c2c4d68ff3b7885a5d563c9401788dc5317a7490eb989ed8d31 7312 yofrankie_1.1b-1~getdeb1.diff.gz
Files: 
 b4d257dc1fc4c49946fa5b2881bd0729 1715 games optional yofrankie_1.1b-1~getdeb1.dsc
 f149c32b22e7bdecec55eae3050ab37b 126347423 games optional yofrankie_1.1b.orig.tar.gz
 23544378887c0c31b391b9e11072a40d 7312 games optional yofrankie_1.1b-1~getdeb1.diff.gz

-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.9 (GNU/Linux)

iQIcBAEBCAAGBQJK2K9bAAoJECT9/e/4vK3Q0dcP/iX0Gdy7xGI5D9BNMLLW/siu
sHINE4258eqCP5N9H2PrFvPz1c4auKmtBia8co/BjI990qVan4hRRyKPYE8qbJ7a
3tiuN+kQiWK3TarEZ/JuWUt5H0DI+oUWUuAsY2pGyS9GM/wMJsO9MD/ZbOodNvVm
/g7GICGJ8Rlk6wb0YcywJOPCU2Bc23GcqqQQ2kqtwZPjpS8CdwtMv+pD+w9QeJ8T
pZ3j4K7ZVnOPis7s8rUinx7bgTDICk8e05gdPwNRVn5jNBtqn+o9bBEdepYz6dBg
gg1K5SQA3ZPT+MbyW7Xykk0jhi0cB/Jft9ODwG8/HoR4zDKAiJBVprLqVMuq0I4D
KerlR+hNrHuFZtI0FH6e+12XZ9NNxBDyxVKAlxVmZUB1xzPfGiXWxcJpaj1fga9G
yDn/e3lXHlGQaY48SrZdeVlDHAfBq13vFukRoEoetfAqfw0cn7t6Iy3qVs7h8HHz
SD0XpxVGH0w3qoTcUcV0ZCjmad2iuQ9M8Vvzoky628orxxXFD6FZprpfSscPCcoo
IVWk37LghwmpRJ6r2ZNzOaSuwcenygnF5JtIf2UzQexHXPu1Gf6q2WRs2h0cjz1H
q+HMsGUqU6by/rIfxmo9R1atnX22ZsMQFMg0Wd9EhdVs+YeGdpUjNZucCIv0+ze1
7EYQQPTKL3nl+2nRqVpz
=46qm
-----END PGP SIGNATURE-----
"""
	control_file = DebianControlFile()
	control_file.load_contents(contents=sample_control_file)
	print control_file
	print "------- Testing sample control file -----"
	print "Source: %s" % control_file['Source']
	print "Version: %s" % control_file.version()
	print "Upstream Version: %s" % control_file.upstream_version()
	print "Files:"
	for file in control_file.files_list():
		print "name: %s, size: %s, md5sum: %s" % (file.name, file.size, file.md5sum)        

