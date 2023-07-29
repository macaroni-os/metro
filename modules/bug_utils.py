#!/usr/bin/python3

import base64
import json
import os
from datetime import datetime

import requests


def gen_base64(username, password):
	d_b_encode = f"{username}:{password}"
	d_encode = bytes(d_b_encode, "utf-8")
	b_d_encode = base64.encodebytes(d_encode).decode("utf-8")[:-1]
	return b_d_encode


class JIRA:

	def __init__(self, url, user, password):
		self.url = url
		self.user = user
		self.password = password

	def get_auth(self):
		base64string = gen_base64(self.user, self.password)
		return "Basic %s" % base64string

	def get_all_issues(self, params=None):
		if params is None:
			params = {}
		url = self.url + '/search'
		r = requests.get(url, params=params)
		if r.status_code == requests.codes.ok:
			return r.json()
		return None

	def create_issue(self, project, title, description, issue_type="Bug", extra_fields=None):
		if extra_fields is None:
			extra_fields = {}
		url = self.url + '/issue/'
		headers = {"Content-type": "application/json", "Accept": "application/json", "Authorization": self.get_auth()}
		issue = {"fields": {
			'project': {'key': project},
			'summary': title,
			'description': description,
			'issuetype': {'name': issue_type}
		}
		}
		issue["fields"].update(extra_fields)
		r = requests.post(url, data=json.dumps(issue), headers=headers)
		try:
			j = r.json()
		except ValueError:
			print("createIssue: Error decoding JSON from POST. Possible connection error.")
			return None
		issue_key = j['key']
		return issue_key

	def create_subtask(self, parent_key, project, title, description):
		return self.create_issue(project=project, title=title, description=description, issue_type="Sub-task", extra_fields={'parent': parent_key})

	def close_issue(self, issue, comment=None, resolution='Fixed'):
		url = self.url + '/issue/' + issue['key'] + '/transitions'
		headers = {"Content-type": "application/json", "Accept": "application/json", "Authorization": self.get_auth()}
		data = {'update': {'comment':
			[
				{'add': {'body': comment or 'Closing ' + issue['key']}}
			]
		}, 'fields': {'resolution': {'name': resolution}}, 'transition': {'id': 831}}
		r = requests.post(url, data=json.dumps(data), headers=headers)
		if r.status_code == requests.codes.ok:
			return True
		else:
			return False

	def comment_on_issue(self, issue, comment):
		url = self.url + '/issue/' + issue['key'] + '/comment'
		headers = {"Content-type": "application/json", "Accept": "application/json", "Authorization": self.get_auth()}
		data = {'body': comment}
		r = requests.post(url, data=json.dumps(data), headers=headers)
		if r.status_code == requests.codes.ok:
			return True
		else:
			return False

	def create_xz_build_log(self, build_log_path):
		"""For uploading a build log to JIRA, we want to timestamp it as well as xz compress the log for space savings."""
		date = datetime.strftime(datetime.now(), "%Y-%m-%d:%H:%M:%S")
		for cmd in [
			f"cp {build_log_path} /var/tmp/build-{date}.log",
			f"xz -9 /var/tmp/build-{date}.log"
		]:
			retval = os.system(cmd)
			if retval != 0:
				raise SystemError(f"Command failure: {cmd}; exit value: {retval}")
		return f"/var/tmp/build-{date}.log.xz"

	def attach_build_log_to_issue(self, issue, build_log_path):
		headers = {"Content-type": "application/json", "Accept": "application/json", "Authorization": self.get_auth()}

		xz_log_path = self.create_xz_build_log(build_log_path)
		files = {'file': open(xz_log_path, 'rb')}
		os.unlink(xz_log_path)

		url = self.url + f"/issue/{issue['key']}/attachments"
		r = requests.post(
			url=url,
			headers=headers,
			files=files,
		)
		if r.status_code == requests.codes.ok:
			return True
		else:
			return False

	def close_duplicate_issue(self, orig_issue, dup_issue):
		url = self.url + '/issue/' + dup_issue['key'] + '/transitions'
		headers = {"Content-type": "application/json", "Accept": "application/json", "Authorization": self.get_auth()}
		data = {'update': {'comment':
			[
				{'add': {'body': 'Duplicate of %s' % orig_issue['key']}}
			]
		}, 'fields': {'resolution': {'name': 'Duplicate'}}, 'transition': {'id': 831}}
		r = requests.post(url, data=json.dumps(data), headers=headers)
		if r.status_code == requests.codes.ok:
			return True
		else:
			return False

# vim: ts=4 sw=4 noet
