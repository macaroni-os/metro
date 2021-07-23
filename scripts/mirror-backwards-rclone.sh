#!/bin/bash --login
echo "Mirroring BACKWARDS from cdn-pull up to the b2 mirror"
ssh drobbins@cdn-pull.funtoo.org rclone sync -lP /home/mirror/funtoo/ b2:funtoo-mirror/
