#!/bin/bash --login

# This is designed to be a simple 1:1 mirror for a release. This script WILL DELETE any files on the mirror that do not exist on the host!
#CUSTOM_EXCLUDE="--exclude *2020-02-03*"
metro="$(dirname $0)/../metro"
mp=$($metro -k path/mirror 2>/dev/null)
echo $mp
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
else
	echo "Mirroring $mp..."
fi
EXTRA_EXCLUDES="--exclude=selinux* --exclude=*2019-* --exclude=*2020-01* --exclude=*2020-02* --delete-excluded"
EXCLUDES="--exclude *.cme --exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar* --exclude *.tar"
/root/metro/scripts/buildrepo index.xml
rclone -Pl $EXCLUDES $EXTRA_EXCLUDES --b2-chunk-size=36M --b2-upload-cutoff=36M --transfers=18 --checkers=24 sync /mnt/data/mirror/funtoo b2:funtoo-mirror
rclone cleanup b2:funtoo-mirror
ssh drobbins@upload.funtoo.org rclone sync -lP b2:funtoo-mirror/ /home/mirror/funtoo/
