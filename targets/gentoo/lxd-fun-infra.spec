[collect ./source/stage3.spec]
[collect ./target/stage4.spec]
[collect ./steps/container-lxd.spec]
[collect ./steps/capture/lxd-tar.spec]

[section stage4]

target/name: lxd-fun-infra

[section target]

sys: lxc

[section path]

lxd: $[path/tmp]/work/lxd

[section steps]

unpack/post: [
#!/bin/bash
fsroot_loc=$[path/install]/etc/builds/$[target/build]/$[target]/fsroot
if [ -d "$fsroot_loc" ]; then
	install -d "$[path/chroot]/tmp/fsroot" || exit 8
	# we will need to sync this to the root filesystem after we're done merging...
	rsync -av "${fsroot_loc}/" "$[path/chroot]/tmp/fsroot" || exit 9
fi
if [ -e "${fsroot_loc}.mtree" ]; then
	cp "${fsroot_loc}.mtree" "$[path/chroot]/tmp/" || exit 10
fi
]

chroot/run: [
#!/bin/bash
$[[steps/setup]]
sed -i -E -e '/^[*]\s+soft/d' -e '/^[*]\s+hard/d' /etc/security/limits.conf

epro flavor core || exit 2
epro mix-in +mediaformat-gfx-common || exit 3
epro mix-in +mediaformat-gfx-extra || exit 4


WEB_PKGS="
app-crypt/certbot
app-crypt/certbot-nginx
net-libs/nodejs
net-proxy/haproxy
www-servers/nginx
"

PHP_PKGS="
dev-lang/php
dev-php/pecl-apcu
dev-php/pecl-memcached
net-misc/memcached
media-gfx/imagemagick
"

BASE_PKGS="
app-admin/metalog
app-misc/tmux
app-editors/vim
mail-mta/postfix
net-analyzer/iptraf-ng
net-misc/autossh
net-misc/mosh
net-misc/rclone
net-misc/zerotier
sys-process/fcron
sys-process/htop
"

DB_PKGS="
dev-db/mongodb
dev-db/mysql-community
"

PY_PKGS="
dev-python/aiohttp
dev-python/jinja
dev-python/lxml
dev-python/mysql-connector-python
dev-python/sqlalchemy
dev-python/pymongo
dev-python/pip
dev-python/pop
dev-python/pop-config
dev-python/python-dateutil
dev-python/pyzmq
www-servers/tornado
"
emerge $eopts -uDN @world $DB_PKGS $PY_PKGS $BASE_PKGS $WEB_PKGS || exit 4
if [ -d /tmp/fsroot ]; then
	echo "Syncing custom config over myself..."
	rsync -av /tmp/fsroot/ / || exit 1
fi
for svc in postfix metalog fcron; do
	rc-update add $svc default
done
$[[steps/chroot/run/container/base]]
]
