import time
from functools import partial
from threading import Thread
from typing import override

from sqlalchemy.orm import Session

import docker
from docker.models.containers import Container
from dpdknet.db.models.host import HostModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser
from dpdknet.utils.commands import run_command_throw


class Host(BaseWrapper):
    model: HostModel
    session: Session

    dcli: docker.DockerClient
    container: Container | None = None

    environment: dict[str, str]

    scheduled_funcs: list[partial[None]] = []

    @classmethod
    def create(cls, name: str, docker_image: str):
        model = HostModel(name=name, docker_image=docker_image)
        return create_wrapper(model, cls)

    def __init__(self, model: HostModel, session: Session):
        self.model = model
        self.session = session
        self.dcli = docker.from_env()
        self.environment = {}

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def docker_image(self) -> str:
        return self.model.docker_image

    @property
    def container_name(self) -> str:
        return f'dn.{self.name}'

    @property
    def pid(self) -> int | None:
        return self.container.attrs['State']['Pid'] if self.container else None

    @override
    def _create(self):
        pass

    def start(self):
        self.stop()
        self.container = self.dcli.containers.run(
            image=self.docker_image,
            name=self.container_name,
            environment=self.environment,
            remove=True,
            detach=True,
            tty=True,
            privileged=True,
        )
        thread = Thread(target=self._run_scheduled_functions_blocking)
        thread.start()

    def stop(self):
        if self.container:
            self.container.stop()
            self.container.remove()
            self.container = None

    def _run_scheduled_functions_blocking(self):
        while True:
            if self.container is None:
                time.sleep(0.2)
                continue
            self.container.reload()
            if self.container.attrs['State']['Running']:
                break
            time.sleep(0.2)
        time.sleep(10)
        for f in self.scheduled_funcs:
            f()
        self.scheduled_funcs.clear()
        print(f'[{self.name}] Scheduled functions executed.')

    def _add_veth(self, veth: OvsPortVeth):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        command = ['ip', 'link', 'set', veth.name, 'netns', str(self.pid)]
        _ = run_command_throw(command)
        command = ['ip', 'link', 'set', f'{veth.name}-ovs', 'up']
        _ = run_command_throw(command)
        command = ['ip', 'link', 'set', veth.name, 'up']
        retcode, output = self.container.exec_run(command)
        if retcode != 0:
            raise RuntimeError(f"Failed to set veth '{veth.name}' up: {output.decode()}")

    def add_veth(self, veth: OvsPortVeth):
        self.scheduled_funcs.append(partial(self._add_veth, veth))


class DpdkHost(Host):
    container: Container | None = None

    ports: list[OvsPortVhostUser] = []

    def __init__(self, model: HostModel, session: Session):
        super().__init__(model, session)

        self.environment.update(
            {
                'DPDKNET_EAL_FLAGS': ' '.join(
                    [
                        '--no-pci',
                        '--single-file-segments',
                        '--proc-type=auto',
                        '--file-prefix=dpdk-' + self.name,
                    ]
                ),
            }
        )

    @override
    def start(self):
        self.stop()
        self.container = self.dcli.containers.run(
            image=self.docker_image,
            name=self.container_name,
            environment=self.environment,
            remove=True,
            detach=True,
            tty=True,
            privileged=True,
            volumes={
                '/dev/hugepages': {'bind': '/dev/hugepages', 'mode': 'rw'},
                '/mnt/huge': {'bind': '/mnt/huge', 'mode': 'rw'},
                'openvswitch': {'bind': '/var/run/openvswitch', 'mode': 'ro'},
            },
        )
        thread = Thread(target=self._run_scheduled_functions_blocking)
        thread.start()

    def add_port(self, port: OvsPortVhostUser):
        if port in self.ports:
            return

        self.ports.append(port)

        portid = len(self.ports) - 1
        socket_path = f'/var/run/openvswitch/{port.name}'

        self.environment.update(
            {
                'DPDKNET_EAL_FLAGS': self.environment['DPDKNET_EAL_FLAGS']
                + f' --vdev virtio_user{portid},path={socket_path},queues=1',
            }
        )
