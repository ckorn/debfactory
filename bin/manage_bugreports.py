#!/usr/bin/python
#
#    (C) Copyright 2009, GetDeb Team - https://launchpad.net/~getdeb
#    --------------------------------------------------------------------
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#    --------------------------------------------------------------------

# To setup the LP API Access you have to launch this:
#import os
#import sys
#home = os.environ['HOME']
#cachedir = home + '/.launchpadlib/cache/'
#from launchpadlib.launchpad import Launchpad, EDGE_SERVICE_ROOT
#launchpad = Launchpad.get_token_and_login('GetDeb.net Bug Manager', EDGE_SERVICE_ROOT, cachedir)
#launchpad.credentials.save(file("some-file.txt", "w"))


import os
import sys
import re
from launchpadlib.launchpad import Launchpad, EDGE_SERVICE_ROOT
from launchpadlib.credentials import Credentials

LP_BUGS = re.compile("\(LP: #([0-9]+)\)")

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
			bugs = LP_BUGS.findall(line)
			for bug in bugs: changelog_dict['bugs_to_be_closed'].append(bug)
		if line.startswith(' -- ') and current_changelog == i:
			changelog_dict['changelog_entry'] += line + '\n'

	return changelog_dict

def check_not_empty(bugs):
	if len(bugs) == 0:
		print "No bugs found to fix"
		sys.exit(3)


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Usage: "+sys.argv[0]+" s[tart] | b[uild] | t[ested] [jaunty|hardy].[amd64|i386] | r[eleased]"
		sys.exit(1)

	changelog = 'debian/changelog'

	if not os.path.exists(changelog):
		print "File "+changelog+" not found"
		sys.exit(2)

	home = os.environ['HOME']
	cachedir = home + '/.launchpadlib/cache/'

	launchpad_key = home + "/.launchpadlib/key.txt"

	credentials = Credentials()
	credentials.load(open(launchpad_key))
	launchpad = Launchpad(credentials, EDGE_SERVICE_ROOT, cachedir)

	me = launchpad.me

	project_name = "GetDeb Software Portal"

	if sys.argv[1] == 'start' or sys.argv[1].startswith('s'):
		current_changelog = get_changelog(1, changelog)
		previous_changelog = get_changelog(2, changelog)

		bug_ids = current_changelog['bugs_to_be_closed']
		check_not_empty(bug_ids)

		for bug_id in bug_ids:
			bug = launchpad.bugs[bug_id]
			subject_text = "Re: " + bug.title

			wrote_task = False

			for task in bug.bug_tasks:
				if task.bug_target_display_name == project_name:
					wrote_task = True
					task.transitionToImportance(importance="Medium")
					task.transitionToStatus(status="In Progress")
					task.transitionToAssignee(assignee=me)

			if wrote_task:
				if previous_changelog['version'] == '':
					bug.newMessage(content="Starting from scratch.", \
					 subject=subject_text)
				else:
					bug.newMessage(content="Taking " + previous_changelog['package'] \
					 + " " + previous_changelog['version'] + " as starting point.", \
					 subject=subject_text)
	elif sys.argv[1] == 'build' or sys.argv[1].startswith('b'):
		current_changelog = get_changelog(1, changelog)
		bug_ids = current_changelog['bugs_to_be_closed']
		check_not_empty(bug_ids)

		for bug_id in bug_ids:
			bug = launchpad.bugs[bug_id]
			subject_text = "Re: " + bug.title

			wrote_task = False

			for task in bug.bug_tasks:
				if task.bug_target_display_name == project_name:
					wrote_task = True
					task.transitionToStatus(status="Fix Committed")

			if wrote_task:
				bug.newMessage(content="Package has been built for " + current_changelog['release'] + ".", \
				  subject=subject_text)
	elif sys.argv[1] == 'tested' or sys.argv[1].startswith('t'):
		if len(sys.argv) < 3:
			print "The release the package has been tested for is missing."
			sys.exit(4)

		current_changelog = get_changelog(1, changelog)
		bug_ids = current_changelog['bugs_to_be_closed']
		check_not_empty(bug_ids)

		for bug_id in bug_ids:
			bug = launchpad.bugs[bug_id]
			has_task = False

			for task in bug.bug_tasks:
				if task.bug_target_display_name == project_name:
					has_task = True

			if has_task:
				tags = bug.tags
				tags.append('tested-' + sys.argv[2])
				bug.tags = tags
				bug.lp_save()
	elif sys.argv[1] == 'released' or sys.argv[1].startswith('r'):
		current_changelog = get_changelog(1, changelog)
		bug_ids = current_changelog['bugs_to_be_closed']
		check_not_empty(bug_ids)

		for bug_id in bug_ids:
			bug = launchpad.bugs[bug_id]
			subject_text = "Re: " + bug.title
			wrote_task = False

			for task in bug.bug_tasks:
				if task.bug_target_display_name == project_name:
					wrote_task = True
					task.transitionToStatus(status="Fix Released")

			if wrote_task:
				bug.newMessage(content="Published.\n\nThanks.\n\n\n" + \
				 "---------------\n" + \
				 current_changelog['changelog_entry'].strip('\r\n'), \
				 subject=subject_text)