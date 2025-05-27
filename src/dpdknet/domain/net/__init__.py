from dpdknet.db.models.host import HostModel
from dpdknet.db.models.link import LinkModel
from dpdknet.domain.net.host import Host, DpdkHost
from dpdknet.domain.net.link import Link

from dpdknet.domain import create_wrapper
from dpdknet.domain.ovs import get_bridge_model_by_name, get_port_model_by_name_on_bridge
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.port import OvsPort


def create_host[T: Host](name: str, docker_image: str, cls: type[T] = DpdkHost) -> T:
    host = HostModel(name=name, docker_image=docker_image)
    return create_wrapper(host, cls)

def create_link(bridge: str | OvsBridge,
                port_src: str | OvsPort,
                port_dst: str | OvsPort,
                duplex: bool = True
                ) -> Link:
    if isinstance(bridge, str):
        bridge_model = get_bridge_model_by_name(bridge)
        if not bridge_model:
            raise ValueError(f"Bridge '{bridge}' does not exist.")
    else:
        bridge_model = bridge.model

    if isinstance(port_src, str):
        port_src_model = get_port_model_by_name_on_bridge(port_src, bridge_model.name)
        if not port_src_model:
            raise ValueError(f"Source port '{port_src}' does not exist on bridge '{bridge_model.name}'.")
    else:
        port_src_model = port_src.model

    if isinstance(port_dst, str):
        port_dst_model = get_port_model_by_name_on_bridge(port_dst, bridge_model.name)
        if not port_dst_model:
            raise ValueError(f"Destination port '{port_dst}' does not exist on bridge '{bridge_model.name}'.")
    else:
        port_dst_model = port_dst.model

    link = LinkModel(
        bridge = bridge_model,
        port_src = port_src_model,
        port_dst = port_dst_model,
        flow_fwd = None,
        flow_bwd = None,
        duplex = duplex
    )
    return create_wrapper(link, Link)

