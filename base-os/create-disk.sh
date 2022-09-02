#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

target_usb=/dev/sda

if [[ ! -z $1 ]]; then
    target_usb=$1
fi

$__dir/../../scripts/build_base_os.sh
sudo ./scripts/parted_wrapper.py --config $__dir/bootable-usb-config/partitioning.yaml --device $target_usb
sudo ./scripts/package_docker.py --image joshs333/rauc-setup/base-os --acl-file tmp/perm_dump --tar-file /tmp/bleh.tar --overlay $__dir/overlay
sudo ./scripts/setup_disk.py --config $__dir/bootable-usb-config/disk-setup.yaml --source /tmp/bleh.tar --device $target_usb
