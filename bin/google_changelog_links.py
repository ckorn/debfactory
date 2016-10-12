#!/usr/bin/python3
import sys
import os
import json
from git import Repo
from pathlib import Path
from getchangelog import getChangelog

SETTINGS_FILE = "~/.config/google_changelog_links.json"

class Data:
	pass

def loadSettings():
	global SETTINGS_FILE
	settings_file=Path(os.path.expanduser(SETTINGS_FILE))
	if settings_file.is_file():
		return json.loads(settings_file.read_text())
	return {}

def saveSettings(settings):
	global SETTINGS_FILE
	json_settings = json.dumps(settings, sort_keys=True, indent=4, separators=(',', ': '))
	settings_file=Path(os.path.expanduser(SETTINGS_FILE))
	settings_file.write_text(json_settings)

def getRelevantCommits(repo, branch, since, skipFirst):
	log = list(repo.iter_commits(branch, max_count=50))
	relevant = []
	found = False
	for commit in log:
		relevant.append(commit)
		if commit.hexsha == since:
			found = True
			break
	if found:
		# start with oldest first
		relevant.reverse()
		if skipFirst: relevant = relevant[1:]
		return relevant
	return []

def getURL(settings, package):
	url = settings.get(package)
	if url is None:
		url=input("Enter URL for package '%(package)s': "%(locals()))
		if len(url) > 0:
			settings[package] = url
			saveSettings(settings)
		else:
			return None
	return url

def getRepoPath():
	start = Path(os.path.abspath(os.path.curdir))
	git = start.joinpath(".git")
	while not git.is_dir() and str(start) != "/":
		start = start.parent
		git = start.joinpath(".git")
	return str(start)

def getSinceKey(repoDir):
	return "since-" + repoDir

def getSince(settings, repoDir):
	x = Data()
	x.sinceFromSettings = False
	if len(sys.argv) == 2:
		x.since = sys.argv[1]
	else:
		x.since = settings.get(getSinceKey(repoDir))
		x.sinceFromSettings = True
	return x

def main():
	settings = loadSettings()
	repoDir = getRepoPath()
	dataSince = getSince(settings, repoDir)
	if dataSince.since is None: return -1
	os.chdir(repoDir)
	repo = Repo(repoDir)
	relevant = getRelevantCommits(repo, repo.active_branch.name, dataSince.since, dataSince.sinceFromSettings)
	for commit in relevant:
		files = [x for x in commit.stats.files.keys()]
		for changelog in files:
			if changelog.endswith("/changelog"):
				package = changelog.split(sep='/', maxsplit=1)[0]
				url = getURL(settings, package)
				if url is not None:
					getChangelog(changelog, True, True, url, False, None, False, True)
					settings[getSinceKey(repoDir)] = commit.hexsha
					saveSettings(settings)
					input("Enter to continue")

if __name__ == "__main__":
	main()
