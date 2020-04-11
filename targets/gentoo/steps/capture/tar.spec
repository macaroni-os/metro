[section path/mirror]

target/basename: $[target/name].tar.$[target/compression]

[section steps]

capture: [
#!/bin/bash
outdir=`dirname $[path/mirror/target]`
if [ ! -d $outdir ]
then
	install -o $[path/mirror/owner] -g $[path/mirror/group] -m $[path/mirror/dirmode] -d $outdir || exit 1
fi
tarout="$[path/mirror/target]"
# remove compression suffix:
tarout="${tarout%.*}"
tar cpf $tarout --xattrs --acls -C $[path/chroot/stage] .
if [ $? -ge 2 ]
then
	echo "Error creating tarball."
	rm -f "$tarout" "$[path/mirror/target]"
	exit 1
fi
# cme = "compress me"
if [ "$[target]" = "stage2" ]; then
    echo "Skipping compression for stage2"
elif [ "$[target]" = "stage1" ]; then
    echo "Skipping compression for stage1"
else
    touch $tarout.cme
fi
# Note: we used to compress here. We no longer do. We want that handled out-of-band
# for performance reasons.
chown $[path/mirror/owner]:$[path/mirror/group] "$tarout" "${tarout}.cme"
exit 0
]
