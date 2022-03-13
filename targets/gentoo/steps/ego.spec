[section steps/ego]

prep: [
ego_out_dir=$[path/work]/etc
install -d $ego_out_dir
cat > $ego_out_dir/ego.conf << EOF
[global]
release = $[profile/release]
EOF
if [ -n "$EGO_SYNC_BASE_URL" ]; then
cat >> $ego_out_dir/ego.conf << EOF
sync_base_url = ${EGO_SYNC_BASE_URL}
EOF
fi
export EGO_CONFIG=$ego_out_dir/ego.conf
]

