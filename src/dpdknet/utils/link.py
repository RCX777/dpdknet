from dpdknet.domain.ovs import create_flow
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.flow import OvsFlow
from dpdknet.domain.ovs.port import OvsPortVhostUser

class Link:
    pass

class VhostUserLink(Link):
    port_src: OvsPortVhostUser
    port_dst: OvsPortVhostUser
    duplex: bool

    bridge: OvsBridge

    flow_fwd: OvsFlow | None = None
    flow_bwd: OvsFlow | None = None

    def __init__(self,
                 port_src: OvsPortVhostUser,
                 port_dst: OvsPortVhostUser,
                 duplex: bool = True):
        self.port_src = port_src
        self.port_dst = port_dst
        self.duplex = duplex

        if port_src.bridge.name != port_dst.bridge.name:
            raise ValueError("Source and destination ports must be on the same bridge.")

        self.bridge = port_src.bridge

        self._create_flow_fwd()
        if duplex:
            self._create_flow_bwd()

    def _create_flow_fwd(self):
        self.flow_fwd = create_flow(
            match = f'in_port={self.port_src.port_number}',
            actions = f'output:{self.port_dst.port_number}',
            bridge_name = self.bridge.name
        )

    def _create_flow_bwd(self):
        self.flow_bwd = create_flow(
            match = f'in_port={self.port_dst.port_number}',
            actions = f'output:{self.port_src.port_number}',
            bridge_name = self.bridge.name
        )

    def down(self):
        if self.flow_fwd:
            self.flow_fwd.delete()
            self.flow_fwd = None

        if self.flow_bwd:
            self.flow_bwd.delete()
            self.flow_bwd = None

    def up(self):
        if not self.flow_fwd:
            self._create_flow_fwd()

        if self.duplex and not self.flow_bwd:
            self._create_flow_bwd()

