#!/usr/bin/env python3

import asyncio
from dpdknet.dpdknet import DpdkNet
from dpdknet.domain.net.host import DpdkHost, Host
from dpdknet.domain.net.link import Link
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser
from dpdknet.scheduling.task import CmdTask, CopyTask


async def main():
    net = DpdkNet()

    br0 = await OvsBridge.create(name='br0', datapath_type='netdev', protocols='OpenFlow10')

    sender = await DpdkHost.create('sender', 'sender:latest')
    receiver = await DpdkHost.create('r_dpdk', 'receiver:latest')
    receiver_nondpdk = await Host.create('r_veth', 'jonlabelle/network-tools:latest')

    vhost_s = await OvsPortVhostUser.create('vhost_s', 'br0')
    vhost_r = await OvsPortVhostUser.create('vhost_r', 'br0')
    veth = await OvsPortVeth.create('veth', 'br0')

    sender.add_port(vhost_s)
    receiver.add_port(vhost_r)
    receiver_nondpdk.add_veth(veth)

    link_1 = await Link.create(br0, vhost_s, vhost_r, duplex = False)
    link_2 = await Link.create(br0, vhost_s, veth, duplex = False)

    listen_task = CmdTask('listen', 'tcpdump -i veth -c 5 -w /cap.pcapng', receiver_nondpdk)
    net.add_task(listen_task)

    copy_task = CopyTask('copy',
                          '/cap.pcapng',
                          './cap.pcapng',
                          receiver_nondpdk,
                          deps=[listen_task])
    net.add_task(copy_task)

    print_task = CmdTask('print', 'capinfos ./cap.pcapng', deps=[copy_task])
    net.add_task(print_task)

    await net.start([sender, receiver, receiver_nondpdk])

    print(net.tasks['print'].result.stdout)

    await net.cleanup()

if __name__ == '__main__':
    asyncio.run(main())


