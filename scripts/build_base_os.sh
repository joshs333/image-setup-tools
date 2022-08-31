#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__call_dir=$(pwd)

ubuntu_url=http://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release/ubuntu-base-20.04.4-base-amd64.tar.gz

workspace_dir=$__dir/../workspace
downloads_dir=$workspace_dir/downloads
build_dir=$__dir/../

if [[ ! -e $downloads_dir ]]; then
    mkdir -p $downloads_dir
fi

if [[ ! -e $downloads_dir/ubuntu-base-20.04.4-base-amd64.tar.gz ]]; then
    cd $downloads_dir && wget $ubuntu_url
    cd $__call_dir
fi

docker build -f $build_dir/base-os/base-os.docker -t joshs333/rauc-setup/base-os:latest $build_dir
