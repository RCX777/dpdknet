#!/usr/bin/env bash

docker run --name dpdk-$1 -it --rm \
       --privileged \
       -v /dev/hugepages:/dev/hugepages \
       -v /mnt/huge:/mnt/huge \
       -v ./apps/$1:/app \
       -v ./utils:/utils \
       -v openvswitch:/var/run/openvswitch:ro \
       dpdk \
       /bin/bash

