#!/usr/bin/python3

import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
import time
from importlib import import_module

from flexdata import Collection


def ismount(path):
	"""enhanced to handle bind mounts"""
	if os.path.ismount(path):
		return 1
	a = os.popen("mount")
	mylines = a.readlines()
	a.close()
	for line in mylines:
		mysplit = line.split()
		if os.path.normpath(path) == os.path.normpath(mysplit[2]):
			return 1
	return 0


class MetroError(Exception):
	def __init__(self, *args):
		self.args = args

	def __str__(self):
		if len(self.args) == 1:
			return str(self.args[0])
		else:
			return "(no message)"


class MetroSetup(object):

	def __init__(self, verbose=False, debug=False):

		self.debug = debug
		self.verbose = verbose

		self.flexdata = import_module("flexdata")
		self.targets = import_module("targets")
		self.configfile = None

	def get_settings(self, args=None, extraargs=None):

		if args is None:
			args = {}

		self.configfile = os.path.expanduser("~/.metro")
		# config settings setup

		if self.verbose:
			print("Using main configuration file %s.\n" % self.configfile)
		settings = self.flexdata.Collection(self.debug)

		if os.path.exists(self.configfile):
			settings.collect(self.configfile, None)
			settings["path/config"] = os.path.dirname(self.configfile)
		else:
			raise RuntimeError("config file '%s' not found\nPlease copy %s to ~/.metro and customize for your environment." %
				(self.configfile, (os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/metro.conf")))

		for key, value in list(args.items()):
			if key[-1] == ":":
				settings[key[:-1]] = value
			else:
				raise RuntimeError("cmdline argument '%s' invalid - does not end in a colon" % key)

		# add extra values
		if extraargs:
			for arg in list(extraargs.keys()):
				settings[arg] = extraargs[arg]
		settings.run_collector()
		if settings["portage/MAKEOPTS"] == "auto":
			settings["portage/MAKEOPTS"] = "-j%s" % (int(subprocess.getoutput("nproc --all")) + 1)

		return settings


class CommandRunner:

	"""CommandRunner is a class that allows commands to run, and messages to be displayed. By default, output will go to a log file.
	Messages will appear on stdout and in the logs."""

	def __init__(self, settings: Collection = None, logging=True):
		self.settings = settings
		self.logging = logging
		if self.settings and self.logging:
			self.fname = self.settings["path/mirror/target/path"] + "/log/" + self.settings["target"] + ".txt"
			if not os.path.exists(os.path.dirname(self.fname)):
				# create output directory for logs
				self.logging = False
				self.run(
					["install", "-o", self.settings["path/mirror/owner"], "-g", self.settings["path/mirror/group"], "-m",
					self.settings["path/mirror/dirmode"], "-d", os.path.dirname(self.fname)], {}
				)
				self.logging = True
			self.cmdout = open(self.fname, "w+")
			# set logfile ownership:
			os.chown(self.fname, pwd.getpwnam(self.settings["path/mirror/owner"]).pw_uid, grp.getgrnam(self.settings["path/mirror/group"]).gr_gid)
			sys.stdout.write("Logging output to %s.\n" % self.fname)

	def mesg(self, msg):
		if self.logging:
			self.cmdout.write(msg + "\n")
			self.cmdout.flush()
		sys.stdout.write(msg + "\n")

	def extract_build_log_path(self):
		"""
		Scan metro build log and extract the full path to the build.log of the failed package.
		"""
		prefix = " * The complete build log is located at "
		s, out = subprocess.getstatusoutput(
			f'tac {self.fname} | grep -m 1 -E "^ \\* The complete build log is located at"'
		)
		if s != 0:
			raise SystemError("Couldn't run tac on build log.")
		line = out.strip()
		line = line[len(prefix):]
		if line.endswith("."):
			line = line[:-1]
		line = line.strip("'")
		line = line.lstrip("/")
		full_build_log_path = os.path.join(self.settings["path/work"], line)
		# Copy the found build.log, so it sits next to errors.json in the metro logs dir:
		shutil.copy(full_build_log_path, os.path.join(self.settings["path/mirror/target/path"], "log/build.log"))

	def extract_build_log_catpkg(self):
		"""
		Scan metro build log and extract the actual package the failed, along with associated metadata.
		"""
		s, out = subprocess.getstatusoutput(
			f'cat {self.fname} | grep "^ \\* ERROR: " | sort -u | sed -e \'s/^ \\* ERROR: \\(.*\\) failed (\\(.*\\) phase).*/\\1 \\2/g\'')
		if s == 0:
			errors = []
			for line in out.split('\n'):
				parts = line.split()
				if len(parts) != 2:
					# not what we're looking for
					continue
				if len(parts[0].split("/")) != 2:
					continue
				errors.append({"ebuild": parts[0], "phase": parts[1]})
			if len(errors):
				fname = os.path.join(self.settings["path/mirror/target/path"], "log/errors.json")
				self.mesg("Detected failed ebuilds... writing to %s." % fname)
				a = open(fname, "w")
				a.write(json.dumps(errors, indent=4))
				a.close()

	def do_error_scan(self):
		# scan log for errors -- and extract them!
		self.mesg("Attempting to extract failed ebuild information...")
		if self.cmdout:
			self.cmdout.flush()
		self.extract_build_log_catpkg()
		self.extract_build_log_path()

	def run(self, cmdargs, env, error_scan=False):
		self.mesg("Running command: %s (env %s) " % (cmdargs, env))
		cmd = None
		try:
			if self.logging:
				cmd = subprocess.Popen(cmdargs, env=env, stdout=self.cmdout, stderr=subprocess.STDOUT)
			else:
				cmd = subprocess.Popen(cmdargs, env=env)
			exitcode = cmd.wait()
		except KeyboardInterrupt:
			cmd.terminate()
			self.mesg("Interrupted via keyboard!")
			raise
		else:
			if exitcode != 0:
				self.mesg("Command exited with return code %s" % exitcode)
				if error_scan and self.logging:
					self.do_error_scan()
			return exitcode


class StampFile:

	def __init__(self, path):
		self.path = path
		self._created = False

	def create(self):
		self._created = True

	def exists(self):
		return os.path.exists(self.path)

	def get(self):
		if not os.path.exists(self.path):
			return False
		with open(self.path, "r") as inf:
			return inf.read()

	def unlink(self):
		try:
			if os.path.exists(self.path):
				os.unlink(self.path)
		except FileNotFoundError:
			pass

	def wait(self, seconds):
		elapsed = 0
		while os.path.exists(self.path) and elapsed < seconds:
			sys.stderr.write(".")
			sys.stderr.flush()
			time.sleep(5)
			elapsed += 5
		if os.path.exists(self.path):
			return False
		return True

	def gen_file_contents(self):
		return ""


class LockFile(StampFile):

	"""Class to create lock files; used for tracking in-progress metro builds."""

	def __init__(self, path):
		super().__init__(path)
		self.hostname = subprocess.getoutput("/bin/hostname")

	def _from_file(self):
		data = self.get()
		if data is False:
			return None
		return data.split(":")

	@property
	def hostname_from_file(self):
		file_dat = self._from_file()
		if file_dat is None:
			return None
		if len(file_dat) != 2:
			return None
		return file_dat[0]

	@property
	def pid_from_file(self):
		file_dat = self._from_file()
		if file_dat is None:
			return None
		if len(file_dat) != 2:
			return None
		return int(file_dat[1])

	@property
	def created_by_this_host(self) -> bool:
		return self.hostname_from_file == self.hostname

	@property
	def created_by_me(self) -> bool:
		if self.hostname_from_file == self.hostname and self.pid_from_file == os.getpid():
			return True
		else:
			return False

	@property
	def pid_exists(self) -> bool:
		my_pid = self.pid_from_file
		if my_pid is not None:
			try:
				os.kill(my_pid, 0)
				return True
			except OSError:
				pass
		return False

	def create(self):
		if self.exists():
			return False
		try:
			out = open(self.path, "w")
		except IOError:
			return False
		out.write(self.gen_file_contents())
		out.close()
		self._created = True
		return True

	def exists(self):
		if os.path.exists(self.path):
			if not self.created_by_this_host:
				sys.stderr.write("# Currently locked by %s, pid %s\n" % (self.hostname_from_file, self.pid_from_file))
				return True
			elif not self.pid_exists:
				sys.stderr.write("# Removing stale lock file: %s\n" % self.path)
				self._unlink()
				return False
			else:
				return True
		else:
			return False

	def _unlink(self):
		super().unlink()

	def unlink(self, force=False):
		"""only unlink if *we* (hostname, pid) created the file. Otherwise, leave alone."""
		do_unlink = False
		if os.path.exists(self.path):
			if not self.created_by_this_host:
				if force is False:
					sys.stderr.write("Won't unlink pidfile -- it was created by host %s!\n" % self.hostname_from_file)
				else:
					do_unlink = True
			elif self.created_by_me:
				# not only from this host, but our pid created it. So we own it, and can remove it.
				do_unlink = True
		if do_unlink:
			super().unlink()

	def gen_file_contents(self):
		mypid = os.getpid()
		return "%s:%s" % (self.hostname, mypid)


class CountFile(StampFile):

	"""Class to record fail count for builds."""

	@property
	def count(self):
		try:
			f = open(self.path, "r")
			d = f.readlines()
			return int(d[0])
		except (IOError, ValueError):
			return None

	def increment(self):
		try:
			count = self.count
			if count is None:
				count = 0
			count += 1
			f = open(self.path, "w")
			f.write(str(count))
			f.close()
		except (IOError, ValueError):
			return None


if __name__ == "__main__":
	pass

# vim: ts=4 sw=4 noet
