#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__call_dir=$(pwd)

build_dir=$__dir/../

$__dir/../base-os/build_base_os.sh

docker build -f $build_dir/base-os-graphical/base-os-graphical.docker -t joshs333/image-setup/base-os-graphical:latest $build_dir
