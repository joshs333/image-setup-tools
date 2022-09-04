#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

target_usb=/dev/sda

if [[ ! -z $1 ]]; then
    target_usb=$1
fi

$__dir/build_nightmare_stick.sh
sudo ./scripts/parted_wrapper.py --config $__dir/../base-os/bootable-usb-config/partitioning.yaml --device $target_usb
sudo ./scripts/package_docker.py --image joshs333/rauc-setup/setup --acl-file tmp/perm_dump --tar-file /tmp/setup.tar --overlay $__dir/../base-os/overlay --overlay $__dir/overlay
sudo ./scripts/setup_disk.py --config $__dir/../base-os/bootable-usb-config/disk-setup.yaml --source /tmp/setup.tar --device $target_usb
