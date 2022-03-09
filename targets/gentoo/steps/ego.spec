[section steps/ego]

prep: [
ego_out_dir=$[path/work]/etc
install -d $ego_out_dir
cat > $ego_out_dir/ego.conf << EOF
[global]
release = $[profile/release]
EOF
fi
]

