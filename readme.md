# Image Setup Tools
The purpose of this repo is to make it easier to make rauc bundles using docker as an image build tool, package that image, partition and install to a disk.

# Example Images
## base-os
Provides a simple image using [base-os docker](base-os/base-os.docker), which loads in a base ubuntu 20.04 file system and installs additional tools on top of is. To download / build run [build_base_os.sh](base-os/build_base_os.sh).

Additionally configuration for making a bootable USB / setup an image in the [bootable-usb-config](base-os/bootable-usb-config/). This can be applied to a disk using [create-disk.sh](base-os/create-disk.sh). This script takes the target partition as the first argument and provides a good example of how to use the scripts here.

This is also a good basic example of grub configuration, the grub configuration file installed directly to the bootloader is at [boot/grub/EFI/BOOT/grub.cfg](base-os/overlay/boot/grub/EFI/BOOT/grub.cfg), this just redirects to another [grub.cfg](base-os/overlay/boot/grub/grub.cfg) in the root of the EFI partition. You may note that these are all in the [/boot/grub](base-os/overlay/boot/grub/) folder in the overlay. This is because the image is setup to mount the efi / boot partition to `/boot/grub` (see [fstab](base-os/overlay/etc/fstab)). This partition setup is facilicated by [setup_disk.py](scripts/setup_disk.py) using [disk_setup.yaml](base-os/bootable-usb-config/disk-setup.yaml) which installs grub to the boot partition - then copies over the `/boot/grub` folder to the root of the boot partition. There are some notes on this scattered through the base-os configuration.

It is equally valid to have a single grub.cfg that directly boots to os partition and not have the boot partition mounted into the os filesystem.

## base-os-graphical
Extends off the base-os image and installs additional packages for a desktop environment with gnome. The [build_base_os_graphical.sh](base-os-graphical/build_base_os_graphical.sh) script will build the base-os and then build the [base-os-graphical.docker](base-os-graphical/base-os-graphical.docker) image. Similarly [create-disk.sh](base-os-graphical/create-disk.sh) can be used to perform all the steps to create a bootable disk with this image.

## base-setup
Extends off the base-os-graphical image, this provides a configuration that can create a USB stick that can be plugged into a computer and partition / flash the hard drive to an image based confugration.

## nightmare-stick
Extends off the base-os image, is a practical joke that prints nasty messages about erasing hard drives and frying the CPU. It doesn't actually do any of this, it was mostly made to check my understanding of various boot / init steps with linux and how it interacts with grub. Use responsibly :)


# Scripts
The `scripts/` folder contains scripts not specific to any image configuration.

## package_docker.py
The [package_docker.py](scripts/package_docker.py) script takes a docker image and exports it to a tar file or folder - can also apply overlays on top of the extract image (usually for /etc/hosts and /etc/hostname which docker overwrites). It takes the following arguments:
- *--image*: the name of the image to dump into a tar file
- *--container-name*: the process involves creating a container from the image, if this is not specified a random name is used, but it is possible to force the script to use a container name specified here
- *--fs-root*: the folder to dump the file system (if tar-file is specified, this is automatically cleaned up after)
- *--tar-file*: once the file system has been generated, dump it into a tar file specified here
- *--acl-file*: when the file system is dumped from a docker container, a lot of permission / owner information gets lost. An acl file generated in the docker container by `getfacl` can be used to restore this information after the cotnainer has been dumped into the fs-root.
- *--overlay*: when a container is created the hostname and hosts list is overwritten, this open copies an overlay into the filesystem root to correct for any information docker sets.
- *--no-purge*: by default, any files in fs-root are purged before dumping the container into it, this prevents that to allow the docker container to dump in over an existing rootfs.

The reason for this is because we are exploring docker as an image building tool, modulo the interesting behavior with the hosts and hostname, it seems to work fairly well. However, any other rootfs building tool can be used to generate a tar file that the rest of the scripts can use.

## parted_wrapper.py
The [parted_wrapper.py](scripts/parted_wrapper.py) takes a partition configuration file (eg: base-os/bootable-usb-config/partitioning.yaml) and performs partitioning. It takes the following arguments:
- *--config*: the configuration to use to setup the disks
- *--device*: the configuration file can specify multiple disks, if only one disk is specified in the config this can override the target device (useful for setting up USB drives).
- *--force*: the script prompts for confirmation before erasing the drive, this makes it not prompts
- *--dry*: print commands that will be run, but do not actually apply them!

## setup_disk.py
The [setup_disk.py](scripts/setup_disk.py) script takes a few arguments:
- *--device*: the device it is installing to (NOTE: unlike the parted_wrapper, this will only perform work on a single device at a time)
- *--config*: the config that describes how / what to install (eg: [disk-setup.yaml](base-os/bootable-usb-config/disk-setup.yaml))
- *--source*: the file source to install from (can be a file system or tar)
- *--skip-grub*: skip any grub setup even if it's enabled
- *--dont-umount*: by default the setup partitions are unmounted after setup, this leaves them mounted

I am not overjoyed with how the install / install_to is implemented.. particularly the install from filesystem (as opposed to tar) source I think is not correct and generally it feels brittle. Need to revisit sometime.

The install order of available actions is the following:
- **purge**: remove all files from the filessytem
- **install**: install files from the source to the rootfs (retain directory structure)
- **install_to**: install files / directories from the source to the rootfs (override directory structure with the `to`)
- **replace_patterns**: can replace the `@BOOT_UUID@` and `@ROOTFS_UUID@` in specified files (helpful for grub / fstab setup)
- **post_script**: run a script to setup the disk with any specific information (single argument - where rootfs is in the filesystem)
- **remove**: remove any files / directories that are temporary setup files

The paths are assumed to be relative to the root of the source / target rootfs, as such it is assumed that a given image would normally be paired with a setup configuration that knows where in that image any setup scripts or specific files are (which can vary by image).

# Misc
When setting up a bootable USB often a lot of pages can be dirtied which can take a while to actual write to the USB... this can cause stalling of any unmount commands waiting for data to be written. To get an idea of how much data needs to be written run this command.
```
watch grep -e Dirty: -e Writeback: /proc/meminfo
```

You can often run into issues where operations seem to be taking unusually long because usb IO is slow.

