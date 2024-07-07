#!/bin/bash --login
method="rsync"
metro="$(dirname $0)/../metro"
mp=$($metro -k path/mirror 2>/dev/null)
which parallel > /dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "This script requires GNU parallel. Emerge sys-process/parallel first."
	exit 1
fi
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
else
	echo "Mirroring $mp..."
fi
EXTRA_EXCLUDES="--exclude=selinux* --exclude=*2023-* --delete-excluded"
EXCLUDES="--exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar*"
#Let 172.19.1.20 compress and index these...
#$mp/../metro/scripts/buildrepo index.xml
#$mp/../metro/scripts/indexr.py $mp
for x in amd64-bulldozer amd64-excavator amd64-steamroller amd64-piledriver amd64-k10; do
	dest=next/x86-64bit/$x
	echo rsync -azve ssh --zc zstd --zl 6 --delete $mp/$dest/ root@172.19.1.20:/home/mirror/funtoo/$dest $EXCLUDES $EXTRA_EXCLUDES
done | parallel
