[collect ./stage.spec]

[section target]

pkgcache: $[target]
name: $[stage4/target/name]-$[:subarch]-$[:build]-$[:version]

[section portage]

ROOT: /
