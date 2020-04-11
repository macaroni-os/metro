[collect ./stage.spec]

[section target]

name: stage3-$[:subarch]-$[:build]-$[:version]
name/prefix: stage3-$[:subarch]-
pkgcache: stage3

[section trigger]

ok/run: [
#!/bin/bash

install -o $[path/mirror/owner] -g $[path/mirror/group] -m $[path/mirror/dirmode] -d $[path/mirror/target/control]/version || exit 1
echo "$[target/version]" > $[path/mirror/target/control]/version/stage3 || exit 1
chown $[path/mirror/owner]:$[path/mirror/group] $[path/mirror/target/control]/version/stage3 || exit 1
if [ "$[strategy/build]" == "remote" ]; then
	# auto-switch to local build once we have a local stage3, but only for official builds.
	# git snapshot QA builds remain locked in remote state.
	echo "local" > $[path/mirror/target/control]/strategy/build
fi
]
