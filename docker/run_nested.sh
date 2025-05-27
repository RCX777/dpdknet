#!/usr/bin/env bash

set -e

# Configure hugepages
HUGEPAGE_NR="2048"

echo "vm.nr_hugepages=$HUGEPAGE_NR" | sudo tee /etc/sysctl.d/99-hugepages.conf
sudo sysctl -p /etc/sysctl.d/99-hugepages.conf
echo "$HUGEPAGE_NR" | sudo tee /proc/sys/vm/nr_hugepages
sudo mkdir -p /mnt/huge
if ! mount | grep -q "/mnt/huge"; then
    sudo mount -t hugetlbfs nodev /mnt/huge
fi

make clean && make

docker build -t dpdknet -f docker/Dockerfile .

CONTAINERS=$(docker ps --filter name="dn.*" --filter status=running -aq)
if [ -n "$CONTAINERS" ]; then
    docker container rm -f "$CONTAINERS"
fi
docker volume rm -f openvswitch

docker run --name dpdknet -it --rm \
           --privileged --pid='host' --net='host' \
           -v /var/run/docker.sock:/var/run/docker.sock \
           -v /dev/hugepages:/dev/hugepages \
           -v /mnt/huge:/mnt/huge \
           -v ./examples:/examples \
           -v openvswitch:/var/run/openvswitch \
           dpdknet "$@"

