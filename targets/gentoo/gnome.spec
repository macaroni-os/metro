[collect ./source/stage3.spec]
[collect ./target/stage4.spec]
[collect ./steps/capture/tar.spec]

[section stage4]

target/name: gnome-stage3

[section steps]

unpack/post: [
#!/bin/bash
fsroot_loc=$[path/install]/etc/builds/$[target/build]/$[target]/fsroot
if [ -d "$fsroot_loc" ]; then
	install -d "$[path/chroot]/tmp/fsroot" || exit 8
	# we will need to sync this to the root filesystem after we're done merging...
	rsync -av "${fsroot_loc}/" "$[path/chroot]/tmp/fsroot" || exit 9
fi
if [ -e "${fsroot_loc}.mtree" ]; then
	cp "${fsroot_loc}.mtree" "$[path/chroot]/tmp/" || exit 10
fi
]

chroot/run: [
#!/bin/bash
$[[steps/setup]]
epro mix-in gnome || exit 1
if [ "$[target/arch_desc]" == "x86-64bit" ]; then
	epro mix-in gfxcard-nvidia gfxcard-amdgpu gfxcard-radeon || exit 1
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
for pkg in gnome metalog vim linux-firmware nss-mdns xorg-x11; do
	emerge $eopts $pkg || exit 4
done
if [ -d /tmp/fsroot ]; then
	echo "Syncing custom config over myself..."
	rsync -av /tmp/fsroot/ / || exit 1
fi
for svc in NetworkManager avahi-daemon bluetooth metalog xdm; do
	rc-update add $svc default
done
]
