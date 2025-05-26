from subprocess import CalledProcessError
from typing import Any

from dpdknet.db.models.base import Base
from dpdknet.db.models.ovs import OvsBridgeModel, OvsPortModel, OvsFlowModel
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPort, OvsPortVhostUser
from dpdknet.domain.ovs.flow import OvsFlow


from dpdknet import g_session as _session


def _create(model, cls_wrapper):
    try:
        _session.add(model)
        _session.commit()
        wrapper = cls_wrapper(model, _session)
        wrapper.create()
        return wrapper
    except Exception as e:
        _session.rollback()
        raise e


def create_bridge(name: str,
                  datapath_type: str = 'netdev',
                  protocols: str = 'OpenFlow10') -> OvsBridge:
    bridge = OvsBridgeModel(name=name,
                            datapath_type=datapath_type,
                            protocols=protocols)
    return _create(bridge, OvsBridge)


def create_port[T: OvsPort](name: str,
                            bridge_name: str,
                            cls: type[T] = OvsPortVhostUser) -> T:
    bridge = get_bridge_by_name(bridge_name)
    if not bridge:
        raise ValueError(f"Bridge '{bridge_name}' does not exist.")

    port = OvsPortModel(name=name, bridge=bridge)
    return _create(port, cls)


def create_flow(match: str,
                actions: str,
                bridge_name: str) -> OvsFlow:
    bridge = get_bridge_by_name(bridge_name)
    if not bridge:
        raise ValueError(f"Bridge '{bridge_name}' does not exist.")

    flow = OvsFlowModel(match=match, actions=actions, bridge=bridge)
    return _create(flow, OvsFlow)


def get_bridge_by_name(name: str) -> OvsBridgeModel:
    return _session.query(OvsBridgeModel).filter_by(name=name).first()


# from dpdknet.domain.ovs import *
