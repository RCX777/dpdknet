from dpdknet.db.models.ovs import OvsBridgeModel, OvsPortModel
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPort, OvsPortVhostUser


from dpdknet import g_session as _session


def get_bridge_by_name(name: str) -> OvsBridgeModel:
    return _session.query(OvsBridgeModel).filter_by(name=name).first()

def create_bridge(name: str,
                  datapath_type: str = 'netdev',
                  protocols: str = 'OpenFlow10') -> OvsBridge:
    bridge = OvsBridgeModel(name=name,
                            datapath_type=datapath_type,
                            protocols=protocols)
    try:
        _session.add(bridge)
        _session.commit()
        return OvsBridge(bridge, _session)
    except Exception as e:
        _session.rollback()
        raise e

def create_port[T: OvsPort](name: str,
                            bridge_name: str,
                            cls: type[T] = OvsPortVhostUser) -> T:
    bridge = get_bridge_by_name(bridge_name)
    if not bridge:
        raise ValueError(f"Bridge '{bridge_name}' does not exist.")

    port = OvsPortModel(name=name, bridge=bridge)
    try:
        _session.add(port)
        _session.commit()
        return cls(port, _session)
    except Exception as e:
        _session.rollback()
        raise e

# from dpdknet.domain.ovs import *
