#!/usr/bin/python3
import sys
import os
import json
from git import Repo
from pathlib import Path
from getchangelog import getChangelog

SETTINGS_FILE = "~/.config/google_changelog_links.json"

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

def getRelevantCommits(repo, branch, since):
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

def main():
	since = sys.argv[1]
	repo = Repo(os.path.abspath(os.path.curdir))
	relevant = getRelevantCommits(repo, repo.active_branch.name, since)
	settings = loadSettings()
	for commit in relevant:
		files = [x for x in commit.stats.files.keys()]
		for changelog in files:
			if changelog.endswith("/changelog"):
				package = changelog.split(sep='/', maxsplit=1)[0]
				url = getURL(settings, package)
				if url is not None:
					getChangelog(changelog, True, True, url, False, None, False, True)
					input("Enter to continue")

if __name__ == "__main__":
	main()
