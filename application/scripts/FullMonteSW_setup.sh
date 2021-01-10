#!/bin/bash
USERNAME=fullmonteweb
PASSWORD=capstone2020
# By default we pull from the 'master' branch but if you want to pull from 
# another branch simple change the 'TAG' variable below to the branch name
TAG=master

REGISTRY=registry.gitlab.com

IMG=-run

MIDDLE=fullmonte/fullmontesw/fullmonte$IMG

IMAGE=$REGISTRY/$MIDDLE:$TAG

# The local path to be mounted to /sims in the container
# Both your regular OS and the docker container will be able to see this folder
# Default  location is ~/docker/sims; Comment (#) and edit the following two lines if you do not want to create this default folder
HOME_DIR=~/docker_sims
mkdir -p $HOME_DIR

# Pull the Docker image
docker login -u $USERNAME -p $PASSWORD $REGISTRY
docker pull $IMAGE

# Run Docker image
# --rm: Delete container on finish
# -t:   Provide terminal
# -i:   Interactive
# -e:   Set environment variable DISPLAY
# -v:   Mount host path into container <host-path>:<container path>
# --privileged: Allow container access to system sockets (for X)
# --runtime=nvidia: Uses the NVIDIA runtime to allow access to the hosts GPU

# build the docker command string
DOCKER_COMMAND="docker run --rm  -v $HOME_DIR:/sims -v /tmp/.X11-unix/X0:/tmp/.X11-unix/X0 --privileged -e DISPLAY=:0 --ipc=host $IMAGE /sims/docker.sh"


# run the docker command
eval $DOCKER_COMMAND
echo [info] Simulation run finished