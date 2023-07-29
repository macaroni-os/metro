#!/usr/bin/env python3

import json
import os
import socket

from bug_utils import JIRA


class JIRAHook:

	def __init__(self, settings):
		self.settings = settings
		jira_url = settings["qa/url"]
		jira_user = settings["qa/username"]
		jira_pass = settings["qa/password"]
		self.jira = JIRA(jira_url, jira_user, jira_pass)

	@property
	def bug_subject(self):
		# helper method -- return a subject for this particular bug.
		if "qa/prefix" in self.settings:
			prefix = f"{self.settings['qa/prefix']}: "
		else:
			prefix = " "
		return f"Metro: {prefix}({self.settings['target/subarch']}) {self.settings['target']} failure on {self.hostname}"

	@property
	def hostname(self):
		return socket.gethostname()

	def info(self):
		out = {}
		for x in ["build", "arch_desc", "subarch", "version"]:
			k = "target/" + x
			if x in self.settings:
				out[x] = self.settings[k]
		if "target" in self.settings:
			out["target"] = self.settings["target"]
		if "path/mirror/target/path" in self.settings:
			out["path"] = self.settings["path/mirror/target/path"]
			err_fn = out["path"] + "/log/errors.json"
			if os.path.exists(err_fn):
				a = open(err_fn, "r")
				out["failed_ebuilds"] = json.loads(a.read())
				a.close()
			build_log = out["path"] + "/log/build.log"
			if os.path.exists(build_log):
				out["build_log"] = build_log
		if "success" in self.settings:
			out["success"] = self.settings["success"]
		return out

	@property
	def all_matching(self):
		i = self.jira.get_all_issues(
			{'jql': 'Summary ~ "\\"%s\\"" and project = QA and status != closed' % self.bug_subject, 'maxresults': 1000})
		if i is not None and "issues" in i:
			return i["issues"]
		else:
			return []

	@property
	def existing_bug(self):
		# helper method -- does an existing bug for this build failure exist?
		return len(self.all_matching) != 0

	def on_failure(self):
		matching = self.all_matching
		info = self.info()
		if "build_log" in info:
			build_log_path = info["build_log"]
			del info["build_log"]
		else:
			build_log_path = None
		jira_key = None
		if not matching:
			# If one doesn't exist, create a new issue...
			jira_key = self.jira.create_issue(
				project='QA',
				title=self.bug_subject,
				description="A build failure has occurred. Details below:\n{code}\n" + json.dumps(self.info(), indent=4, sort_keys=True) + "\n{code}\n"
			)
			print(f"Created issue {jira_key}")
		else:
			# Update comment with new build failure info, to avoid creating a brand new bug.
			for match in matching:
				self.jira.comment_on_issue(
					match,
					"Another build failure has occurred. Details below:\n{code}\n" + json.dumps(self.info(), indent=4, sort_keys=True) + "\n{code}\n"
				)
				jira_key = match
				break
		if jira_key and build_log_path:
			self.jira.attach_build_log_to_issue(jira_key, build_log_path)

	def on_success(self):
		for i in self.all_matching():
			print("Closing matching issue %s" % i['key'])
			self.jira.comment_on_issue(
				i,
				"Build completed successfully. Closing. Details below:\n{code}\n" + json.dumps(self.info(), indent=4, sort_keys=True) + "\n{code}\n"
			)
			self.jira.close_issue(i)

	def run(self):
		if self.settings["success"] == "yes":
			return self.on_success()
		else:
			return self.on_failure()

# vim: ts=4 sw=4 noet
