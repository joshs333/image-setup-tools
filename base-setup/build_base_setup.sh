#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__call_dir=$(pwd)


build_dir=$__dir/../

$__dir/../base-os-graphical/build_base_os_graphical.sh

docker build -f $build_dir/base-setup/base-setup.docker -t joshs333/image-setup/base-setup:latest $build_dir
