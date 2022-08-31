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
import shlex
import argparse
import subprocess

def convert_to_bytes(size_string):
    if size_string[-1:] == "G":
        return int(size_string[:-1])* 1024 * 1024 * 1024
    if size_string[-1:] == "M":
        return int(size_string[:-1]) * 1024 * 1024
    if size_string[-1:] == "K":
        return int(size_string[:-1]) * 1024
    if size_string[-1:] == "B":
        return int(size_string[:-1])

    return int(size_string)
    
def get_partition_prefix(device):
    if "nvme" in device:
        return device + "p"
    return device


class Partition:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.size = 0
        self.type = "ext4"
        self.name = ""
        self.number = None
        self.flags = []

    def __repr__(self):
        return f"({self.name}, {self.number} {self.size})"

    def command(self):
        if self.type == "empty":
            return ""
        else:
            return f"mkpart {self.type} {self.start}B {self.end}B"

def execute(command, dry = False):
    if dry:
        print(command)
    else:
        subprocess.run(shlex.split(command))

def get_size(disk):
    data = subprocess.check_output(shlex.split(f"parted -s {device} unit B print free"))

    lines = data.decode('utf8').split("\n")[7:-2]
    size = 0
    precise_start = None
    for l in lines:
        data = [b for b in l.split(" ") if "B" in b]
        start = int(data[0][:-1])
        end = int(data[1][:-1])
        printed_size = int(data[2][:-1])
        calculated_size = (end - start + 1)

        size += calculated_size

        if start is not None:
            precise_start = start
    return precise_start, precise_start + size, size

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wrapper around parted to apply partitioning to a disk based on a configuration file.')
    
    # General Arguments
    parser.add_argument('--config', default="partitions.yaml", help='yaml file describing how to set up the disk')
    parser.add_argument('--device', help='target a different disk than specificed in the config file (when there is only one in config)')
    parser.add_argument('--force', action="store_true", help='do not prompt for confirmation #just-do-it')
    parser.add_argument('--dry', action="store_true", help='print commands but do not run')
    args = parser.parse_args()

    config_data = {}
    with open(args.config, 'r') as f:
        config_data = yaml.load(f.read(), Loader = yaml.Loader)

    if "disks" not in config_data:
        print("ERROR: Config must have `disks` tag as root")
        exit(1)

    if os.geteuid() != 0 and not args.dry:
        print("ERROR: Please execute as root or with sudo, or as --dry")
        exit(1)

    disks = config_data["disks"]
    for disk in disks:
        device = None
        if "device" in disk:
            device = disk["device"]
        if args.device is not None and len(disks) == 1:
            device = args.device
        if device is None:
            print("Unable to get a target device.")
            exit(1)

        if not os.path.exists(device):
            print(f"WARN: Cannot format [{device}] does not exist.")
            continue

        table = "gpt"
        if "table" in disk:
            table = disk["table"]


        if "partitions" not in disk or len(disk["partitions"]) == 0:
            print("ERROR: No partitions specified in disk configuration.")
            exit(1)

        print("Starting by erasing disk and writing table.")
        if not args.force:
            input(f"Press [ENTER] to continue (warning will erase {device})")

        devices = glob.glob(f"{device}*")
        for d in devices:
            if d == device:
                continue
            execute(f"umount {d}", dry=args.dry)
            

        execute(f"sfdisk --delete {device}", dry=args.dry)
        execute(f"parted -s {device} mktable {table}", dry=args.dry)
        
        print()
        start, end, size = get_size(device)
        print(f"Working on disk `{device}`, size: {size}, parsing partitions.")
        
        # Track number specified partitions separately
        general_partition_list = []
        number_specified_partitions = {}

        # parse each partition from config -> Partition()
        for partition in disk["partitions"]:
            partition_info = Partition()

            if "type" not in partition:
                print("ERROR: Partition MUST have type set!")
                exit(1)
            if "size" not in partition:
                print("ERROR: Partition MUST have size set!")
                exit(1)
            partition_info.type = partition["type"]
            allowed_types = ["fat32", "ext3", "ext4"]
            if partition_info.type not in allowed_types:
                print("ERROR: Partition type {partition_info.type} is invalid.")
                exit(1)

            partition_info.size = partition["size"]

            # store size as either a % as a float or just bytes as an int
            if partition_info.size[-1] != "%":
                partition_info.size = convert_to_bytes(partition_info.size)

                remainder = partition_info.size % 512
                partition_info.size += 512 - remainder
            else:
                partition_info.size = float(partition_info.size[:-1]) / 100.0

            if "name" in partition:
                partition_info.name = partition["name"]
            if "flags" in partition:
                allowed_flags = ["boot", "esp"]
                for f in partition["flags"]:
                    if f in allowed_flags:
                        partition_info.flags.append(f)
                    else:
                        print(f"WARN: Invalid flag: {f}")
            if "number" in partition:
                partition_info.number = int(partition["number"])
                if partition_info.number in number_specified_partitions:
                    print(f"ERROR: Duplicate numbers specified {partition_info.number}")
                    exit()
                number_specified_partitions[partition_info.number] = partition_info
            else:
                general_partition_list.append(partition_info)

        total_partitions = len(general_partition_list) + len(number_specified_partitions)

        for num in number_specified_partitions:
            if num > total_partitions:
                print(f"ERROR: Partition numbered {num} is greater than the number of partitions.")
                exit()
            if num < 1:
                print(f"ERROR: Partition numbered {num} cannot be allocated... numbers must be [1, #partitions]")
                exit()

        # By now each size is either a % or explicitly in bytes
        specifically_allocated_size = 0
        total_percent_allocated = 0.0
        percent_based_partitions = 0
        for partition in general_partition_list:
            is_percent = type(partition.size) != int
            if not is_percent:
                specifically_allocated_size += partition.size
            else:
                total_percent_allocated += partition.size
                percent_based_partitions += 1
        for num in number_specified_partitions:
            partition = number_specified_partitions[num]
            is_percent = type(partition.size) != int
            if not is_percent:
                specifically_allocated_size += partition.size
            else:
                total_percent_allocated += partition.size
                percent_based_partitions += 1

        if specifically_allocated_size > size:
            print(f"ERROR: Allocated space {specifically_allocated_size} is greater than disk size {size}.")
            exit()

        # check if we need to split %-sized allocation
        if total_percent_allocated > 0.0:
            if math.fabs(total_percent_allocated - 1.0) > 0.01:
                print(f"WARN: Total percentage based allocations add up to {total_percent_allocated * 100}%, not 100%...")

            remaining_sectors = (size - specifically_allocated_size) / 512
            if remaining_sectors < percent_based_partitions:
                print(f"ERROR: only {remaining_sectors} sectors remain... unable to allocate space for {percent_based_partitions} %-sized partitions.")
                exit()
            remaining_sectors -= percent_based_partitions

            # Split remaining space among %-sized partitions
            remainder_sectors = 0.0
            for partition in general_partition_list:
                is_percent = type(partition.size) != int
                if is_percent:
                    allocated = 1 + remaining_sectors * partition.size / total_percent_allocated
                    remainder_sectors += allocated - int(allocated)
                    if remainder_sectors >= 1.0:
                        allocated += 1
                        remainder_sectors -= 1.0
                    partition.size = int(allocated) * 512
            for num in number_specified_partitions:
                partition = number_specified_partitions[num]
                is_percent = type(partition.size) != int
                if is_percent:
                    allocated = 1 + remaining_sectors * partition.size / total_percent_allocated
                    remainder_sectors += allocated - int(allocated)
                    if remainder_sectors >= 1.0:
                        allocated += 1
                        remainder_sectors -= 1.0
                    partition.size = int(allocated) * 512

        k = 0
        current_start = start
        partition_prefix = get_partition_prefix(device)
        make_filesystem = False
        if "make_filesystems" in disk:
            make_filesystem = disk["make_filesystems"]

        for i in range(total_partitions):
            target_partition = None
            if i + 1 in number_specified_partitions:
                target_partition = number_specified_partitions[i + 1]
            else:
                target_partition = general_partition_list[k]
                k += 1

            target_partition.start = current_start
            target_partition.end = current_start + target_partition.size - 1
            current_start = current_start + target_partition.size

            command = target_partition.command()
            if command != "":
                print(f"Creating {partition_prefix}{i + 1} - {target_partition}")
                execute(f"parted -s {device} {command}", dry=args.dry)
                if target_partition.name != "":
                    name_command = f"parted -s {device} name {i + 1} '\"{target_partition.name}\"'"
                    execute(name_command, dry=args.dry)

                for flag in target_partition.flags:
                    execute(f"parted -s {device} set {i + 1} {flag} on", dry=args.dry)

                if make_filesystem:
                    type_to_command_map = {
                        "fat32": "fat"
                    }
                    partition_type = target_partition.type
                    if partition_type in type_to_command_map:
                        partition_type = type_to_command_map[partition_type]

                    time.sleep(0.1)
                    execute(f"mkfs.{partition_type} {partition_prefix}{i + 1}", dry=args.dry)

                    
