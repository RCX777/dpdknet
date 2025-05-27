from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dpdknet.db.models.base import BaseModel
from dpdknet.db.models.ovs import OvsBridgeModel, OvsPortModel, OvsFlowModel

class LinkModel(BaseModel):
    __tablename__: str = 'links'

    bridge_id: Mapped[int] = mapped_column(ForeignKey('ovs_bridges.id'), nullable=False)
    bridge: Mapped[OvsBridgeModel] = relationship(OvsBridgeModel, back_populates='links')

    port_src_id: Mapped[int] = mapped_column(ForeignKey('ovs_ports.id'), nullable=False)
    port_src: Mapped[OvsPortModel] = relationship(
        OvsPortModel,
        back_populates='links_src',
        foreign_keys=[port_src_id]
    )

    port_dst_id: Mapped[int] = mapped_column(ForeignKey('ovs_ports.id'), nullable=False)
    port_dst: Mapped[OvsPortModel] = relationship(
        OvsPortModel,
        back_populates='links_dst',
        foreign_keys=[port_dst_id]
    )

    flow_fwd_id: Mapped[int] = mapped_column(ForeignKey('ovs_flows.id'), nullable=True)
    flow_fwd: Mapped[OvsFlowModel] = relationship(
        OvsFlowModel,
        back_populates='links_src',
        foreign_keys=[flow_fwd_id]
    )

    flow_bwd_id: Mapped[int] = mapped_column(ForeignKey('ovs_flows.id'), nullable=True)
    flow_bwd: Mapped[OvsFlowModel] = relationship(
        OvsFlowModel,
        back_populates='links_dst',
        foreign_keys=[flow_bwd_id]
    )

    duplex: Mapped[bool] = mapped_column(nullable=False, default=True)

