from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from dpdknet.db.models.base import Base

class OvsBridgeModel(Base):
    __tablename__: str = 'ovs_bridges'

    id: Column[int] = Column(Integer, primary_key=True)
    name: Column[str] = Column(String, unique=True, nullable=False)

    datapath_type: Column[str] = Column(String, nullable=False, default='netdev')
    protocols: Column[str] = Column(String, nullable=False, default='OpenFlow10')

    ports = relationship('OvsPortModel', back_populates='bridge')

class OvsPortModel(Base):
    __tablename__: str = 'ovs_ports'

    id: Column[int] = Column(Integer, primary_key=True)
    name: Column[str] = Column(String, unique=True, nullable=False)
    bridge_id: Column[int] = Column(Integer, ForeignKey('ovs_bridges.id'))
    bridge = relationship('OvsBridgeModel', back_populates='ports')

