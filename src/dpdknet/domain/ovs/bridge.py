from typing import override

from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsBridgeModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.utils.commands import run_command, run_command_throw

from dpdknet.db.session import g_session


class OvsBridge(BaseWrapper):
    model: OvsBridgeModel
    session: Session

    @classmethod
    def get(cls, name: str):
        model = g_session.query(OvsBridgeModel).filter_by(name=name).first()
        if not model:
            return None
        return cls(model, g_session)

    @classmethod
    def all(cls):
        models = g_session.query(OvsBridgeModel).all()
        return [cls(model, g_session) for model in models]

    @classmethod
    def create(cls, name: str, datapath_type: str = 'netdev', protocols: str = 'OpenFlow10'):
        model = OvsBridgeModel(name=name, datapath_type=datapath_type, protocols=protocols)
        return create_wrapper(model, cls)

    def __init__(self, model: OvsBridgeModel, session: Session):
        self.model = model
        self.session = session

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

    async def _delete(self):
        if await self.exists():
            command = ['ovs-vsctl', 'del-br', self.name]
            _ = await run_command_throw(command)

    async def delete(self):
        await self._delete()
        self.session.delete(self.model)
        self.session.commit()

    async def exists(self) -> bool:
        command = ['ovs-vsctl', 'list', 'Bridge', self.name]
        return (await run_command(command))[0] == 0

    @override
    async def _create(self):
        if await self.exists():
            raise RuntimeError(f"OVS Bridge '{self.name}' already exists.")

        command = [
            'ovs-vsctl',
            'add-br',
            self.name,
            '--',
            'set',
            'Bridge',
            self.name,
            f'datapath_type={self.datapath_type}',
            f'protocols={self.protocols}',
        ]
        _ = await run_command_throw(command)
