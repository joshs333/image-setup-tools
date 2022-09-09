#!/usr/bin/env bash

export PATH=$PATH:/usr/games

force_color_prompt=yes

scroll_speed=1000

function lolcat_banner() {
    banner "$@" | pv -qL $scroll_speed | lolcat
}

function scary() {
    drive=$1
    # lolcat_banner "Erasing"
    lolcat_banner $(basename $drive)
    echo $drive - overwriting partition tables
    echo $drive - clearing file system
    echo $drive - erased
    echo
    #sleep 0.2
    #lolcat_banner .
    #sleep 0.2
    #lolcat_banner .
}

amixer set `Master` 100%
aplay home/user/nightmare/black_hole_sound.mp3 & > /dev/null 2> /dev/null

sleep_time=0.5

lolcat_banner "Kill Stick"
sleep $sleep_time

if [[ ! -z $(ls /dev/sd* 2> /dev/null) ]]; then
    for f in $(ls /dev/sd*); do
        scary $f
        sleep $sleep_time
    done
fi


if [[ ! -z $(ls /dev/nvme* 2> /dev/null) ]]; then
    for f in $(ls /dev/nvme*); do
        scary $f
        sleep $sleep_time
    done
fi

if [[ ! -z $(ls /dev/mmc* 2> /dev/null) ]]; then
    for f in $(ls /dev/mmc*); do
        scary $f
        sleep $sleep_time
    done
fi

jp2a --width=80  home/user/nightmare/set-woman-hand-with-middle-finger-up_266639-144.jpg\?w\=2000  --colors
lolcat_banner "All Data"
lolcat_banner "Erased"
sleep 1.0
echo
echo
lolcat_banner "Attempting"
lolcat_banner "To Fry CPU"
echo "Disabling thermal regulation"
sleep 1.0
echo "Initiating power regulation overload"
sleep 2.0
echo
echo
echo
echo "--- [ Kernel Panic ] ---"
echo "RSP: 0018:ffff12ea2841DSa9 RAX: ffff8c8c92c9aaf8"
echo "RBP: 0019:ff1fa23fea18fb34 R11: fddf8c8c52c9aaf8"
echo "RDX: 0020:2ffffgffff3afba9 R13: 11f228c12c52aaf8"
echo " power fluctuations detected"
echo " power regulation failed"
echo " all systems failed"
echo "--- [ end Kernel panic - not syncing: Attempting to kill init! ] ---"
sleep 10

lolcat_banner "That's it,"
lolcat_banner "Reboot"

sleep 100000
