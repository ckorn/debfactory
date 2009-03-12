#!/usr/bin/python
import sys
import os
import shutil

absDir="/export/abs"

def askToContinue():
  con = raw_input('Continue (y/n)? ')
  if con=="n":
    sys.exit()

def printChangeLog(dsc):
  source = dsc.replace(".dsc", "_source.changes")
  f=open(source, 'r')
  inchanges = 0
  counter = 0
  for line in f.readlines():
    line = line.strip('\r\n')
    if inchanges and line[0]!=" ": break
    if line[0:8]=="Changes:":
       inchanges = 1
    elif inchanges:
       if counter < 2:
         counter = counter + 1
       else:
         print line
  f.close()

def callCreateUpdate(dsc):
  os.system('update_create.py ' + dsc)

def getUpdateFile(dsc):
  update = dsc.replace(".dsc", ".update")
  return update

def getUpdateDir():
  release = os.path.basename(os.getcwd())
  return absDir+"/updates/"+release

def moveUpdate(update):
  updateDir=getUpdateDir()
  shutil.move(update, updateDir)

def callMoveToReady(dsc):
  os.system('move_to_ready.py ' + dsc)
  

if __name__=="__main__":
  if len(sys.argv) != 2:
    print "Usage: "+sys.argv[0]+" dsc"
    sys.exit(2)

  dsc = sys.argv[1]

  printChangeLog(dsc)
  askToContinue()
  callCreateUpdate(dsc)
  print ".update file created. Move to updates directory?"
  askToContinue()
  moveUpdate(getUpdateFile(dsc))
  print ".update file moved. run move_to_ready?"
  askToContinue()
  callMoveToReady(dsc)
