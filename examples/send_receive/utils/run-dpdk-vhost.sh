#!/bin/bash

cpu_mask=0xc
vhost_sock_path=/var/run/openvswitch/vhost-user-$2
memory_size=1024
interface_type="--no-pci --vdev virtio_user1,path=$vhost_sock_path,queues=1"

$1 \
    -m $memory_size \
    --single-file-segments \
    -c $cpu_mask \
    --no-pci \
    $interface_type \
    --proc-type=auto \
    --file-prefix=dpdk-$2 \
    -- $3

