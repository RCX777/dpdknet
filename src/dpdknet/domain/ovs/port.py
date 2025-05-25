from typing import override
from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsPortModel
from dpdknet.utils.commands import run_command_throw


class OvsPort:
    model: OvsPortModel
    session: Session

    def __init__(self, model: OvsPortModel, session: Session):
        self.model = model
        self.session = session

        self.create()

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def bridge(self) -> str:
        return self.model.bridge.name

    def delete(self):
        self.session.delete(self.model)
        self.session.commit()

    def create(self):
        command = ['ovs-vsctl', 'add-port', self.bridge, self.name]
        _ = run_command_throw(command)


class OvsPortVhostUser(OvsPort):
    def __init__(self, model: OvsPortModel, session: Session):
        super().__init__(model, session)

    @override
    def create(self):
        command = ['ovs-vsctl', 'add-port', self.bridge, self.name,
                   '--', 'set', 'Interface', self.name,
                   'type=dpdkvhostuser']
        _ = run_command_throw(command)
