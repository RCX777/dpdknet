#!/bin/bash -e

export PATH="/usr/dpdk/bin:$PATH"

export OVS_SOCK_PATH='/var/run/openvswitch'
export OVS_DB_PATH='/etc/openvswitch'
export OVS_LOG_PATH='/tmp/openvswitch/logs'
export OVS_DATA='/usr/local/share/openvswitch'

export OVS_PIDFILE="$OVS_SOCK_PATH/ovs-vswitchd.pid"
export OVSDB_PIDFILE="$OVS_SOCK_PATH/ovsdb-server.pid"

export OVS_RUNDIR="$OVS_SOCK_PATH"

mkdir -p $OVS_DB_PATH $OVS_SOCK_PATH $OVS_LOG_PATH /usr/local/var/run/openvswitch

ovsdb-tool create $OVS_DB_PATH/conf.db $OVS_DATA/vswitch.ovsschema

ovsdb-server $OVS_DB_PATH/conf.db \
    --remote=punix:$OVS_SOCK_PATH/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --log-file=$OVS_LOG_PATH/ovsdb-server.log \
    --pidfile=$OVSDB_PIDFILE \
    --unixctl=$OVS_SOCK_PATH/ovsdb-server.ctl \
    --detach

# Wait until the socket appears
while [ ! -S "$OVS_SOCK_PATH/db.sock" ]; do sleep 1; done

ovs-vsctl --db=unix:$OVS_SOCK_PATH/db.sock --no-wait init
ovs-vsctl --db=unix:$OVS_SOCK_PATH/db.sock --no-wait \
    set Open_vSwitch . other_config:dpdk-init=true \
    other_config:dpdk-socket-mem="2048,0" \
    other_config:dpdk-hugepage-dir="/mnt/huge"

ovs-vswitchd unix:$OVS_SOCK_PATH/db.sock \
    --pidfile=$OVS_PIDFILE \
    --log-file=$OVS_LOG_PATH/vswitchd.log \
    --unixctl=$OVS_SOCK_PATH/ovs-vswitchd.ctl \
    --detach

# check if docker socket is mounted
if [ ! -S /var/run/docker.sock ]; then
    echo 'Error: the Docker socket file "/var/run/docker.sock" was not found. It should be mounted as a volume.'
    exit 1
fi

# source /opt/venv/bin/activate

# For testing
# ovs-vsctl add-br br0 -- set Bridge br0 datapath_type=netdev protocols=OpenFlow10
# ovs-vsctl add-port br0 vhost-user-1 -- set Interface vhost-user-1 type=dpdkvhostuser
# ovs-vsctl add-port br0 vhost-user-2 -- set Interface vhost-user-2 type=dpdkvhostuser
# ovs-ofctl -O OpenFlow10 add-flow br0 in_port=1,actions=output:2
# ovs-ofctl -O OpenFlow10 add-flow br0 in_port=2,actions=output:1

if [[ $# -eq 0 ]]; then
    exec /bin/bash
else
    exec $*
fi
