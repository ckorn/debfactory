#!/usr/bin/python
import sys
from common import *

if __name__ == "__main__":
	orig_file = get_base_package_name()
	if not orig_file:
		print "No orig.tar.gz file has been found."
		sys.exit(1)
	basename = orig_file.split('_')[0]
	result=get_mirror_results(basename)
	e=choose_result(result)
	download(e['shortname'], e['url'])
	applyDiff(e['shortname'], orig_file)
