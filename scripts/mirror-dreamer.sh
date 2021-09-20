#!/bin/bash --login
# This script will grab stages from dreamer's removable storage (in-datacenter) and update our images that way,
# rather than pulling from rclone. Once this is done, you should run scripts/mirror-backwards-rclone.sh to get
# our b2 backup in sync with what is on the server (we normally PULL from the b2 backup so it expects to be the
# "master".
#
# This script should be run directly from the 'ports' container when /mnt/data-removable is mounted on dreamer,
# as either the root or drobbins user.
metro="$(dirname $0)/../metro"
ip=$($metro -k path/install 2>/dev/null)
[ $? -ne 0 ] && echo "Get install path failed." && exit 1
mp=$($metro -k path/mirror 2>/dev/null)
[ $? -ne 0 ] && echo "Get mirror path failed." && exit 1
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
else
	echo "Mirroring $mp..."
fi
EXTRA_EXCLUDES="--exclude=selinux* --exclude=*2019-* --exclude=*2020-* --delete-excluded"
EXCLUDES="--exclude *.cme --exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar* --exclude *.tar"
rsync -ave ssh --delete drobbins@192.150.253.92:/mnt/data-removable/funtoo/ $mp/ $EXCLUDES $EXTRA_EXCLUDES 
echo "Generating XML index"
$ip/../metro/scripts/buildrepo index.xml
echo "Generating index.xml files at $mp"
$ip/../metro/scripts/indexr.py $mp
[ $? -ne 0 ] && echo "Indexr failed." && exit 1
chown -R drobbins:drobbins $mp/
# flush wiki
ssh drobbins@www.funtoo.org sudo /etc/init.d/memcached restart
