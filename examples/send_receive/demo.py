#!/usr/bin/env python3

import time

from dpdknet.domain.net.host import Host
from dpdknet.domain.ovs import create_bridge, create_port
from dpdknet.domain.net import create_link, create_host
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser

br0 = create_bridge('br0', datapath_type = 'netdev')

sender = create_host('sender', 'sender:latest')
receiver = create_host('receiver', 'receiver:latest')
receiver_nondpdk = create_host('rec', 'jonlabelle/network-tools:latest', cls = Host)

vhost0 = create_port('vhost0', 'br0', cls = OvsPortVhostUser)
vhost1 = create_port('vhost1', 'br0', cls = OvsPortVhostUser)

veth0 = create_port('veth0', 'br0', cls = OvsPortVeth)
veth1 = create_port('veth1', 'br0', cls = OvsPortVeth)

sender.add_port(vhost0)
receiver.add_port(vhost1)
receiver.add_veth(veth0)
receiver_nondpdk.add_veth(veth1)

link_vhost = create_link(br0, vhost0, vhost1, duplex = True)
link_veth = create_link(br0, vhost0, veth0, duplex = True)
link_veth_nondpdk = create_link(br0, vhost0, veth1, duplex = True)


sender.start()
receiver.start()
receiver_nondpdk.start()



while True:
    time.sleep(10)

