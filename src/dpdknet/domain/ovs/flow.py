from typing import override
from sqlalchemy.orm import Session

from dpdknet.db.models.ovs import OvsFlowModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.bridge import OvsBridge
from dpdknet.utils.commands import run_command_throw


class OvsFlow(BaseWrapper):
    model: OvsFlowModel
    session: Session

    @classmethod
    def create(cls, match: str, actions: str, bridge_name: str):
        bridge = OvsBridge.get(bridge_name)
        if not bridge:
            raise ValueError(f"Bridge '{bridge_name}' does not exist.")

        flow = OvsFlowModel(match=match, actions=actions, bridge=bridge.model)
        return create_wrapper(flow, cls)

    def __init__(self, model: OvsFlowModel, session: Session):
        self.model = model
        self.session = session

    @property
    def match(self) -> str:
        return self.model.match

    @property
    def actions(self) -> str:
        return self.model.actions

    @property
    def bridge_id(self) -> int:
        return self.model.bridge_id

    @property
    def bridge(self) -> OvsBridge:
        return OvsBridge(self.model.bridge, self.session)

    @property
    def protocol(self) -> str:
        return self.bridge.protocols.split(',')[0] if self.bridge.protocols else 'OpenFlow10'

    def delete(self):
        command = ['ovs-ofctl', 'del-flows', self.bridge.name, self.match]
        _ = run_command_throw(command)
        self.session.delete(self.model)
        self.session.commit()

    def exists(self) -> bool:
        command = ['ovs-ofctl', 'dump-flows', self.bridge.name]
        output = run_command_throw(command)
        return any(self.match in line for line in output.splitlines())

    def get_flow_model_by_match(self) -> OvsFlowModel | None:
        results = self.session.query(OvsFlowModel).filter_by(match=self.match, bridge_id=self.bridge_id)
        for flow in results:
            if flow != self.model:
                return flow
        return None

    @override
    def _create(self):
        existing_flow = self.get_flow_model_by_match()
        if existing_flow:
            command = [
                'ovs-ofctl',
                'mod-flows',
                '-O',
                self.protocol,
                self.bridge.name,
                f'{self.match},actions={existing_flow.actions},{self.actions}',
            ]
            self.session.rollback()
            self.model = existing_flow
        else:
            command = [
                'ovs-ofctl',
                'add-flow',
                '-O',
                self.protocol,
                self.bridge.name,
                f'{self.match},actions={self.actions}',
            ]
        _ = run_command_throw(command)
