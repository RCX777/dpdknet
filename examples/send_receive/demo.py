#!/usr/bin/env python3

import time

from dpdknet.domain.ovs import *
from dpdknet.domain.net import *
from dpdknet.utils.link import VhostUserLink


br0 = create_bridge('br0', datapath_type = 'netdev')

sender = create_host('sender', 'sender:latest')
receiver = create_host('receiver', 'receiver:latest')

vhost0 = create_port('vhost0', 'br0', cls = OvsPortVhostUser)
vhost1 = create_port('vhost1', 'br0', cls = OvsPortVhostUser)

sender.add_port(vhost0)
receiver.add_port(vhost1)

link = VhostUserLink(vhost0, vhost1, duplex = True)
link.down()
link.up()

sender.start()
receiver.start()


while True:
    time.sleep(10)

