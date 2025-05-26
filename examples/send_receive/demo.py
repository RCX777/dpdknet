#!/usr/bin/env python3

import time

from dpdknet.domain.ovs import *


br0 = create_bridge('br0', datapath_type = 'netdev')

vhost0 = create_port('vhost0', 'br0', cls = OvsPortVhostUser)
vhost1 = create_port('vhost1', 'br0', cls = OvsPortVhostUser)

flow1 = create_flow(f'in_port={vhost0.port_number}',
                    f'output:{vhost1.port_number}',
                    'br0')
flow2 = create_flow(f'in_port={vhost1.port_number}',
                    f'output:{vhost0.port_number}',
                    'br0')

while True:
    time.sleep(10)

