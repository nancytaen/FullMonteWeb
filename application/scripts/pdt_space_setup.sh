#!/bin/bash

USERNAME=fullmonteweb
PASSWORD=capstone2020

TAG=master
REGISTRY=registry.gitlab.com
IMAGE=$REGISTRY/fullmonte/pdt-space/pdt-space-run:$TAG


# The local path to be mounted to /meshes in the container
MOUNTED_DRIVE_PATH=~/docker_pdt

# Pull the Docker image
docker login -u $USERNAME -p $PASSWORD $REGISTRY
docker pull $IMAGE

# Allow local access from docker group to X windows server
# (necessary on some hosts, not others - reason unknown)
xhost +local:docker


# Run Docker image
# --rm: Delete container on finish
# -t:   Provide terminal
# -i:   Interactive
# -e:   Set environment variable DISPLAY
# -v:   Mount host path into container <host-path>:<container path>
# --privileged: Allow container access to system sockets (for X)

DOCKER_COMMAND="docker run --rm  \
        -v $MOUNTED_DRIVE_PATH:/sims \
        -v /tmp/.X11-unix/X0:/tmp/.X11-unix/X0 \
        --privileged \
        -e DISPLAY=:0 \
        $IMAGE $1"

#eval $DOCKER_COMMAND > ~/eval_result.log
#$2 = 0 for write output to stdout
#$2 = 1 for write output tp log file
if [ "$2" -ne 1 ]; then
        $DOCKER_COMMAND

else
        $DOCKER_COMMAND > ~/eval_result.log
fi

echo [info] PDT-SPACE run finished

