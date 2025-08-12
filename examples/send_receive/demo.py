#!/usr/bin/env python3

import asyncio
from dpdknet.dpdknet import DpdkNet
from dpdknet.domain.net.host import DpdkHost, Host
from dpdknet.domain.net.link import Link
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser


async def main():
    net = DpdkNet()

    br0 = OvsBridge.create(name='br0', datapath_type='netdev', protocols='OpenFlow10')

    sender = DpdkHost.create('sender', 'sender:latest')
    receiver = DpdkHost.create('r_dpdk', 'receiver:latest')
    receiver_nondpdk = Host.create('r_veth', 'jonlabelle/network-tools:latest')

    vhost_s = OvsPortVhostUser.create('vhost_s', 'br0')
    vhost_r = OvsPortVhostUser.create('vhost_r', 'br0')
    veth = OvsPortVeth.create('veth', 'br0')

    sender.add_port(vhost_s)
    receiver.add_port(vhost_r)
    receiver_nondpdk.add_veth(veth)

    link_1 = Link.create(br0, vhost_s, vhost_r, duplex = False)
    link_2 = Link.create(br0, vhost_s, veth, duplex = False)

    net.add_task('listen', 'tcpdump -i veth -c 5 -w out.pcap', 'r_veth')

    await net.start()

    print(net.tasks['listen'].result.stdout)

    net.cleanup()

if __name__ == '__main__':
    asyncio.run(main())


