from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsBridgeModel
from dpdknet.utils.commands import run_command, run_command_throw


class OvsBridge:
    model: OvsBridgeModel
    session: Session

    def __init__(self, model: OvsBridgeModel, session: Session):
        self.model = model
        self.session = session

        if not self.exists():
            self.create()
        else:
            raise RuntimeError(f"OVS Bridge '{self.name}' already exists.")

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def datapath_type(self) -> str:
        return self.model.datapath_type

    @property
    def protocols(self) -> str:
        return self.model.protocols

    @property
    def ports(self):
        return self.model.ports

    def delete(self):
        command = ['ovs-vsctl', 'del-br', self.name]
        _ = run_command_throw(command)
        self.session.delete(self.model)
        self.session.commit()

    def exists(self) -> bool:
        command = ['ovs-vsctl', 'list', 'Bridge', self.name]
        return run_command(command)[1] == 0

    def create(self):
        command = ['ovs-vsctl', 'add-br', self.name, '--', 'set', 'Bridge', self.name,
                   f'datapath_type={self.datapath_type}', f'protocols={self.protocols}']
        _ = run_command_throw(command)

