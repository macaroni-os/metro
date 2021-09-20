#!/usr/bin/python3

import os, stat, sys
from datetime import datetime
file_width = 67 
file_post_space = 3

def do_line(of, f, url_f, sz, mtime, path_offset = "/"):
    is_dir = False
    if sz is None:
        is_dir = True
        # dir
        sz = "-"
        f = f + "/"
    else:
        sz = str(sz)
    url_f = "https://build.funtoo.org" + os.path.join(path_offset, url_f)
    if is_dir:
        # This avoids a weird issue where "1.4-release-std" will redirect to cdn-pull.funtoo.org, which
        # will bump people off the CDN! Whereas adding a "/" will get them to the index without the 
        # extra redirect, and should keep them on the CDN.
        url_f += "/"
    if len(f) > file_width:
        fout = f[:file_width - 3] + "..."
        pad = 0
    else:
        fout = f
        pad = file_width - len(f)
    fout = f"<a href=\"{url_f}\">{fout}</a>" + " " * ( pad + file_post_space)
    of.write(fout + " " + datetime.fromtimestamp(mtime).strftime("%Y-%b-%d %H:%M") + " " + sz.rjust(16) + "\n")


def do_index(cur_path, dirnames, filenames, path_offset = "/"):
    print(f"Processing {cur_path}...")
    with open(cur_path + "/index.html", "w") as of: 
        of.write(f"<html><head><title>Index of {path_offset}</title></head>\n")
        of.write("<body>\n")
        of.write(f"<h1>Index of {path_offset}</h1><hr><pre>\n")
        f_list = []
        d_list = []
        hidden = [ "robots.txt", "index.html" ]
        for f in filenames:
            if f in hidden or f.startswith("."):
                continue
            if f.startswith("stage1") or f.startswith("stage2"):
                continue
            real_path = os.path.join(cur_path, f)
            try:
                st = os.stat(real_path)
            except FileNotFoundError:
                continue
            if os.path.islink(real_path):
                f_list.append((f, os.readlink(real_path), st[stat.ST_SIZE], st[stat.ST_MTIME]))
            else:
                f_list.append((f, f, st[stat.ST_SIZE], st[stat.ST_MTIME]))
        for d in dirnames:
            real_path = os.path.join(cur_path, d)
            try:
                st = os.stat(real_path)
            except FileNotFoundError:
                continue
            if d.startswith("."):
                continue
            d_list.append((d, d, None, st[stat.ST_MTIME]))
        if path_offset != "/":
            of.write('<a href="..">..</a>\n')
        for f, real_f, sz, mtime in sorted(d_list) + sorted(f_list):
            do_line(of, f, real_f, sz, mtime, path_offset)
        of.write("</pre><hr>")
        of.write("</body></html>")

ix_path = sys.argv[1]

for path, dirnames, filenames in os.walk(ix_path):
    if os.path.basename(path).startswith("."):
        continue
    common_path = os.path.commonpath([ix_path, path])
    if common_path == path:
        path_offset = "/"
    else:
        path_offset = "/" + path[len(common_path):].lstrip("/")
    do_index(path, dirnames, filenames, path_offset=path_offset)
