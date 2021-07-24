[collect ./source/stage3.spec]
[collect ./target/stage4.spec]
[collect ./steps/capture/tar.spec]

[section stage4]

target/name: $[target]-stage3

[section steps]

unpack/post: [
#!/bin/bash
fsroot_loc=$[path/install]/etc/builds/$[target/build]/$[target]/fsroot
if [ -d "$fsroot_loc" ]; then
	install -d "$[path/chroot]/tmp/fsroot" || exit 8
	# we will need to sync this to the root filesystem after we're done merging...
	rsync -av --no-owner --no-group "${fsroot_loc}/" "$[path/chroot]/tmp/fsroot" || exit 9
fi
if [ -e "${fsroot_loc}.mtree" ]; then
	cp "${fsroot_loc}.mtree" "$[path/chroot]/tmp/" || exit 10
fi
]

chroot/run: [
#!/bin/bash
$[[steps/setup]]
epro mix-in $[desktop/mix-in] || exit 1
extra_pkgs=""
extra_initd=""
if [ "$[target/arch_desc]" == "x86-64bit" ]; then
	epro mix-in gfxcard-nvidia gfxcard-amdgpu gfxcard-radeon gfxcard-vmware || exit 1
	extra_pkgs="open-vm-tools"
	extra_initd="vmware-tools"
	case "$[target/subarch]" in
		intel64-skylake|intel64-broadwell)
			epro mix-in gfxcard-intel-iris || exit 2
			;;
		intel64-*|generic_64)
			epro mix-in gfxcard-intel || exit 2
			;;
	esac
	for pkg in nvidia-kernel-modules; do
		emerge $eopts $pkg || exit 4
	done
elif [ "$[target/arch_desc]" == "x86-32bit" ]; then
	epro mix-in gfxcard-intel || exit 1
fi
epro flavor desktop || exit 2
emerge $eopts -uDN @world || exit 3
emerge $eopts $[desktop/packages] metalog vim linux-firmware sof-firmware nss-mdns xorg-x11 $extra_pkgs || exit 4
if [ -e /etc/init.d/elogind ]; then
	rc-update add elogind boot
fi
if [ -d /tmp/fsroot ]; then
	echo "Syncing custom config over myself..."
	rsync -av /tmp/fsroot/ / || exit 1
fi
for svc in NetworkManager avahi-daemon bluetooth metalog xdm $extra_initd; do
	rc-update add $svc default
done
]
