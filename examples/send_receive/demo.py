#!/usr/bin/env python3

import time

from dpdknet.domain.net.host import DpdkHost, Host
from dpdknet.domain.net.link import Link
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser

br0 = OvsBridge.create(name='br0', datapath_type='netdev', protocols='OpenFlow10')

sender = DpdkHost.create('sender', 'sender:latest')
receiver = DpdkHost.create('receiver', 'receiver:latest')
receiver_nondpdk = Host.create('rec', 'jonlabelle/network-tools:latest')

vhost0 = OvsPortVhostUser.create('vhost0', 'br0')
vhost1 = OvsPortVhostUser.create('vhost1', 'br0')

veth0 = OvsPortVeth.create('veth0', 'br0')
veth1 = OvsPortVeth.create('veth1', 'br0')

sender.add_port(vhost0)
receiver.add_port(vhost1)
receiver.add_veth(veth0)
receiver_nondpdk.add_veth(veth1)

link_vhost = Link.create(br0, vhost0, vhost1, duplex = True)
link_veth = Link.create(br0, vhost0, veth0, duplex = True)
link_veth_nondpdk = Link.create(br0, vhost0, veth1, duplex = True)

sender.start()
receiver.start()
receiver_nondpdk.start()

while True:
    time.sleep(10)

