#!/bin/bash --login

# This is designed to be a simple 1:1 mirror for a release. In final form, this script WILL DELETE any files on the mirror that do not exist on the host!
# That's why we are targeting only a particular release. We have --delete disabled for now.

metro="$(dirname $0)/../metro"
mp=$($metro -k path/mirror 2>/dev/null)
echo $mp
if [ -z "$mp" ]; then
	echo "Could not get path/mirror from metro configuration; exiting."
	exit 1
else
	echo "Mirroring $mp..."
fi
rsync -rltJOve ssh --partial --progress --perms --chmod=Dugo+x,ugo+r,go-w --exclude *.cme --exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar* --exclude *.tar $mp/1.4-release-std/ drobbins@upload.funtoo.org:/home/mirror/funtoo/1.4-release-std/
rsync -rltJOve ssh --partial --progress --perms --chmod=Dugo+x,ugo+r,go-w --exclude *.tar $mp/livecd drobbins@upload.funtoo.org:/home/mirror/funtoo/ --delete
ssh drobbins@upload.funtoo.org sudo /root/metro/scripts/buildrepo index.xml
# don't delete until we've reindexed.
rsync -rltJOve ssh --partial --progress --perms --chmod=Dugo+x,ugo+r,go-w --exclude *.cme --exclude *.cme.run --exclude *.progress --exclude stage1*.tar* --exclude stage2*.tar* --exclude *.tar $mp/1.4-release-std/ drobbins@upload.funtoo.org:/home/mirror/funtoo/1.4-release-std/ --delete
# reindex again.
ssh drobbins@upload.funtoo.org sudo /root/metro/scripts/buildrepo index.xml

