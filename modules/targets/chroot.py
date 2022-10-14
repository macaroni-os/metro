#!/usr/bin/python3

import os

from metro_support import MetroError
from .base import BaseTarget


class ChrootTarget(BaseTarget):

	def __init__(self, settings, cr):
		BaseTarget.__init__(self, settings, cr)

		# we need a source archive
		self.required_files.append("path/mirror/source")

		# define various mount points for our cache support (ccache, binpkgs, genkernel, etc).
		caches = [
			["path/cache/package", "cache/package", "/var/tmp/cache/package"],
			["path/cache/kernel", "cache/kernel", "/var/tmp/cache/kernel"],
			["path/cache/probe", "probe", "/var/tmp/cache/probe"],
		]

		for key, name, dst in caches:
			if self.settings.has_key(key) and self.settings[key] is not None and self.settings[key] != "":
				self.cr.mesg("Enabling cache: %s" % key)
				self.mounts[dst] = self.settings[key]

	def run(self):
		self.check_required_files()
		self.abort_if_bind_mounts()

		# before we start - clean up any messes
		self.clean_path(recreate=True)

		try:
			self.run_script("steps/unpack")
			self.run_script("steps/unpack/post", optional=True)
			self.run_script_in_chroot("steps/chroot/prerun", optional=True)
			self.run_script_in_chroot("steps/chroot/run", error_scan=True)
			# capture info about built stage, prior to cleaning. Two part-process,
			# one part in chroot, and the other part outside the chroot.
			if self.settings["release/type"] == "official":
				self.run_script_in_chroot("steps/chroot/grabinfo", optional=True)
				self.run_script("steps/precapture", optional=True)
			# postrun is for cleaning with bind-mounts still active:
			self.run_script_in_chroot("steps/chroot/postrun", optional=True)
			self.abort_if_bind_mounts()
			self.run_script_in_chroot("steps/chroot/clean", nobind=True, optional=True)
			self.abort_if_bind_mounts()
			self.run_script_in_chroot("steps/chroot/test", optional=True)
			self.run_script_in_chroot("steps/chroot/postclean", nobind=True, optional=True)
		except:
			self.kill_chroot_pids()
			raise
		self.run_script("steps/clean", optional=True)
		if self.settings["release/type"] == "official":
			self.run_script("steps/capture")
			self.run_script("trigger/ok/run", optional=True)

		self.abort_if_bind_mounts()
		self.clean_path()

	def get_chroot_pids(self):
		cdir = self.settings["path/cache/build"]
		pids = []
		for pid in os.listdir("/proc"):
			if not os.path.isdir("/proc/" + pid):
				continue
			try:
				mylink = os.readlink("/proc/" + pid + "/exe")
			except OSError:
				# not a pid directory
				continue
			if mylink[0:len(cdir)] == cdir:
				pids.append([pid, mylink])
		return pids

	def kill_chroot_pids(self):
		for pid, mylink in self.get_chroot_pids():
			print("Killing process " + pid + " (" + mylink + ")")
			self.cmd(self.cmds["kill"] + " -9 " + pid)

	def run_script_in_chroot(self, key, optional=False, error_scan=False, nobind=False):
		return self.run_script(key, chroot=self.settings["path/work"], nobind=nobind, optional=optional, error_scan=error_scan)


# vim: ts=4 sw=4 noet
