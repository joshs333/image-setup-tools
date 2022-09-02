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
import subprocess

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wrapper around parted to apply partitioning to a disk based on a configuration file.')
    
    # General Arguments
    parser.add_argument('--image', help='docker image to dump from')
    parser.add_argument('--container-name', help='specify an container name to use (otherwise randomly generalted)')
    parser.add_argument('--fs-root', help='dump to this folder (if tar-file is specified, this is automatically cleaned up after)')
    parser.add_argument('--tar-file', help='where to dump the filesystem')
    parser.add_argument('--acl-file', help='acl file to restore permissions from (relative to fs-root after extraction)')
    parser.add_argument('--overlay', action='append', help='apply an overlay after extraction of the file system')
    parser.add_argument('--no-purge', action="store_true", help='do NOT purge all files from fs-root before copying file-tree')
    args = parser.parse_args()

    if args.image is None:
        print("Please specify image.")
        exit(1)

    tar_file_dest = None
    if args.tar_file is not None:
        tar_file_dest = os.path.abspath(args.tar_file)

    target_fs = os.path.join("/tmp", str(uuid.uuid4()))
    if args.fs_root is None and tar_file_dest is None:
        print("Please specify --tar-file or --fs-root")
        exit(0)

    if args.fs_root is not None:
        target_fs = args.fs_root

    if not os.path.isdir(target_fs):
        os.makedirs(target_fs)

    container_name = str(uuid.uuid4())
    if args.container_name is not None:
        container_name = args.container_name

    r = subprocess.run(shlex.split(f"docker container create --name {container_name} {args.image}"))
    if r.returncode != 0:
        print("Creating container failed :(")
        exit()

    try:
        if not args.no_purge:
            for f in os.listdir(target_fs):
                path = os.path.join(target_fs, f)
                try:
                    shutil.rmtree(path)
                except OSError:
                    os.remove(path)

        print("Copying file tree...")
        r = subprocess.run(shlex.split(f"docker cp {container_name}:/ {target_fs}"))
        if r.returncode != 0:
            print("Creating container failed :(")
            exit()

        for raw_overlay_path in args.overlay:
            if not os.path.isdir(raw_overlay_path):
                continue
            overlay_dir = os.path.abspath(raw_overlay_path)

            def copy(source, dest):
                for f in os.listdir(source):
                    path = os.path.join(source, f)
                    pd = os.path.join(dest, f)

                    if os.path.isdir(path):
                        copy(path, pd)
                    else:
                        shutil.copy(path, pd)
            copy(overlay_dir, target_fs)

        print("Restoring permissions...")
        if args.acl_file is not None:
            acl_file_path = os.path.join(target_fs, args.acl_file)
            if os.path.exists(acl_file_path):
                r = subprocess.run(shlex.split(f"setfacl --restore {acl_file_path}"), cwd=target_fs)
                if r.returncode != 0:
                    print("Permissions restoration failed.")

        if tar_file_dest is not None:
            r = subprocess.run(shlex.split(f"tar -cvf {tar_file_dest} ."), cwd=target_fs)
            if r.returncode != 0:
                print("tar generation failed")
            
            shutil.rmtree(target_fs)
    except Exception as err:
        print("Some failure exporting..." + str(err))

    r = subprocess.run(shlex.split(f"docker rm {container_name}"))
