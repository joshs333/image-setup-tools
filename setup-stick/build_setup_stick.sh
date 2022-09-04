#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__call_dir=$(pwd)


workspace_dir=$__dir/../workspace
downloads_dir=$workspace_dir/downloads
build_dir=$__dir/../

$__dir/../base-os/build_base_os.sh

docker build -f $build_dir/nightmare-stick/setup-stick.docker -t joshs333/rauc-setup/setup:latest $build_dir
