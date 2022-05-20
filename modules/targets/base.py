import os, sys, types
from glob import glob
from shutil import which

from metro_support import MetroError


class BaseTarget:
	mounts = {}
	cmds = {
		"bash": "/bin/bash",
		"chroot": "/usr/bin/chroot",
		"install": "/usr/bin/install",
		"kill": "/bin/kill",
		"linux32": "/usr/bin/linux32",
		"mount": "/bin/mount",
		"rm": "/bin/rm",
	}

	def __init__(self, settings, cr):
		self.settings = settings
		# new CommandRunner (logger) object:
		self.cr = cr
		self.env = {}
		self.env["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin"
		self.required_files = []
		fchroot_bin = which("fchroot")
		if fchroot_bin is None:
			raise MetroError("Please install fchroot and ensure it is in your path.")
		else:
			self.cmds["fchroot"] = fchroot_bin

	def abort_if_bind_mounts(self):
		for path in ["proc", "sys", "dev"] + list(self.mounts.keys()):
			abs_path = os.path.join(self.settings["path/work"], path.lstrip("/"))
			if os.path.ismount(abs_path):
				raise MetroError(f"Path {abs_path} is still mounted. Refusing to continue for safety.")

	def run(self):
		self.check_required_files()
		self.abort_if_bind_mounts()
		self.clean_path(recreate=True)
		self.run_script("steps/run")
		self.clean_path()

	def run_script(self, key, chroot=None, optional=False, error_scan=False, nobind=False):
		if key not in self.settings:
			if optional:
				return
			raise MetroError("run_script: key '%s' not found." % (key,))

		if type(self.settings[key]) != list:
			raise MetroError("run_script: key '%s' is not a multi-line element." % (key,))

		self.cr.mesg("run_script: running %s..." % key)

		if chroot:
			chrootfile = "/tmp/" + key + ".metro"
			outfile = chroot + chrootfile
		else:
			outfile = self.settings["path/tmp"] + "/pid/" + repr(os.getpid())

		outdir = os.path.dirname(outfile)
		if not os.path.exists(outdir):
			os.makedirs(outdir)

		with open(outfile, "w") as outfd:
			outlines = list(self.settings[key])
			if not chroot and "EGO_SYNC_BASE_URL" in os.environ:
				if outlines[0] == "#!/bin/bash":
					outlines.insert(1, f'export EGO_SYNC_BASE_URL={os.environ["EGO_SYNC_BASE_URL"]}')
			outfd.write("\n".join(outlines) + "\n")

		os.chmod(outfile, 0o755)

		cmds = []
		if chroot:
			cmds.append(self.cmds["fchroot"])
			if nobind:
				cmds.append("--nobind")
			else:
				for dest, src in self.mounts.items():
					cmds.append(f"--bind={src}:{dest}")
					# fchroot expects bind-mount destination to exist:
					dest_path = os.path.join(chroot, dest.lstrip("/"))
					os.makedirs(dest_path, exist_ok=True)
			cmds.append(chroot)
			cmds.append(chrootfile)
		else:
			cmds.append(outfile)

		retval = self.cr.run(cmds, env=self.env, error_scan=error_scan)
		if retval != 0:
			raise MetroError("Command failure (key %s, return value %s) : %s" % (key, repr(retval), " ".join(cmds)))

		# it could have been cleaned by our outscript, so if it exists:
		if os.path.exists(outfile):
			os.unlink(outfile)

	def check_required_files(self):
		for loc in self.required_files:
			try:
				matches = glob(self.settings[loc])
			except:
				raise MetroError("Setting %s is set to %s; glob failed." % (loc, repr(self.settings[loc])))
			if len(matches) == 0:
				loc_no_ending = None
				found = False
				# look for uncompressed version of file:
				for ending in [".tar.xz", ".tar.gz", "tar.bz2"]:
					if self.settings[loc].endswith(ending):
						zap_part = "." + ending.split(".")[-1]
						# remove .gz, .xz extension:
						loc_no_ending = self.settings[loc][:-len(zap_part)]
						break
				if loc_no_ending is not None:
					matches = glob(loc_no_ending)
					if len(matches) != 0:
						print("Found uncompressed file: %s" % loc_no_ending)
						found = True
				if not found:
					raise MetroError("Required file " + self.settings[loc] + " not found. Aborting.")
			elif len(matches) > 1:
				raise MetroError("Multiple matches found for required file pattern defined in '%s'; Aborting." % loc)

	def clean_path(self, path=None, recreate=False):
		if path == None:
			path = self.settings["path/work"]
		if os.path.exists(path):
			print("Cleaning up %s..." % path)
		self.cmd(self.cmds["rm"] + " -rf " + path)
		if recreate:
			# This line ensures that the root /var/tmp/metro path has proper 0700 perms:
			self.cmd(self.cmds["install"] + " -d -m 0700 -g root -o root " + self.settings["path/tmp"])
			# This creates the directory we want.
			self.cmd(self.cmds["install"] + " -d -m 0700 -g root -o root " + path)
		# The 0700 perms prevent Metro-generated /tmp directories from being abused by others -
		# because they are world-writeable, they could be used by malicious local users to
		# inject arbitrary data/executables into a Metro build.

	def cmd(self, mycmd, myexc="", badval=None):
		self.cr.mesg("Executing \"" + mycmd + "\"...")
		try:
			sys.stdout.flush()
			retval = self.cr.run(mycmd.split(), self.env)
			if badval:
				# This code is here because tar has a retval of 1 for non-fatal warnings
				if retval == badval:
					raise MetroError(f'{myexc} (error code {retval}')
			else:
				if retval != 0:
					raise MetroError(f'{myexc} (error code {retval}')
		except:
			raise

# vim: ts=4 sw=4 noet
