import glob
import os
from httplib import HTTPConnection
import re
from subprocess import Popen, PIPE
import commands
import shutil
from functools import cmp_to_key
import tempfile

MIRROR_URL = "188.138.90.189"
GETDEB_SUBDIR = ""

def exe(c):
    print c
    os.system(c)

# If the package does not start with lib it is
# the first character. Else it is lib and the first character.
def get_package_subdir(orig):
    if orig.startswith('lib'):
        return orig[0:4]
    return orig[0]

def download(p,d, save_dir=None):
    tmp = glob.glob('./' + p + '*.diff.gz')
    if tmp: return
    c='wget -q ' + d
    if save_dir:
        c+= ' -P ' + save_dir
    exe(c)

def get_base_package_name():
    tmp = glob.glob('./*.orig.tar.gz')
    if not tmp:
        tmp = glob.glob('./*.orig.tar.bz2')
    if not tmp:
        tmp = glob.glob('./*.orig.tar.xz')
    if not tmp: return None
    return os.path.basename(tmp[0])

def search_on_mirror(basename, section):
    global MIRROR_URL, GETDEB_SUBDIR
    http_connection = HTTPConnection(MIRROR_URL)
    download_dir = 'http://' + MIRROR_URL + '/' + GETDEB_SUBDIR + '/ubuntu/pool/' + section + '/' + get_package_subdir(basename) + \
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
    package_re = re.compile('<a .*?>(?P<filename>(?P<orig>.*?)(?:\.diff\.gz|\.debian\.tar\.gz|\.debian\.tar\.bz2|\.debian\.tar\.xz))<')
    download_re = re.compile('<a href="(?P<download>.*?)">')
    for line in package_lines:
        search_result = re.search(package_re, line)
        if not search_result: continue
        orig = search_result.group('orig')
        filename = search_result.group('filename')
        search_result = re.search(download_re, line)
        download = download_dir + search_result.group('download')
        entry={ "shortname": orig, "filename": filename, "url": download }
        p_d.append(entry)
    return p_d

def untar(orig):
    if orig.endswith(".gz"): t = "z"
    elif orig.endswith(".bz2"): t = "j"
    elif orig.endswith(".xz"): t = "J"
    else: return
    s = 'tar x%(t)sf %(orig)s'%locals()
    exe(s)

def topLevelName(files):
    name = None
    for f in files:
        if f:
            cur = f.split("/", 1)
            # no top level dir. Just files?
            if cur[0] == f: return None
            if cur[0] != name:
                # init
                if name is None:
                    name = cur[0]
                # there is a different top level name
                # so the tarball does not have a top level dir
                else:
                    return None
    return name

def parseChangelogField(fieldname, changelogFile=None):
    args = ["dpkg-parsechangelog"]
    if changelogFile:
        args += ["-l", changelogFile]
    p1 = Popen(args, stdout=PIPE)
    p2 = Popen(["grep", "^%(fieldname)s:"%locals()], stdin=p1.stdout, stdout=PIPE)
    p3 = Popen(["sed", "s/^%(fieldname)s: //"%locals()], stdin=p2.stdout, stdout=PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    return p3.communicate()[0].strip("\r\n")

def applyDiff(p,orig):
    package_name = orig.split('_')[0]
    version = orig.split('_')[1].split('.orig')[0]
    dir_name = package_name + '-' + version
    tarType = None
    if orig.endswith(".gz"): tarType = "z"
    elif orig.endswith(".bz2"): tarType = "j"
    elif orig.endswith(".xz"): tarType = "J"
    else: return
    cwd = os.getcwd()
    if not os.path.exists(dir_name):
        # has the top-level directory the correct name
        # or is there any at all?
        p1 = Popen(["tar", "tf", orig], stdout=PIPE)
        top_level_dir = topLevelName(p1.communicate()[0].split("\n"))
        # no top level dir? create it, cd in it, untar, go back
        if top_level_dir is None:
            print "No top level dir. Creating: %(dir_name)s"%locals()
            os.mkdir(dir_name)
            os.chdir(os.path.join(cwd, dir_name))
            untar(os.path.join("..", orig))
            os.chdir(cwd)
        # top level dir has wrong name? untar and rename
        elif top_level_dir != dir_name:
            untar(orig)
            print "Top level dir has wrong name. Renaming: %(top_level_dir)s -> %(dir_name)s"%locals()
            os.rename(top_level_dir, dir_name)
        # all fine. top level dir exists and has correct name
        else:
            untar(orig)

    if os.path.exists(dir_name + '/debian'):
        shutil.rmtree(dir_name + '/debian')
        print "Warning! debian directory already existed. Removed."

    tmp = glob.glob(p + '*.diff.gz')

    if tmp:
        os.chdir(os.path.join(cwd, dir_name))
        print 'zcat ../' + p + '*.diff.gz | patch -p1'
        os.system('zcat ../' + p + '*.diff.gz | patch -p1')
    else:
        tmp = glob.glob(p + '*.debian.tar.gz')
        if tmp:
            os.chdir(os.path.join(cwd, dir_name))
            print 'tar xzf ../' + p + '*.debian.tar.gz'
            os.system('tar xzf ../' + p + '*.debian.tar.gz')
        else:
            tmp = glob.glob(p + '*.debian.tar.bz2')
            os.chdir(os.path.join(cwd, dir_name))
            if tmp:
                print 'tar xjf ../' + p + '*.debian.tar.bz2'
                os.system('tar xjf ../' + p + '*.debian.tar.bz2')
            else:
                print 'tar xJf ../' + p + '*.debian.tar.xz'
                os.system('tar xJf ../' + p + '*.debian.tar.xz')

    # Take the same release as the previous/current changelog entry
    release = parseChangelogField("Distribution")
    version_revision = parseChangelogField("Version")
    pre_epoch = version_revision.split(':', 1)
    revision = version_revision.rsplit('-', 1)[-1]
    if len(pre_epoch) > 1:
        epoch = pre_epoch[0] + ":"
    else:
        epoch = ""

    s = 'dch -D %(release)s --newversion "%(epoch)s%(version)s-%(revision)s" "New upstream version"'%locals()
    print s
    os.system(s)

    os.system("grep get-orig-source debian/rules >/dev/null && echo 'get-orig-source'")

    os.chdir(cwd)

def diffVersionCompare(a,b):
    v1 = a['shortname'].split("_")[1]
    v2 = b['shortname'].split("_")[1]
    com="dpkg --compare-versions '%s' lt '%s' "%(v1,v2)
    if v1==v2: return 0
    (rc, output) = commands.getstatusoutput(com)
    if rc == 0: return -1
    return 1

def get_mirror_results(basename):
    result = search_on_mirror(basename, "apps") or []
    result2 = search_on_mirror(basename, "games") or []
    result.extend(result2)
    result.sort(key=cmp_to_key(diffVersionCompare))
    return result

def choose_result(result):
    for i, e in enumerate(result):
        print i,e["shortname"]

    c = raw_input('Choose:')
    e = result[int(c)]
    return e

def choose_from_mirror(basename):
    result=get_mirror_results(basename)
    return choose_result(result)

def clean_dir(directory):
    for d in os.listdir(directory):
        if os.path.isfile(d):
            os.remove(d)
        else:
            shutil.rmtree(d)

def move_files(source, target):
    for s in os.listdir(source):
        src_file = os.path.join(source, s)
        dst_file = os.path.join(target, s)
        shutil.move(src_file, dst_file)

def apply_new_debian_dir(tmp_dir):
    debian_tarball=os.listdir(tmp_dir)[0]
    clean_dir('.')
    untar(os.path.join(tmp_dir, debian_tarball))
    move_files('./debian/', '.')
    os.rmdir('./debian')

def get_changelog(i, filename):
    changelog = file(filename, "r")
    current_changelog = 0
    changelog_dict = {'package' : '', 'version' : '', 'release' : '', 'bugs_to_be_closed' : [], 'changelog_entry' : ''}

    for line in changelog.readlines():
        line = line.strip('\r\n')
        if not line:
            if current_changelog == i:
                changelog_dict['changelog_entry'] += '\n'
            continue
        if not line.startswith(' '):
            current_changelog += 1
            if current_changelog == i:
                parts = line.split()
                changelog_dict['changelog_entry'] += line + '\n'
                changelog_dict['package'] = parts[0]
                changelog_dict['version'] = parts[1].strip('()')
                changelog_dict['release'] = parts[2].strip(';')
        if current_changelog > i:
            break
        if line.startswith('  ') and current_changelog == i:
            changelog_dict['changelog_entry'] += line + '\n'
        if line.startswith(' -- ') and current_changelog == i:
            changelog_dict['changelog_entry'] += line + '\n'

    line_matches = re.finditer('\(LP:\s*(?P<buglist>.+?\))', changelog_dict['changelog_entry'], re.DOTALL)
    for line_match in line_matches:
        bug_matches = re.finditer('#(?P<bugnum>\d+)', line_match.group('buglist'))
        for bug_match in bug_matches:
            bugnum = bug_match.group('bugnum')
            if not bugnum in changelog_dict['bugs_to_be_closed']:
                changelog_dict['bugs_to_be_closed'].append(bugnum)

    return changelog_dict

def getPackages(lines):
    packages = []
    package = {}
    description = ""
    empty = True
    for line in lines:
        line = line.strip("\n\r")
        if line == "":
            package["Description"] = description
            if not empty: packages.append(package)
            description = ""
            package = {}
            empty = True
        elif line.startswith(" "):
            empty = False
            description += line + "\n"
        else:
            parts=line.split(':', 1)
            package[parts[0]] = parts[1][1:]
            empty = False
    return packages


def getBinaryPackages(release, component, arch):
    global MIRROR_URL, GETDEB_SUBDIR
    http_connection = HTTPConnection(MIRROR_URL)
    # http://build.getdeb.net/ubuntu/dists/yakkety-getdeb-testing/apps/binary-amd64/Packages
    packagesFile = 'http://' + MIRROR_URL + '/' + GETDEB_SUBDIR + '/ubuntu/dists/' + release + '-getdeb-testing/' + component + '/binary-' + arch + '/Packages'
    http_connection.request('GET', packagesFile)
    http_response = http_connection.getresponse()
    if http_response.status != 200: return None
    data = http_response.read()
    http_connection.close()
    data = data.split('\n')
    binary_packages = getPackages(data)
    package_files = []
    for package in binary_packages:
        source = package.get("Source")
        if not source: source = package["Package"]
        # a package can exist in different versions
        exists=[x for x in package_files if x["Source"]==source and x["Version"] == package["Version"]]
        if len(exists) == 0:
            package_dict = {}
            package_dict["Source"] = source
            package_dict["Version"] = package["Version"]
            package_dict["Files"] = []
            package_files.append(package_dict)
        elif len(exists) == 1:
            package_dict = exists[0]
        else: assert False
        assert package["Version"] == package_dict["Version"], "%s: %s"%(package, package_dict)
        package_dict["Files"].append(package["Filename"])
    return package_files

def downloadPackages(files):
    for f in files:
        c='wget -q ' + 'http://' + MIRROR_URL + '/' + GETDEB_SUBDIR + '/ubuntu/' + f
        exe(c)

class MakeTempDir(object):
    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        return self.tempdir
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tempdir)
