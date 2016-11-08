#!/usr/bin/python
import sys
from common import *


def main():
    if len(sys.argv) < 2:
        print "Usage: "+sys.argv[0]+" changelog [arch]"
        sys.exit(1)
    arch="amd64"
    if len(sys.argv) == 3: arch=sys.argv[2]
    changelog=sys.argv[1]
    changelog_dict=get_changelog(1, changelog)
    source=changelog_dict['package']
    version=changelog_dict['version']
    release=changelog_dict['release']
    #source=parseChangelogField("Source", changelog)
    #version=parseChangelogField("Version", changelog)
    #release=parseChangelogField("Distribution", changelog)
    binary_packages = getBinaryPackages(release, "apps", arch)
    package = [x for x in binary_packages if x["Source"]==source and x["Version"]==version]
    if len(package) == 0:
        binary_packages = getBinaryPackages(release, "games", arch)
        package = [x for x in binary_packages if x["Source"]==source and x["Version"]==version]
    assert len(package) == 1, "Not found"
    package=package[0]
    downloadPackages(package["Files"])


if __name__ == "__main__":
    main()
