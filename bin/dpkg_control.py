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
			
    class MissingBaseDirError(Exception):
        def __init__(self, value):
            self.value = value

    class FileNotFoundError(Exception):
        def __init__(self, filename):
            self.filename = filename
        def __str__(self):
            return repr(self.filename)

    class MD5Error(Exception):
        def __init__(self, expected_md5, found_md5, name):
            self.expected_md5 = expected_md5
            self.found_md5 = found_md5
            self.name = name
        def __str__(self):
            return repr(self.value1, self.value2, self.value3)


    def __init__(self, filename=None):
        self._filename = filename		
        if filename is not None:
            self.load_contents(filename)
			
    def load_contents(self, filename=None, contents=None):
        """
        Opens the control file and load it's contents into the data
        attribute.
        """
        self._data = []
        self._deb_info = {}
        if filename is not None:
            if filename[0] != "/":
                raise self.MissingBaseDirError('Needs full pathname')
                return
            self._filename = filename
            control_file = open(self._filename, 'r')
            self._data = control_file.readlines()
            control_file.close()
        if contents is not None:
            self._data = contents.split("\n")
        ast_data = []
        deb_info = {}
        for line in self._data:
			#print "Line: %s" % line
			if not line:
				continue
			if line == '-----BEGIN PGP SIGNATURE-----':
				break
			if line[0] == " ":
				last_data.append(line.strip("\r\n "))
			else:
				(field, sep, value) = line.partition(": ") 
				if not sep == ": ":
					continue
				value = value.strip("\r\n")
#				print "Field:", field, ":", value            
				if field not in deb_info:
					if value:
						deb_info[field] = value
					else:
						last_data = []
						deb_info[field] = last_data
        self._deb_info = deb_info
		
    def files_list(self):
		files = self['Files']
		file_info_list = []
		for file in files:
			file_parts = file.split(" ")
			file_info = self.FileInfo(file_parts[0], file_parts[1], \
				file_parts[len(file_parts)-1])
			file_info_list.append(file_info)
		return file_info_list
	
    def verify_gpg(self, keyring, verbose=False):
		"""
		Verify the file GPG signature using the specified keyring file.
		Returns:
			signature author on success
			None on failure
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
		
    def verify_md5sum(self, basedir=None):
		"""
		Verify the MD5 checksum for all the files
		Returns:
			None: on success
			(expected_md5, found_md5, filename): on failure
		"""
		basedir = basedir or os.path.dirname(self._filename)
		for file in self.files_list():
			full_filename = "%s/%s" % (basedir, file.name)
			if not os.path.exists(full_filename):
				return (file.md5sum, "FILE_NOT_FOUND", file.name)
			else:
				md5sum=commands.getoutput("md5sum %s" % full_filename)								
				(found_md5, dummy) = md5sum.split()
				if found_md5 != file.md5sum:
					return (file.md5sum, found_md5, file.name)
		return None	
        
    def copy(self, targetdir=None, sourcedir=None, md5check=True):
        """
        Copies the files listed on the control file
        The control file is also copied at the end
        """
        sourcedir = sourcedir or os.path.dirname(self._filename)
        if not os.path.isdir(targetdir):
            raise Exception
            return
            
        file_list = self.files_list()
        file_list.append(self.FileInfo(None, None, \
            os.path.basename(self._filename)))
        for file in file_list:
            source_filename = "%s/%s" % (sourcedir, file.name)
            target_filename = "%s/%s" % (targetdir, file.name)
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

    def move(self, targetdir=None, sourcedir=None, md5check=True):
        """
        Moves the files listed on the control file
        The control file is also moved at the end
        Returns:
			None: on success
			(expected_md5, found_md5, filename): on failure
        """
        sourcedir = sourcedir or os.path.dirname(self._filename)
        if not os.path.isdir(targetdir):
            raise Exception
            return

        file_list = self.files_list()
        file_list.append(self.FileInfo(None, None, \
            os.path.basename(self._filename)))
        for file in file_list:
            source_filename = "%s/%s" % (sourcedir, file.name)
            target_filename = "%s/%s" % (targetdir, file.name)
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

    def remove(self, basedir=None):
        """
        Removes all files listed and the control file itself
        Returns:
	        None: on success
	        (expected_md5, found_md5, filename): on failure
        """
        basedir = basedir or os.path.dirname(self._filename)
        
        file_list = self.files_list()
        file_list.append(self.FileInfo(None, None, \
            os.path.basename(self._filename)))
        for file in file_list:
            full_filename = "%s/%s" % (basedir, file.name)
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
Hash: SHA1

Format: 1.0
Source: pybackpack
Binary: pybackpack
Architecture: all
Version: 0.5.6-1
Maintainer: Andy Price <andy@andrewprice.me.uk>
Uploaders: Python Applications Packaging Team <python-apps-team@lists.alioth.debian.org>
Homepage: http://andrewprice.me.uk/projects/pybackpack/
Standards-Version: 3.8.0
Vcs-Browser: http://svn.debian.org/wsvn/python-apps/packages/pybackpack/?op=log
Vcs-Svn: svn://svn.debian.org/python-apps/packages/pybackpack/trunk/
Build-Depends: cdbs, debhelper (>= 5), python-support (>= 0.3), python-dev
Checksums-Sha1: 
 5ea70dfc4c3c204b24ffe7efba852f10464322db 116514 pybackpack_0.5.6.orig.tar.gz
 2b2cf9fcf2d565dca921b8324c34337cbd244752 2254 pybackpack_0.5.6-1.diff.gz
Checksums-Sha256: 
 58f7680d9032799303b374d36996ca020415edf2474e95ca1ca90fe73b297d12 116514 pybackpack_0.5.6.orig.tar.gz
 59e4221b35941ed4da9ea97112f1e2361555ab3d43125a09a887d9bd3850dd60 2254 pybackpack_0.5.6-1.diff.gz
Files: 
 63d787dd207b150e0c258f7fe50f0477 116514 pybackpack_0.5.6.orig.tar.gz
 1d204c04b188f637dce0c5e4b085a67f 2254 pybackpack_0.5.6-1.diff.gz

-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.9 (GNU/Linux)

iEYEARECAAYFAkjdYrAACgkQB01zfu119ZmFHwCfeu2a9zvHjmzXwBfi6stkmQVs
bDAAn0Q2qf3no3vO1piw5uhwMbIul6Kb
=74wC
-----END PGP SIGNATURE-----
"""
    control_file = DebianControlFile()
    control_file.load_contents(contents=sample_control_file)
    print "------- Testing sample control file -----"
    print "Source: %s" % control_file['Source']
    print "Files:"
    for file in control_file.files_list():
		print "name: %s, size: %s, md5sum: %s" % (file.name, file.size, file.md5sum)        

