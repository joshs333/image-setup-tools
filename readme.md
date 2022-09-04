# Rauc Setup Tools
The purpose of this repo is to make it easier to make rauc bundles using docker as an image build tool, package that image, partition and install to a disk.

The `base-os` folder provides configuration for a simple operating system image build and scripts to build that image or generate a bootable USB disk with it.

The `nightmare-stick` extends off `base-os` but adds a 'nightmare script' init target that basically prints nasty messages about erasing data and frying the CPU, it does not actually do any of this.. it was intended more as an exercise to confirm my understanding of the init process with linux. *NOTE: yes, this could very easily be used to make an actual nightmare stick... be responsible please, as I take none for this particular use*.

The `setup-stick` is the real purpose of this repo, it provides a way to generate a setup USB that can be plugged into a target machine and automatically partition and flash the computer according to configuration files. After this initial setup the tools here should be helpful in generating rauc bundles using docker as the image build tool and rauc can be used for OTA updates.

# Scripts
The `scripts/` folder contains scripts not specific to any image configuration.
- **package_docker.py**: takes a docker image and exports it to a tar file or folder - can also apply overlays on top of the extract image (usually for /etc/hosts and /etc/hostname which docker overwrites)
- **parted_wrapper.py**: takes a partition configuration file (eg: base-os/bootable-usb-config/partitioning.yaml) and sets up a drive(s)
- **setup_disk.py**: performs disk setup through grub installs and flashing.


## Setup Disk
The setup disk script takes three arguments:
- *--device*: the device it is installing to (NOTE: unlike the parted_wrapper, this will only perform work on a single device at a time)
- *--source*: the file source to install from
- *--config*: the config that describes how / what to install

The configuration file absorbs most of the information, the base-os [disk-setup.yaml](base-os/bootable-usb-config/disk-setup.yaml) is a good reference.

I am not overjoyed with how the install / install_to is implemented.. particularly the install from filesystem (as opposed to tar) source I think is not correct and generally it feels brittle. Need to revisit sometime.


# Misc
When setting up a bootable USB often a lot of pages can be dirtied which can take a while to actual write to the USB... this can cause stalling of any unmount commands waiting for data to be written. To get an idea of how much data needs to be written run this command.
```
watch grep -e Dirty: -e Writeback: /proc/meminfo
```

You can often run into issues where operations seem to be taking unusually long because usb IO is slow.

