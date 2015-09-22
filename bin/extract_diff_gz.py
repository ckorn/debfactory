#!/usr/bin/python
from common import *
import os
import sys

if __name__ == "__main__":
    # the current directory has to be empty or it has to be an extracted debian directory
    dir_ok = (len(os.listdir('.')) == 0)
    dir_ok = dir_ok or (os.path.isfile('changelog') and os.path.isfile('control') and os.path.isfile('rules'))
    if not dir_ok:
        print "Current dir not empty and no debian directory"
        sys.exit(1)
    # basename of the package is the name of the current directory
    basename=os.path.split(os.getcwd())[1]
    with MakeTempDir() as tmp_dir:
        result=get_mirror_results(basename)
        p,d=choose_result(result)
        download(p,d,tmp_dir)
        apply_new_debian_dir(tmp_dir)
    exe('git add .')
    exe('git diff --staged')