#!/usr/bin/python
import os
import sys

def getSourceFiles():
  find = os.popen("find . -name '*.h' -or -name '*.c' -or -name '*.cpp' -or -name '*.hpp' -or -name '*.cc'")
  files = find.readlines()
  stripped_files = list()
  for file in files:
    stripped_files.append(file.strip("\n"))
  return stripped_files

def getUniqHeadersInFiles(files):
  header_list = list()
  file_header_list = list()
  for file in files:
    f = open(file, 'r')
    for line in f.readlines():
      if line[0:8]=="#include":
        if line.find("<") != -1:
          dummy, header = line.split("<", 1)
          header, dummy = header.split(">", 1)
          header = header.strip()
          if not header in header_list:
            header_list.append(header)
            file_header_list.append((file,header))
    f.close()
  return file_header_list

def removeSkipHeaders(headers):
  newHeaders = list()
  skip = ["iostream", "string", "vector", "algorithm", "map", "fstream", "sstream", "new", "memory", "cstring", "string.h", "stdint.h", "assert.h", "math.h", "cmath", "cfloat", "cstdlib", "stdlib.h", "stdio.h", "climits", "execinfo.h", "signal.h", "exception", "pthread.h", "sys/ipc.h", "sys/shm.h", "unistd.h", "stddef.h", "pc.h", "limits.h", "config.h", "ctype.h", "fcntl.h", "sys/ioctl.h", "time.h", "linux/fb.h", "sys/mman.h", "sys/time.h"]
  for header in headers:
    if not header[1] in skip:
      newHeaders.append(header)
  return newHeaders

def isInStdLib(dev_lines):
  std_lib_found = 0
  for line in dev_lines:
    if line.find("libc6-dev") <> -1:
      std_lib_found = 1
  return std_lib_found

def getDevPackages(header):
  aptFile = os.popen("apt-file find "+header)
  files = aptFile.readlines()
  stripped_files = list()
  for file in files:
    stripped_files.append(file.strip("\r\n"))
  return stripped_files

def printDevs(devs):
  for i in range(len(devs)):
    dev = devs[i]
    print str(i) + ": " + dev

def chooseDevPackage(devs, current, nMax):
  chosenDev = raw_input('['+str(current)+'/'+str(nMax)+'] Choose the right dev Package [0:'+str(len(devs)-1)+'] or press [enter] to skip: ')
  if chosenDev == "": return None
  dev = devs[int(chosenDev)]
  dev, dummy = dev.split(":", 1)
  dev = dev.strip()
  return dev

def buildDepends(dev_list):
  builddeps = "Build-Depends: debhelper (>=6),"
  for i in range(len(dev_list)):
    builddeps+=" " + dev_list[i]

    if i < len(dev_list)-1:
      builddeps+=","

  print "\n\n\n"
  print builddeps

if __name__=="__main__":
  dev_list = list()
  files = getSourceFiles()
  file_header_list = getUniqHeadersInFiles(files)
#  file_header_list = removeSkipHeaders(file_header_list)

  print "Found "+str(len(file_header_list))+" unique headers."

  numHeaders = len(file_header_list)
  i = 1

  for file_header in file_header_list:
    print
    devs = getDevPackages(file_header[1])

    if len(devs) == 0:
      print "Warning: no dev package for header '" + file_header[1] + "' found!"
      con = raw_input('Continue (y/n)? ')
      if con=="n":
        sys.exit()
    else:
      if not isInStdLib(devs):
        printDevs(devs)
        print file_header[0],file_header[1]
        chosenDev = chooseDevPackage(devs, i, numHeaders)
        if chosenDev != None and not chosenDev in dev_list:
          dev_list.append(chosenDev)
      else:
        print "Header " + file_header[1] + " is in standard lib"

    i = i + 1

  buildDepends(dev_list)