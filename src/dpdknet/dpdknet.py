from dpdknet.db.models.base import BaseModel
from dpdknet.db.models.ovs import *
from dpdknet.db.models.host import *
from dpdknet.db.models.link import *

from dpdknet.domain.net.host import Host
from dpdknet.domain.ovs.bridge import OvsBridge

from dpdknet import g_engine


def cleanup():
    bridges = OvsBridge.all()
    for bridge in bridges:
        print(bridge.name)
        bridge._delete()
    hosts = Host.all()
    for host in hosts:
        print(host.name)
        host._delete()
    BaseModel.metadata.drop_all(g_engine)
    BaseModel.metadata.create_all(g_engine)

