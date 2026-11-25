#!/bin/bash
# This script downloads the PTB-XL dataset from PhysioNet and extracts it to the current directory.
# Dataset page: https://physionet.org/content/ptb-xl/1.0.3/

set -ex

version="1.0.3" # the latest version, Nov. 9 2022
download_url="https://physionet.org/content/ptb-xl/get-zip/${version}/"  # 1.7Gb
data_dir="data/raw/ptb-xl-${version}"

# create the data directory if it doesn't exist
if [ ! -d ${data_dir} ]; then
    mkdir -p ${data_dir}
fi

wget "${download_url}" && \
    unzip "ptb-xl-${version}.zip" -d ${data_dir} && \
    rm -fv "ptb-xl-${version}.zip"

