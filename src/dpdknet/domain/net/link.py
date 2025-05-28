from typing import override

from sqlalchemy.orm import Session

from dpdknet.db.models.link import LinkModel
from dpdknet.domain import BaseWrapper
from dpdknet.domain.ovs import create_flow
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.domain.ovs.flow import OvsFlow
from dpdknet.domain.ovs.port import OvsPort, OvsPortVhostUser


class Link(BaseWrapper):
    model: LinkModel
    session: Session

    def __init__(self, model: LinkModel, session: Session):
        self.model = model
        self.session = session

    @override
    def create(self):
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
        self.model.flow_fwd = create_flow(
            match=f'in_port={self.port_src.port_number}',
            actions=f'output:{self.port_dst.port_number}',
            bridge_name=self.model.bridge.name,
        ).model

    def _create_flow_bwd(self):
        self.model.flow_bwd = create_flow(
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
