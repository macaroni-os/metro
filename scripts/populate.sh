for x in $(cd 1.3-release-std; ls -d *-*/*); do
x="${x##./}"
subarch=${x##*/}
arch_desc=${x%%/*}
install -d 1.4-release-std/$x
if [ ! -d 1.4-release-std/$x/.control ]; then
cp -a 1.4-release-std/x86-64bit/intel64-skylake/.control 1.4-release-std/$x || echo fart
fi
out=1.4-release-std/$x/.control
echo "$subarch" > $out/remote/subarch
echo "$arch_desc" > $out/remote/arch_desc
echo "remote" > $out/strategy/build
done
