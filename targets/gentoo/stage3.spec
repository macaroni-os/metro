[collect ./source/stage2.spec]
[collect ./target/stage3.spec]
[collect ./steps/capture/tar.spec]

[section steps]

chroot/run: [
#!/bin/bash
$[[steps/setup]]

# make sure eselect is available first. In theory, it should be on the stage1:
if ! [ -e /usr/bin/eselect ]; then
	emerge $eopts -1 app-admin/eselect || exit 15
else
	# ensure we have the latest eselect availble before we start using it:
	emerge -u1 app-admin/eselect
fi

# use python3
a=$(eselect python list | sed -n -e '1d' -e 's/^.* (python3\.[[:digit:]]+).*$/\1/g' -e '/python3/p' | head -n1)
if [ "$a" != "" ]
then
	eselect python set $a
	eselect python cleanup
fi

emerge $eopts -u1 portage || exit 1
emerge $eopts -u1 --nodeps ego || exit 1
export USE="$[portage/USE]"
# handle perl upgrades
perl-cleaner --modules || exit 1
emerge $eopts -e system || exit 1
# hack for binutils-libs needing a rebuild for libctf.so.0.0.0 -- build from source, not package cache
emerge -1 binutils-libs || exit 1
# zap the world file and emerge packages
rm -f /var/lib/portage/world || exit 2
emerge $eopts $[emerge/packages/first:zap] || exit 1
emerge $eopts $[emerge/packages:zap] || exit 1

# add default runlevel services
services=""
services="$[baselayout/services:zap]"

for service in $services
do
	s=${service%%:*}
	l=${service##*:}
	[ "$l" == "$s" ] && l="default"
	if [ -e /etc/init.d/$service ]; then
		rc-update add $s ${l}
	fi
done

if [ -e /usr/share/eselect/modules/vi.eselect ] && [ -e /bin/busybox ]
then
	eselect vi set busybox
fi
$[[steps/chroot/run/extra:lax]]
]

[section portage]

ROOT: /
