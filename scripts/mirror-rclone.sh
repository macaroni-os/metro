#!/bin/bash --login

metro="$(dirname $0)/../metro"
mp=$($metro -k path/mirror 2>/dev/null)
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
else
	echo "Mirroring $mp..."
fi
EXTRA_EXCLUDES="--exclude=selinux* --exclude=*2019-* --delete-excluded"
EXCLUDES="--exclude *.cme --exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar* --exclude *.tar"
$mp/../metro/scripts/buildrepo index.xml
$mp/../metro/scripts/indexr.py $mp
rclone -Pl $EXCLUDES $EXTRA_EXCLUDES --b2-chunk-size=36M --b2-upload-cutoff=36M --transfers=3 --checkers=24 sync $mp b2:funtoo-mirror
rclone cleanup b2:funtoo-mirror
if [ "$1" == "half" ]; then
	echo "Only performing first half of mirroring operation."
	echo "This part is done."
	exit 0
fi
ssh drobbins@cdn-pull.funtoo.org rclone sync -lP b2:funtoo-mirror/ /home/mirror/funtoo/
ssh drobbins@cdn-pull.funtoo.org 'find /home/mirror/funtoo -type f -exec chmod 0644 {} \;'
ssh drobbins@cdn-pull.funtoo.org 'find /home/mirror/funtoo -type d -exec chmod 0755 {} \;'
ssh root@www.funtoo.org /etc/init.d/memcached restart
