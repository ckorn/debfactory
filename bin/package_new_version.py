#!/usr/bin/python
from common import *
import shutil


if __name__ == "__main__":
    basename=raw_input("Enter basename: ")
    e=choose_from_mirror(basename)
    download(e['shortname'], e['url'])
    untar(e['filename'])
    exe('uscan --download --rename --repack --compression xz --destdir .')
    shutil.rmtree('./debian')
    orig_file=get_base_package_name()
    applyDiff(e['shortname'], orig_file)
    os.remove(e['filename'])