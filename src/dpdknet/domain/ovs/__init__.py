from dpdknet.db.models.ovs import OvsBridgeModel, OvsPortModel, OvsFlowModel
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPort, OvsPortVhostUser
from dpdknet.domain.ovs.flow import OvsFlow

from dpdknet.domain import create_wrapper, get_wrapper

from dpdknet import g_session as _session



def create_bridge(name: str,
                  datapath_type: str = 'netdev',
                  protocols: str = 'OpenFlow10') -> OvsBridge:
    bridge = OvsBridgeModel(name=name,
                            datapath_type=datapath_type,
                            protocols=protocols)
    return create_wrapper(bridge, OvsBridge)


def create_port[T: OvsPort](name: str,
                            bridge_name: str,
                            cls: type[T] = OvsPortVhostUser) -> T:
    bridge = get_bridge_model_by_name(bridge_name)
    if not bridge:
        raise ValueError(f"Bridge '{bridge_name}' does not exist.")

    port = OvsPortModel(name=name, bridge=bridge)
    return create_wrapper(port, cls)


def create_flow(match: str,
                actions: str,
                bridge_name: str) -> OvsFlow:
    bridge = get_bridge_model_by_name(bridge_name)
    if not bridge:
        raise ValueError(f"Bridge '{bridge_name}' does not exist.")

    flow = OvsFlowModel(match=match, actions=actions, bridge=bridge)
    return create_wrapper(flow, OvsFlow)


def get_bridge_model_by_name(name: str) -> OvsBridgeModel | None:
    return _session.query(OvsBridgeModel).filter_by(name=name).first()

def get_port_model_by_name(name: str) -> OvsPortModel | None:
    return _session.query(OvsPortModel).filter_by(name=name).first()

def get_port_model_by_name_on_bridge(name: str, bridge_name: str) -> OvsPortModel | None:
    bridge = get_bridge_model_by_name(bridge_name)
    if not bridge:
        return None
    return _session.query(OvsPortModel).filter_by(name=name, bridge_id=bridge.id).first()

def get_bridge_by_name(name: str) -> OvsBridge | None:
    model = _session.query(OvsBridgeModel).filter_by(name=name).first()
    return get_wrapper(model, OvsBridge) if model else None

def get_port_by_name(name: str) -> OvsPort | None:
    model = _session.query(OvsPortModel).filter_by(name=name).first()
    return get_wrapper(model, OvsPort) if model else None

def get_vhost_user_port_by_name(name: str) -> OvsPortVhostUser | None:
    model = _session.query(OvsPortModel).filter_by(name=name, type='dpdkvhostuser').first()
    return get_wrapper(model, OvsPortVhostUser) if model else None

def get_vhost_user_port_by_name_on_bridge(name: str, bridge: str) -> OvsPortVhostUser | None:
    port = get_vhost_user_port_by_name(name)
    return port if port and port.bridge.name == bridge else None

