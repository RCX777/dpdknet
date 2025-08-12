import time

from dpdknet.db.models.base import BaseModel
from dpdknet.db.models.ovs import *
from dpdknet.db.models.host import *
from dpdknet.db.models.link import *

from dpdknet.domain.net.host import Host
from dpdknet.domain.ovs.bridge import OvsBridge

from dpdknet.scheduling.task import TaskScheduler

from dpdknet import g_engine, g_session

class DpdkNet(TaskScheduler):
    async def start(self):
        for host in Host.all():
            host.start()
        time.sleep(5)
        await self.run()

    def cleanup(self):
        bridges = OvsBridge.all()
        for bridge in bridges:
            bridge._delete()
        hosts = Host.all()
        for host in hosts:
            host._delete()
        g_session.commit()
        BaseModel.metadata.drop_all(g_engine)
        BaseModel.metadata.create_all(g_engine)

