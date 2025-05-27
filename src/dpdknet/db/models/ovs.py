from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dpdknet.db.models.base import BaseModel

class OvsBridgeModel(BaseModel):
    __tablename__: str = 'ovs_bridges'

    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    datapath_type: Mapped[str] = mapped_column(nullable=False, default='netdev')
    protocols: Mapped[str] = mapped_column(nullable=False, default='OpenFlow10')

    ports: Mapped[list['OvsPortModel']] = relationship('OvsPortModel', back_populates='bridge')
    flows: Mapped[list['OvsFlowModel']] = relationship('OvsFlowModel', back_populates='bridge')


class OvsPortModel(BaseModel):
    __tablename__: str = 'ovs_ports'

    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    type: Mapped[str] = mapped_column(nullable=False, default='unset')

    bridge_id: Mapped[int] = mapped_column(ForeignKey('ovs_bridges.id'))
    bridge: Mapped[OvsBridgeModel] = relationship('OvsBridgeModel', back_populates='ports')


class OvsFlowModel(BaseModel):
    __tablename__: str = 'ovs_flows'

    match: Mapped[str] = mapped_column(nullable=False)
    actions: Mapped[str] = mapped_column(nullable=False)

    bridge_id: Mapped[int] = mapped_column(ForeignKey('ovs_bridges.id'))
    bridge: Mapped[OvsBridgeModel] = relationship('OvsBridgeModel', back_populates='flows')
