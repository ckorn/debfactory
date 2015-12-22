#!/usr/bin/python
from common import *
import shutil
import sys

if __name__ == "__main__":
    if len(sys.argv) == 1:
        basename=raw_input("Enter basename: ")
    else:
        basename=sys.argv[1]
    e=choose_from_mirror(basename)
    download(e['shortname'], e['url'])
    untar(e['filename'])
    exe('uscan --download --rename --repack --compression xz --destdir .')
    shutil.rmtree('./debian')
    orig_file=get_base_package_name()
    applyDiff(e['shortname'], orig_file)
    os.remove(e['filename'])
