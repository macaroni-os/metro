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
epro flavor desktop || exit 2
epro mix-in $[desktop/mix-in] || exit 1
extra_pkgs=""
extra_initd=""
if [ "$[target/arch_desc]" == "x86-64bit" ]; then
	epro mix-in gfxcard-kvm gfxcard-amdgpu gfxcard-radeon gfxcard-vmware || exit 1
	extra_pkgs="chrony grub linux-firmware sof-firmware open-vm-tools"
	extra_initd="vmware-tools"
	case "$[target/subarch]" in
		intel64-skylake|intel64-broadwell)
			epro mix-in gfxcard-intel-iris || exit 2
			;;
		*)
			epro mix-in gfxcard-intel || exit 2
			;;
	esac

elif [ "$[target/arch_desc]" == "x86-32bit" ]; then
	extra_pkgs="chrony grub linux-firmware sof-firmware"
	epro mix-in gfxcard-intel || exit 1
elif [ "$[target/arch_desc]"] == "arm-64bit" ]; then
	if [ "$[target/subarch]" == "raspi4" ]; then
		extra_pkgs="raspberrypi-image raspberrypi-wifi-ucode raspberrypi-firmware raspberrypi-userland"
		epro mix-in gfxcard-raspi4 || exit 2
		rc-update del hwclock default || exit 4
		rc-update add swclock default || exit 4
		extra_initd="busybox-ntpd"
	fi
fi
# enable intel stuff for all intel things:
targ_sub="$[target/subarch]"
if [ "${targ_sub/intel/}" != "${targ_sub}" ]; then
    extra_pkgs="$extra_pkgs intel-microcode iucode_tool"
fi
if [ -e /etc/init.d/chronyd ]; then
    rc-update add chronyd default || exit 51
fi
emerge $eopts -uDN @world || exit 3
emerge $eopts -uDN $[desktop/packages] metalog vim nss-mdns xorg-x11 $extra_pkgs || exit 4
emerge $eopts @preserved-rebuild -uDN -1 --backtrack=6 || exit 5

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
glib-compile-schemas /usr/share/glib-2.0/schemas/
]
