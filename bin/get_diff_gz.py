#!/usr/bin/python
import glob
import os
import sys
from httplib import HTTPConnection
import re

def download(p,d):
	tmp = glob.glob('./' + p + '*.diff.gz')
	if tmp: return
	print 'wget -q ' + d
	os.system('wget -q ' + d)

def get_base_package_name():
	tmp = glob.glob('./*.orig.tar.gz')
	if not tmp:
		tmp = glob.glob('./*.orig.tar.bz2')
	if not tmp: return None
	return os.path.basename(tmp[0])

def search_on_getdeb(orig_file, release):
	http_connection = HTTPConnection('mirror.informatik.uni-mannheim.de')
	download_dir = 'http://mirror.informatik.uni-mannheim.de/pub/mirrors/getdeb/ubuntu/' + release + '/' + orig_file[0:2] + '/'
	http_connection.request('GET', download_dir)
	http_response = http_connection.getresponse()
	if http_response.status != 200: return None
	data = http_response.read()
	http_connection.close()
	data = data.split('\n')
	basename = orig_file.split('_')[0]
	package_lines = list()
	for line in data:
		if basename in line:
			package_lines.append(line)
	if len(package_lines) == 0: return None
	p_d = list()
	package_re = re.compile('<a .*?>(?P<orig>.*?)\.diff\.gz<')
	download_re = re.compile('<a href="(?P<download>.*?)">')
	for line in package_lines:
		search_result = re.search(package_re, line)
		if not search_result: continue
		orig = search_result.group('orig') 
		search_result = re.search(download_re, line)
		download = download_dir + search_result.group('download')
		p_d.append((orig,download))
	return p_d

def search_on_getdeb2(orig_file, release):
	http_connection = HTTPConnection('mirror.informatik.uni-mannheim.de')
	basename = orig_file.split('_')[0]
	download_dir = 'http://mirror.informatik.uni-mannheim.de/pub/mirrors/getdeb/ubuntu/pool/apps/' + orig_file[0] + \
	  '/' + basename + '/'
	http_connection.request('GET', download_dir)
	http_response = http_connection.getresponse()
	if http_response.status != 200: return None
	data = http_response.read()
	http_connection.close()
	data = data.split('\n')
	package_lines = list()
	for line in data:
		if basename in line:
			package_lines.append(line)
	if len(package_lines) == 0: return None
	p_d = list()
	package_re = re.compile('<a .*?>(?P<orig>.*?)(?:\.diff\.gz|\.debian\.tar\.gz)<')
	download_re = re.compile('<a href="(?P<download>.*?)">')
	for line in package_lines:
		search_result = re.search(package_re, line)
		if not search_result: continue
		orig = search_result.group('orig') 
		search_result = re.search(download_re, line)
		download = download_dir + search_result.group('download')
		p_d.append((orig,download))
	return p_d

def search_on_playdeb(orig_file, release):
	http_connection = HTTPConnection('mirror.informatik.uni-mannheim.de')
	basename = orig_file.split('_')[0]
	download_dir = 'http://mirror.informatik.uni-mannheim.de/pub/mirrors/getdeb/ubuntu/pool/games/' + orig_file[0] + \
	  '/' + basename + '/'
	http_connection.request('GET', download_dir)
	http_response = http_connection.getresponse()
	if http_response.status != 200: return None
	data = http_response.read()
	http_connection.close()
	data = data.split('\n')
	package_lines = list()
	for line in data:
		if basename in line:
			package_lines.append(line)
	if len(package_lines) == 0: return None
	p_d = list()
	package_re = re.compile('<a .*?>(?P<orig>.*?)(?:\.diff\.gz|\.debian\.tar\.gz)<')
	download_re = re.compile('<a href="(?P<download>.*?)">')
	for line in package_lines:
		search_result = re.search(package_re, line)
		if not search_result: continue
		orig = search_result.group('orig') 
		search_result = re.search(download_re, line)
		download = download_dir + search_result.group('download')
		p_d.append((orig,download))
	return p_d

def applyDiff(p,orig):
	package_name = orig.split('_')[0]
	version = orig.split('_')[1].split('.orig')[0]
	dir_name = package_name + '-' + version
	if not os.path.exists(dir_name):
		if orig.endswith(".gz"):
			print 'tar xzf ' + orig
			os.system('tar xzf ' + orig)
		else:
			print 'tar xjf ' + orig
			os.system('tar xjf ' + orig)
		if not os.path.exists(dir_name):
			tmp = glob.glob('./' + package_name + '*')
			for t in tmp:
				if os.path.isdir(t):
					os.rename(t, dir_name)
	if not os.path.exists(dir_name + '/debian'):
		tmp = glob.glob(p + '*.diff.gz')
		if tmp:
			print 'cd ' + dir_name + ' ; zcat ../' + p + '*.diff.gz | patch -p1 ; dch -D lucid --newversion "'+version+'-1~getdeb1" "New upstream version"'
			os.system('cd ' + dir_name + ' ; zcat ../' + p + '*.diff.gz | patch -p1 ; dch -D lucid --newversion "'+version+'-1~getdeb1" "New upstream version"')
		else:
			print 'cd ' + dir_name + ' ; tar xzf ../' + p + '*.debian.tar.gz ; dch -D lucid --newversion "'+version+'-1~getdeb1" "New upstream version"'
			os.system('cd ' + dir_name + ' ; tar xzf ../' + p + '*.debian.tar.gz ; dch -D lucid --newversion "'+version+'-1~getdeb1" "New upstream version"')

if __name__ == "__main__":
	orig_file = get_base_package_name()
	if not orig_file:
		print "No orig.tar.gz file has been found."
		sys.exit(1)

	if len(sys.argv) == 2:
		release = sys.argv[1]
	else:
		release = 'jaunty'

	result = search_on_getdeb(orig_file, release) or []
	result2 = search_on_playdeb(orig_file, release) or []
	result.extend(result2)
	result3 = search_on_getdeb2(orig_file, release) or []
	result.extend(result3)
	i = 0
	for r in result:
		p,d = r
		print i,p
		i += 1

	c = raw_input('Choose:')
	p,d = result[int(c)]
	download(p, d)
	applyDiff(p, orig_file)
