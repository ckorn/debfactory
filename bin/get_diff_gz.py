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
	p,d=choose_result(result)
	download(p, d)
	applyDiff(p, orig_file)
