import asyncio

from dpdknet.db.session import init_session, clean_db

from dpdknet.domain.net.host import Host
from dpdknet.domain.ovs.bridge import OvsBridge

from dpdknet.scheduling.task import TaskScheduler


class DpdkNet(TaskScheduler):
    def __init__(self):
        super().__init__()

    async def start(self, hosts: list[Host]):
        _ = await asyncio.gather(*(host.start() for host in hosts))
        print("Started hosts")
        await self.run()

    async def cleanup(self):
        bridges = OvsBridge.all()
        _ = await asyncio.gather(*(bridge._delete() for bridge in bridges))
        hosts = Host.all()
        _ = await asyncio.gather(*(host._delete() for host in hosts))
        clean_db()

