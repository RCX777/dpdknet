from typing import override

from sqlalchemy.orm import Session

from dpdknet.db.models.link import LinkModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.flow import OvsFlow
from dpdknet.domain.ovs.port import OvsPort, OvsPortVhostUser


class Link(BaseWrapper):
    model: LinkModel
    session: Session

    @classmethod
    def create(cls, bridge: str | OvsBridge, port_src: str | OvsPort, port_dst: str | OvsPort, duplex: bool = True):
        if isinstance(bridge, str):
            bridge_wrapper = OvsBridge.get(bridge)
            if not bridge_wrapper:
                raise ValueError(f"Bridge '{bridge}' does not exist.")
        else:
            bridge_wrapper = bridge

        if isinstance(port_src, str):
            port_src_wrapper = OvsPort.get(port_src, bridge_wrapper.name)
            if not port_src_wrapper:
                raise ValueError(f"Source port '{port_src}' does not exist on bridge '{bridge_wrapper.name}'.")
        else:
            port_src_wrapper = port_src

        if isinstance(port_dst, str):
            port_dst_wrapper = OvsPort.get(port_dst, bridge_wrapper.name)
            if not port_dst_wrapper:
                raise ValueError(f"Destination port '{port_dst}' does not exist on bridge '{bridge_wrapper.name}'.")
        else:
            port_dst_wrapper = port_dst

        link = LinkModel(
            bridge=bridge_wrapper.model,
            port_src=port_src_wrapper.model,
            port_dst=port_dst_wrapper.model,
            flow_fwd=None,
            flow_bwd=None,
            duplex=duplex,
        )
        return create_wrapper(link, cls)

    def __init__(self, model: LinkModel, session: Session):
        self.model = model
        self.session = session

    @override
    def _create(self):
        if self.model.port_src.bridge.name != self.model.port_dst.bridge.name:
            raise ValueError('Source and destination ports must be on the same bridge.')

        self._create_flow_fwd()
        if self.model.duplex:
            self._create_flow_bwd()

    @property
    def flow_fwd(self) -> OvsFlow | None:
        if self.model.flow_fwd:
            return OvsFlow(self.model.flow_fwd, self.session)
        return None

    @property
    def flow_bwd(self) -> OvsFlow | None:
        if self.model.flow_bwd:
            return OvsFlow(self.model.flow_bwd, self.session)
        return None

    @property
    def bridge(self) -> OvsBridge:
        return OvsBridge(self.model.bridge, self.session)

    @property
    def port_src(self) -> OvsPort | OvsPortVhostUser:
        if self.model.port_src.type == 'dpdkvhostuser':
            return OvsPortVhostUser(self.model.port_src, self.session)
        return OvsPort(self.model.port_src, self.session)

    @property
    def port_dst(self) -> OvsPort | OvsPortVhostUser:
        if self.model.port_dst.type == 'dpdkvhostuser':
            return OvsPortVhostUser(self.model.port_dst, self.session)
        return OvsPort(self.model.port_dst, self.session)

    def _create_flow_fwd(self):
        self.model.flow_fwd = OvsFlow.create(
            match=f'in_port={self.port_src.port_number}',
            actions=f'output:{self.port_dst.port_number}',
            bridge_name=self.model.bridge.name,
        ).model

    def _create_flow_bwd(self):
        self.model.flow_bwd = OvsFlow.create(
            match=f'in_port={self.port_dst.port_number}',
            actions=f'output:{self.port_src.port_number}',
            bridge_name=self.model.bridge.name,
        ).model

    def down(self):
        if self.flow_fwd:
            self.flow_fwd.delete()

        if self.flow_bwd:
            self.flow_bwd.delete()

    def up(self):
        if not self.flow_fwd:
            self._create_flow_fwd()

        if self.model.duplex and not self.flow_bwd:
            self._create_flow_bwd()
