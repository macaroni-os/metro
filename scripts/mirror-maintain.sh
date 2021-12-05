#!/bin/bash --login

# This script is meant to perform maintenance of the local mirror of metro builds. This script will clean up any old builds,
# and also call buildrepo digestgen to sign any new builds.

metro="$(dirname $0)/../metro"
buildrepo="$(dirname $0)/buildrepo"
mp="$($metro -k path/mirror 2>/dev/null)"
echo $mp
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
fi
$buildrepo clean | tee /tmp/foo.sh
for x in $(find $mp -type l) ; do
	echo "rm $x" >> /tmp/foo.sh
done
echo
echo $mp
echo "About to perform the above clean actions in 5 seconds... (^C to abort...)"
for x in 5 4 3 2 1; do
	echo -n "$x "
	sleep 1
done
echo
sh /tmp/foo.sh
$buildrepo digestgen
echo "Regenerating symlinks"
for subdir in $(cd $mp && ls -d */*/*/20* | cut -f1-3 -d/ | sort -u); do
	latest=$(ls -d $mp/$subdir/20* | sort | tail -n 1)
	for xzfile in $(ls $latest/*.tar.xz 2>/dev/null); do
		basexzfile=$(basename $xzfile)
		prefix="${basexzfile%%-*}"
		echo $xzfile $prefix
		# The link to create, abs path:
		link=$(dirname $latest)/$prefix-latest.tar.xz
		# The link destination, "2021-11-13/stage3-2021-11-13.tar.xz"
		linkdest=$(basename $latest)/$(basename $xzfile)
		# The absolute path to the link destination (used for GPG links)
		linkdestabs=$(dirname $latest)/$linkdest
		echo Creating $link "->" $linkdest
		rm -f $link; rm -f $link.gpg
		ln -s $linkdest $link
		if [ -e ${linkdestabs}.gpg ]; then
			ln -s ${linkdest}.gpg ${link}.gpg
			echo Creating GPG ${link}.gpg "->" ${linkdest}.gpg
		else
			echo GPG signature ${linkdestabs}.gpg does NOT exist
		fi
	done
done
echo "Fixing permissions"
cd $mp
chown -R drobbins:drobbins $mp
find $mp -type f -exec chmod 0644 {} \;
find $mp -type d -exec chmod 755 {} \;
