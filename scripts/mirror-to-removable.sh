#!/bin/bash --login
# Will mirror stuff to /mnt/data-removable for dragging to datacenter.
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
( cd $ip/../metro; git pull )
echo "Generating XML index"
$ip/../metro/scripts/buildrepo index.xml
echo "Generating index.xml files at $mp"
$ip/../metro/scripts/indexr.py $mp
[ $? -ne 0 ] && echo "Indexr failed." && exit 1
chown -R drobbins:drobbins $mp/
rsync -av --delete $mp/ /mnt/data-removable/funtoo/ $EXCLUDES $EXTRA_EXCLUDES 
