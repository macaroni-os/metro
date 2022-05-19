#!/usr/bin/python3

import os
import subprocess
import time
from shutil import which

from metro_support import MetroError, ismount
from qemu_support import native_support

from .base import BaseTarget


class ChrootTarget(BaseTarget):
	def __init__(self, settings, cr):
		BaseTarget.__init__(self, settings, cr)

		# we need a source archive
		self.required_files.append("path/mirror/source")

		# define general linux mount points
		self.mounts = { }

		options = ["cache/package"]

		# define various mount points for our cache support (ccache, binpkgs,
		# genkernel, etc).
		caches = [
			[ "path/cache/package", "cache/package", "/var/tmp/cache/package" ] ,
			[ "path/cache/kernel", "cache/kernel", "/var/tmp/cache/kernel" ] ,
			[ "path/cache/probe", "probe", "/var/tmp/cache/probe" ],
		]

		for key, name, dst in caches:
			if name in options:
				if key not in self.settings:
					raise MetroError("Required setting %s not found (for %s option support)" % (key, name))
				if self.settings[key] is not None:
					# package cache dir will not be defined for snapshot...
					self.cr.mesg("Enabling cache: %s" % key)
					self.mounts[dst] = self.settings[key]

	def run(self):
		self.check_required_files()

		# before we clean up - make sure we are unmounted
		self.kill_chroot_pids()
		self.unbind()

		# before we start - clean up any messes
		self.clean_path(recreate=True)

		try:
			self.run_script("steps/unpack")
			self.run_script("steps/unpack/post", optional=True)

			if "host/arch_desc" in self.settings:
				host_arch = self.settings["host/arch_desc"]
			else:
				uname_arch = os.uname()[4]
				if uname_arch in ["x86_64", "AMD64"]:
					host_arch = "x86-64bit"
				elif uname_arch in ["x86", "i686", "i386"]:
					host_arch = "x86-32bit"
				else:
					raise MetroError("Unrecognized host architecture. Please set host/arch to x86-64bit, arm-32bit, etc. in ~/.metro.")

			if host_arch not in native_support.keys():
				raise MetroError("Arch specified in host/arch_desc \"%s\" not supported." % host_arch)
			target_arch = self.settings["target/arch_desc"]

			fchroot_bin = which("fchroot")
			if fchroot_bin is None:
				raise MetroError("Please install fchroot and ensure it is in your path.")

			self.bind()

			self.run_script_in_chroot("steps/chroot/prerun", optional=True)
			self.run_script_in_chroot("steps/chroot/run", error_scan=True)
			# capture info about built stage, prior to cleaning. Two part-process,
			# one part in chroot, and the other part outside the chroot.
			if self.settings["release/type"] == "official":
				self.run_script_in_chroot("steps/chroot/grabinfo", optional=True)
				self.run_script("steps/precapture", optional=True)
			# postrun is for cleaning with bind-mounts still active:
			self.run_script_in_chroot("steps/chroot/postrun", optional=True)
			self.unbind()
			self.run_script_in_chroot("steps/chroot/clean", optional=True)
			# re-add bind mounts -- only for tests to run...
			self.bind()
			self.run_script_in_chroot("steps/chroot/test", optional=True)
			self.unbind()
			self.run_script_in_chroot("steps/chroot/postclean", optional=True)
		except:
			self.kill_chroot_pids()
			self.unbind()
			raise
		self.run_script("steps/clean", optional=True)
		if self.settings["release/type"] == "official":
			self.run_script("steps/capture")
			self.run_script("trigger/ok/run", optional=True)

		self.kill_chroot_pids()
		self.unbind()
		self.clean_path()

	def get_chroot_pids(self):
		cdir = self.settings["path/cache/build"]
		pids = []
		for pid in os.listdir("/proc"):
			if not os.path.isdir("/proc/"+pid):
				continue
			try:
				mylink = os.readlink("/proc/"+pid+"/exe")
			except OSError:
				# not a pid directory
				continue
			if mylink[0:len(cdir)] == cdir:
				pids.append([pid, mylink])
		return pids

	def kill_chroot_pids(self):
		for pid, mylink in self.get_chroot_pids():
			print("Killing process "+pid+" ("+mylink+")")
			self.cmd(self.cmds["kill"]+" -9 "+pid)

	def run_script_in_chroot(self, key, optional=False, error_scan=False):
		return self.run_script(key, chroot=self.settings["path/work"], optional=optional, error_scan=error_scan)

	def bind(self):
		""" Perform bind mounts """
		for dst, src in list(self.mounts.items()):
			if not os.path.exists(src):
				os.makedirs(src, 0o755)

			wdst = self.settings["path/work"]+dst
			if not os.path.exists(wdst):
				os.makedirs(wdst, 0o755)

			self.cr.mesg("Mounting %s to %s ..." % (src, dst))
			if os.system(self.cmds["mount"]+" -R "+src+" "+wdst) != 0:
				self.unbind()
				raise MetroError("Couldn't bind mount "+src)

		mounts = self.get_active_mounts()

	def get_active_mounts(self):
		# os.path.realpath should ensure that we are comparing the right thing,
		# if something in the path is a symlink - like /var/tmp -> /foo.
		# Because /proc/mounts will store the resolved path (ie.  /foo/metro)
		# not the regular one (ie. /var/tmp/metro)
		prefix = os.path.realpath(self.settings["path/work"])

		# this used to have a "os.popen("mount")" which is not as accurate as
		# the kernel list /proc/mounts.  The "mount" command relies on
		# /etc/mtab which is not necessarily correct.
		with open("/proc/mounts", "r") as myf:
			mounts = [line.split()[1] for line in myf]
			mounts = [mount for mount in mounts if mount.startswith(prefix)]
			mounts.sort(reverse=True)
			return mounts

# vim: ts=4 sw=4 noet
