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
    links: Mapped[list['LinkModel']] = relationship('LinkModel', back_populates='bridge')


class OvsPortModel(BaseModel):
    __tablename__: str = 'ovs_ports'

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    type: Mapped[str] = mapped_column(nullable=False, default='interface')
    port_number: Mapped[int] = mapped_column(nullable=True)

    bridge_id: Mapped[int] = mapped_column(ForeignKey('ovs_bridges.id'))
    bridge: Mapped[OvsBridgeModel] = relationship(OvsBridgeModel, back_populates='ports')

    links_src: Mapped[list['LinkModel']] = relationship(
        'LinkModel',
        back_populates='port_src',
        foreign_keys='LinkModel.port_src_id'
    )

    links_dst: Mapped[list['LinkModel']] = relationship(
        'LinkModel',
        back_populates='port_dst',
        foreign_keys='LinkModel.port_dst_id'
    )


class OvsFlowModel(BaseModel):
    __tablename__: str = 'ovs_flows'

    match: Mapped[str] = mapped_column(nullable=False)
    actions: Mapped[str] = mapped_column(nullable=False)

    bridge_id: Mapped[int] = mapped_column(ForeignKey('ovs_bridges.id'))
    bridge: Mapped[OvsBridgeModel] = relationship(OvsBridgeModel, back_populates='flows')

    links_src: Mapped['LinkModel'] = relationship(
        'LinkModel',
        back_populates='flow_fwd',
        foreign_keys='LinkModel.flow_fwd_id'
    )

    links_dst: Mapped['LinkModel'] = relationship(
        'LinkModel',
        back_populates='flow_bwd',
        foreign_keys='LinkModel.flow_bwd_id'
    )

from dpdknet.db.models.link import LinkModel
