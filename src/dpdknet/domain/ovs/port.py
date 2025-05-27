from typing import override
from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsPortModel
from dpdknet.domain import BaseWrapper
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.utils.commands import run_command_throw


class OvsPort(BaseWrapper):
    model: OvsPortModel
    session: Session

    def __init__(self, model: OvsPortModel, session: Session):
        self.model = model
        self.session = session

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def type(self) -> str:
        return self.model.type

    @property
    def bridge(self) -> OvsBridge:
        return OvsBridge(self.model.bridge, self.session)

    @property
    def port_number(self) -> int:
        command = ['ovs-vsctl', 'get', 'Interface', self.name, 'ofport']
        return int(run_command_throw(command).strip())

    def delete(self):
        command = ['ovs-vsctl', 'del-port', self.bridge.name, self.name]
        _ = run_command_throw(command)
        self.session.delete(self.model)
        self.session.commit()

    @override
    def create(self):
        command = ['ovs-vsctl', 'add-port', self.bridge.name, self.name]
        _ = run_command_throw(command)


class OvsPortVhostUser(OvsPort):
    def __init__(self, model: OvsPortModel, session: Session):
        super().__init__(model, session)
        self.model.type = 'dpdkvhostuser'

    @override
    def create(self):
        command = ['ovs-vsctl', 'add-port', self.bridge.name, self.name,
                   '--', 'set', 'Interface', self.name,
                   'type=dpdkvhostuser']
        _ = run_command_throw(command)
