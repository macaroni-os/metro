[collect ./source/stage3.spec]
[collect ./steps/container.spec]
[collect ./steps/capture/tar.spec]

[section stage4]

target/name: openvz

[section target]

sys: openvz
name: $[:build]-$[:subarch]-$[stage4/target/name]-$[:version]

[section steps]

chroot/run: [
$[[steps/chroot/run/container/base]]
]
