#!/bin/bash

cpu_mask=0xc
memory_size=1024

$1 \
    $DPDKNET_EAL_FLAGS \
    -m $memory_size \
    -c $cpu_mask
