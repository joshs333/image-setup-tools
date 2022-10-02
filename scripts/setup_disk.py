#!/usr/bin/env python3
#####
# @file parted_wrapper.py
# @brief read from a configuration file and apply it to a disk or disks
# @author Joshua Spisak (jspisak@andrew.cmu.edu)
# @date 2022-8-29
#####
import os
import time
import math
import yaml
import glob
import uuid
import shlex
import shutil
import argparse
import fileinput
import subprocess

def get_partition_prefix(device):
    if "nvme" in device:
        return device + "p"
    if "mmc" in device:
        return device + "p"
    return device

# Copies a file, does not retain the tree above file
def copy_file_direct(buffer_folder, source, source_type, file, dest):
    if file[0] == "/":
        file = "." + file

    file_path = os.path.join(source, file)
    if source_type == "tar":
        if not os.path.exists(buffer_folder):
            os.makedirs(buffer_folder)

        r = subprocess.run(shlex.split(f"tar -C {buffer_folder} -xvf {source} {file}"))
        if r.returncode != 0:
            print(f"unable to file {file} in {source}")
            return False
        file_path = os.path.join(buffer_folder, file)

    if file_path[-1] == "/" and os.path.isdir(file_path):
        def recursive_move(source, fdest):
            for f in os.listdir(source):
                local_path = os.path.join(source, f)
                dest_path = os.path.join(fdest, f)

                if os.path.exists(dest_path) and not os.path.isdir(dest_path):
                    os.remove(dest_path)
                if os.path.isdir(local_path):
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    recursive_move(local_path, dest_path)
                else:
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.move(local_path, dest_path)
        recursive_move(file_path, dest)
    else:
        if os.path.exists(dest):
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            else:
                os.remove(dest)
        shutil.move(file_path, dest)

    return True

# Copies a file, retains the tree above file
def install_files(source, source_type, file, dest):
    if file != "" and file[0] == "/":
        file = "." + file

    if source_type == "tar":
        if not os.path.exists(buffer_folder):
            os.makedirs(buffer_folder)

        r = subprocess.run(shlex.split(f"tar -C {dest} -xvf {source} {file}"))
        if r.returncode != 0:
            print(f"unable to extract {file} in {source}")
            return False
    else:
        target = os.path.join(dest, file)
        if not os.path.exists(os.path.split(target)[0]):
            os.path.makedirs(os.path.split(target)[0])
        shutil.move(os.path.join(source, file), target)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wrapper around parted to apply partitioning to a disk based on a configuration file.')
    
    # General Arguments
    parser.add_argument('--device', help='target device to setup')
    parser.add_argument('--config', help='configuration file to use to understand what setup steps to perform')
    parser.add_argument('--source', help='file or tar file to install from')
    parser.add_argument('--skip-grub', action="store_true", help='skip grub setup')
    parser.add_argument('--dont-umount', action="store_true", help="don't unmount drives when done")
    args = parser.parse_args()


    if os.geteuid() != 0:
        print("ERROR: Please execute as root or with sudo")
        exit(1)

    temp_setup_dir = os.path.join("/tmp", str(uuid.uuid4()))
    buffer_folder = os.path.join(temp_setup_dir, "buffer")

    def do_before_exit(exit_code = 0):
        if os.path.exists(buffer_folder):
            shutil.rmtree(buffer_folder)
        exit(exit_code)

    config_data = {}
    with open(args.config, 'r') as f:
        config_data = yaml.load(f.read(), Loader = yaml.Loader)


    if args.device is None:
        print("Please specify a --device")
        do_before_exit()

    source_type = None
    source_path = args.source
    if source_path is None:
        print("Please specify a --source")
        do_before_exit()
    if os.path.isdir(source_path):
        source_type = "dir"
    else:
        source_type = "tar"

    grub_partition = 1
    if "grub_setup" in config_data and not args.skip_grub:
        grub_install = True
        grub_config = None
        
        if "install" in config_data["grub_setup"]:
            grub_install = config_data["grub_setup"]["install"]
        if "partition" in config_data["grub_setup"]:
            grub_partition = config_data["grub_setup"]["partition"]
        if "config" in config_data["grub_setup"]:
            grub_config = config_data["grub_setup"]["config"]

        target_partition = get_partition_prefix(args.device) + str(grub_partition)
        if not os.path.exists(target_partition):
            print(f"Can't find efi partition {target_partition}")
            do_before_exit()

        mount_point_cmd = subprocess.check_output(shlex.split(f"lsblk -o MOUNTPOINT {target_partition}"))
        mount_point = mount_point_cmd.decode('utf8').split("\n")[1]

        we_did_mount = False
        if mount_point == "":
            mount_point = os.path.join(temp_setup_dir, "boot_partition")
            os.makedirs(mount_point)
            we_did_mount = True
            r = subprocess.run(shlex.split(f"mount {target_partition} {mount_point}"))
            if r.returncode != 0:
                print(f"Unable to mount efi partition to setup. Please resolve issues with {target_partition}")
                do_before_exit()


        failed = False
        if grub_install:
            try:
                r = subprocess.run(shlex.split(f"grub-install --removable --target x86_64-efi --efi-directory {mount_point} {args.device}"))
                if r.returncode != 0:
                    print(f"Grub install failed :(")
                    failed = True
            except Exception as err:
                print("grub-install failed :(")
                failed = True
    
        if grub_config is not None:
            copy_file_direct(buffer_folder, source_path, source_type, grub_config, os.path.join(mount_point, "EFI/BOOT/grub.cfg"))

        if we_did_mount and not args.dont_umount:
            r = subprocess.run(shlex.split(f"umount {mount_point}"))
            if r.returncode != 0:
                print(f"Unable to umount efi partition {target_partition} from {mount_point}")
                do_before_exit()
        if failed:
            do_before_exit()

    if "partition_setup" in config_data:
        partition_cfg = config_data["partition_setup"]

        target_partition = get_partition_prefix(args.device) + str(grub_partition)
        if not os.path.exists(target_partition):
            print(f"Can't find efi partition {target_partition}")
            do_before_exit()

        boot_uuid_cmd = subprocess.check_output(shlex.split(f"lsblk -o UUID {target_partition}"))
        boot_uuid = boot_uuid_cmd.decode('utf8').split("\n")[1]

        for target_partition_cfg in partition_cfg:
            if "partition" not in target_partition_cfg:
                print("Each parititon to be set up must have `partition` set.")
                do_before_exit(1)
            partition_id = target_partition_cfg["partition"]

            target_partition = get_partition_prefix(args.device) + str(partition_id)
            if not os.path.exists(target_partition):
                print(f"Can't find efi partition {target_partition}")
                do_before_exit()

            rootfs_uuid_cmd = subprocess.check_output(shlex.split(f"lsblk -o UUID {target_partition}"))
            rootfs_uuid = rootfs_uuid_cmd.decode('utf8').split("\n")[1]

            mount_point_cmd = subprocess.check_output(shlex.split(f"lsblk -o MOUNTPOINT {target_partition}"))
            mount_point = mount_point_cmd.decode('utf8').split("\n")[1]

            we_did_mount = False
            if mount_point == "":
                mount_point = os.path.join(temp_setup_dir, f"partition_{partition_id}")
                os.makedirs(mount_point)
                r = subprocess.run(shlex.split(f"mount {target_partition} {mount_point}"))
                if r.returncode != 0:
                    print(f"Unable to mount efi partition to setup. Please resolve issues with {target_partition}")
                    do_before_exit()
                we_did_mount = True

            failed = False
            try:
                failed = False

                if "purge" in target_partition_cfg and target_partition_cfg["purge"] == True:
                    for f in os.listdir(mount_point):
                        path = os.path.join(mount_point, f)
                        try:
                            shutil.rmtree(path)
                        except OSError:
                            os.remove(path)

                if "install" in target_partition_cfg:
                    for install in target_partition_cfg["install"]:
                        install_files(source_path, source_type, install, mount_point)

                if "install_to" in target_partition_cfg:
                    for install in target_partition_cfg["install_to"]:
                        install_source = [k for k in install.keys()][0]
                        install_dest = install[install_source]
                        if install_dest[0] == "/":
                            install_dest = install_dest[1:]
                        copy_file_direct(buffer_folder, source_path, source_type, install_source, os.path.join(mount_point, install_dest))

                if "replace_patterns" in target_partition_cfg:
                    for f in target_partition_cfg["replace_patterns"]:
                        if f[0] == "/":
                            f = f[1:]
                        target_f = os.path.join(mount_point, f)

                        edit_command = f"sed -i 's/@BOOT_UUID@/{boot_uuid}/g' {target_f}"
                        r = subprocess.run(shlex.split(edit_command))
                        edit_command = f"sed -i 's/@ROOTFS_UUID@/{rootfs_uuid}/g' {target_f}"
                        r = subprocess.run(shlex.split(edit_command))

                if "post_script" in target_partition_cfg:
                    for f in target_partition_cfg["post_script"]:
                        if f[0] == "/":
                            f = f[1:]
                        target_script = os.path.join(mount_point, f)

                        subprocess.run(shlex.split(target_script + " " + mount_point), cwd=mount_point)

                if "remove" in target_partition_cfg:
                    for remove in target_partition_cfg["remove"]:
                        if remove[0] == "/":
                            remove = remove[1:]
                        target_file = os.path.join(mount_point, remove)
                        if os.path.isdir(target_file):
                            shutil.rmtree(target_file)
                        elif os.path.exists(target_file):
                            os.remove(target_file)

            except Exception as err:
                failed = True
                print("Something failed with partition setup " + str(err))


            if we_did_mount and not args.dont_umount:
                print(f"Unmounting {mount_point}")
                r = subprocess.run(shlex.split(f"umount {mount_point}"))
                if r.returncode != 0:
                    print(f"Unable to umount efi partition {target_partition} from {mount_point}")
                    do_before_exit()
            if failed:
                do_before_exit()

    print("All done :)")