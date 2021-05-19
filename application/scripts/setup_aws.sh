#!/bin/bash
echo 0 > ~/setup.log
sudo apt-get remove docker docker-engine docker.io containerd runc
echo 1 > ~/setup.log
sudo apt-get update
echo 2 > ~/setup.log
sudo apt-get -y install apt-transport-https ca-certificates curl gnupg-agent software-properties-common
echo 3 > ~/setup.log
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
echo 4 > ~/setup.log
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
echo 5 > ~/setup.log
sudo apt-get update
echo 6 > ~/setup.log
sudo apt-get -y install docker-ce docker-ce-cli containerd.io
echo 7 > ~/setup.log
sudo apt-get -y install zip
echo 8 > ~/setup.log