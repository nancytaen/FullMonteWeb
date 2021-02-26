#!/bin/bash
sudo apt-get -y purge nvidia*
sudo apt-get -y autoremove
sudo apt-get -y install build-essential dkms

# install nvidia driver
# Commands taken from https://docs.nvidia.com/datacenter/tesla/tesla-installation-notes/index.html#ubuntu-lts
BASE_URL=https://us.download.nvidia.com/tesla
# For supported products on this driver version, refer to https://www.nvidia.com/download/driverResults.aspx/165294/en-us
DRIVER_VERSION=450.80.02
curl -fSsl -O $BASE_URL/$DRIVER_VERSION/NVIDIA-Linux-x86_64-$DRIVER_VERSION.run
sudo sh ~/NVIDIA-Linux-x86_64-$DRIVER_VERSION.run -s

# Commands below are taken from FullMonte wiki https://gitlab.com/FullMonte/FullMonteSW/snippets/1719217
# If you have nvidia-docker 1.0 installed: we need to remove it and all existing GPU containers
docker volume ls -q -f driver=nvidia-docker | xargs -r -I{} -n1 docker ps -q -a -f volume={} | xargs -r docker rm -f
sudo apt-get purge -y nvidia-docker

# Add the package repositories
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update

# Install nvidia-docker2 and reload the Docker daemon configuration
sudo apt-get install -y nvidia-docker2
sudo pkill -SIGHUP dockerd