#!/usr/bin/env python3

import time

from dpdknet.domain.ovs import *


br0 = create_bridge('br0', datapath_type = 'netdev')

vhost0 = create_port('vhost0', 'br0', cls = OvsPortVhostUser)
vhost1 = create_port('vhost1', 'br0', cls = OvsPortVhostUser)

while True:
    time.sleep(10)

