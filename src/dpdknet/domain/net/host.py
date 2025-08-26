import os
import asyncio
import time
from typing import Any, Callable, override
from collections.abc import Coroutine
from uuid import uuid4
from functools import partial

from sqlalchemy.orm import Session

import docker
import docker.errors
from docker.models.containers import Container
from dpdknet.db.models.host import HostModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser
from dpdknet.utils.commands import run_command_throw

from dpdknet.db.session import g_session

class Host(BaseWrapper):
    model: HostModel
    session: Session

    dcli: docker.DockerClient
    container: Container | None

    environment: dict[str, str]

    veth_queue: list[Callable[[], Coroutine[Any, Any, None]]]

    @classmethod
    def get(cls, name: str):
        model = g_session.query(HostModel).filter_by(name=name).first()
        if not model:
            return None
        return cls(model, g_session)

    @classmethod
    def all(cls):
        models = g_session.query(HostModel).all()
        return [cls(model, g_session) for model in models]

    @classmethod
    def create(cls, name: str, docker_image: str):
        model = HostModel(name=name, docker_image=docker_image)
        return create_wrapper(model, cls)

    def __init__(self, model: HostModel, session: Session):
        self.model = model
        self.session = session
        self.dcli = docker.from_env()
        try:
            self.container = self.dcli.containers.get(self.container_name)
        except docker.errors.NotFound:
            self.container = None
        self.environment = {}
        self.veth_queue = []

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def docker_image(self) -> str:
        return self.model.docker_image

    @property
    def started(self) -> bool:
        return self.model.started

    @started.setter
    def started(self, value: bool):
        self.model.started = value
        self.session.commit()

    @property
    def container_name(self) -> str:
        return f'dn.{self.name}'

    @property
    def pid(self) -> int | None:
        return self.container.attrs['State']['Pid'] if self.container else None

    @override
    async def _create(self):
        pass

    async def _wait_until_ready(self, timeout: float = 10):
        def check_timeout():
            nonlocal timeout
            time.sleep(0.2)
            timeout -= 0.2
            if timeout <= 0:
                raise TimeoutError(f'Timeout while waiting for container {self.container_name} to be ready.')
        while self.container is None:
            check_timeout()
        while True:
            self.container.reload()
            if self.container.attrs['State']['Running']:
                break
            check_timeout()
        while True:
            pid = self.pid
            if pid and os.path.exists(f'/proc/{pid}/ns/ipc'):
                break
            check_timeout()
        print(f'[{self.name}] Container started.')
        pending = [asyncio.create_task(v()) for v in self.veth_queue]
        self.veth_queue.clear()
        _ = await asyncio.gather(*pending)

    async def start(self):
        self.stop()
        if not self.container:
            self.container = self.dcli.containers.run(
                image=self.docker_image,
                name=self.container_name,
                environment=self.environment,
                remove=True,
                detach=True,
                tty=True,
                privileged=True,
            )
        await self._wait_until_ready()
        self.started = True

    def stop(self):
        if self.container:
            self.container.stop()

    async def _delete(self):
        if self.container:
            print(f'[{self.name}] Deleting container...')
            self.container.remove(force=True)
            self.container = None

    async def delete(self):
        await self._delete()
        self.session.delete(self.model)
        self.session.commit()

    async def _add_veth(self, veth: OvsPortVeth):
        if self.container is None:
            raise RuntimeError('Container is not running. Cannot add veth.')
        command = ['ip', 'link', 'set', veth.name, 'netns', str(self.pid)]
        _ = await run_command_throw(command)
        command = ['ip', 'link', 'set', f'{veth.name}-ovs', 'up']
        _ = await run_command_throw(command)
        command = ['ip', 'link', 'set', veth.name, 'up']
        retcode, output = await asyncio.to_thread(self.container.exec_run, command, detach=False)
        if retcode != 0:
            raise RuntimeError(f"Failed to set veth '{veth.name}' up: {output.decode()}")
        print(f'[{self.name}] Veth {veth.name} added to container {self.container_name}.')

    def add_veth(self, veth: OvsPortVeth):
        self.veth_queue.append(partial(self._add_veth, veth))

    async def copy_file(self, src: str, dst: str,
                  dst_host: 'Host | None' = None):
        if self.container is None or not self.started:
            raise RuntimeError('Container is not running. Cannot copy file.')
        if dst_host is None:
            command = ['docker', 'cp', f'{self.container_name}:{src}', dst]
            retcode, output = await run_command_throw(command)
            if retcode != 0:
                raise RuntimeError(f'Failed to copy file to dpdknet: {output}')
        else:
            tmp = f'/tmp/dpdknet/{uuid4()}'
            if not dst_host.started:
                raise RuntimeError(f'Host "{dst_host.name}" is not started.')
            command = ['docker', 'cp', f'{self.container_name}:{src}', tmp]
            retcode, output = await run_command_throw(command)
            if retcode != 0:
                raise RuntimeError(f"Failed to copy file to dpdknet: {output}")
            command = ['docker', 'cp', tmp, f'{dst_host.container_name}:{dst}']
            retcode, output = await run_command_throw(command)
            if retcode != 0:
                raise RuntimeError(f'Failed to copy file to host "{dst_host.name}": {output}')


class DpdkHost(Host):
    container: Container | None
    started: bool

    ports: list[OvsPortVhostUser]

    def __init__(self, model: HostModel, session: Session):
        super().__init__(model, session)

        self.ports = []

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
    async def start(self):
        self.stop()
        if not self.container:
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
        await self._wait_until_ready()
        self.started = True

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

