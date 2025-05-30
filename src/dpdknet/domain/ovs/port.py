from typing import override

from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsPortModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.utils.commands import run_command, run_command_throw


class OvsPort(BaseWrapper):
    model: OvsPortModel
    session: Session

    @classmethod
    def all(cls, bridge: OvsBridge):
        from dpdknet import g_session

        ports = g_session.query(OvsPortModel).filter_by(bridge_id=bridge.model.id).all()
        return [cls(port, g_session) for port in ports]

    @classmethod
    def get(cls, name: str, bridge_name: str):
        from dpdknet import g_session

        bridge = OvsBridge.get(bridge_name)
        if not bridge:
            return

        port_model = g_session.query(OvsPortModel).filter_by(name=name, bridge_id=bridge.model.id).first()
        return cls(port_model, g_session) if port_model else None

    @classmethod
    def create(
        cls,
        name: str,
        bridge_name: str,
    ):
        bridge = OvsBridge.get(bridge_name)
        if not bridge:
            raise ValueError(f"Bridge '{bridge_name}' does not exist.")

        port = OvsPortModel(name=name, bridge=bridge.model)
        return create_wrapper(port, cls)

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
    def port_number(self) -> int:
        return self.model.port_number

    def update_port_number(self):
        command = ['ovs-vsctl', 'get', 'Interface', self.name, 'ofport']
        self.model.port_number = int(run_command_throw(command)[1].strip())

    @property
    def bridge(self) -> OvsBridge:
        return OvsBridge(self.model.bridge, self.session)

    def delete(self):
        command = ['ovs-vsctl', 'del-port', self.bridge.name, self.name]
        _ = run_command_throw(command)
        self.session.delete(self.model)
        self.session.commit()

    @override
    def _create(self):
        command = ['ovs-vsctl', 'add-port', self.bridge.name, self.name]
        _ = run_command_throw(command)
        self.update_port_number()


class OvsPortVhostUser(OvsPort):
    def __init__(self, model: OvsPortModel, session: Session):
        super().__init__(model, session)
        self.model.type = 'dpdkvhostuser'

    @override
    def _create(self):
        command = [
            'ovs-vsctl',
            'add-port',
            self.bridge.name,
            self.name,
            '--',
            'set',
            'Interface',
            self.name,
            'type=dpdkvhostuser',
        ]
        _ = run_command_throw(command)
        self.update_port_number()


class OvsPortVeth(OvsPort):
    def __init__(self, model: OvsPortModel, session: Session):
        super().__init__(model, session)
        self.model.type = 'veth'

    @override
    def update_port_number(self):
        command = ['ovs-vsctl', 'get', 'Interface', f'{self.name}-ovs', 'ofport']
        self.model.port_number = int(run_command_throw(command)[1].strip())

    @override
    def _create(self):
        self.veth_pair_create()
        self.veth_pair_up()
        command = ['ovs-vsctl', 'add-port', self.bridge.name, f'{self.name}-ovs']
        _ = run_command_throw(command)
        self.update_port_number()

    def veth_pair_exists(self) -> bool:
        command = ['ip', 'link', 'show', self.name]
        retcode, _ = run_command(command)
        return retcode == 0

    def veth_pair_create(self):
        if self.veth_pair_exists():
            self.veth_pair_delete()
        command = ['ip', 'link', 'add', self.name, 'type', 'veth', 'peer', 'name', f'{self.name}-ovs']
        _ = run_command_throw(command)

    def veth_pair_delete(self):
        command = ['ip', 'link', 'delete', self.name]
        _ = run_command_throw(command)

    def veth_pair_up(self):
        command = ['ip', 'link', 'set', self.name, 'up']
        _ = run_command_throw(command)
        command = ['ip', 'link', 'set', f'{self.name}-ovs', 'up']
        _ = run_command_throw(command)
