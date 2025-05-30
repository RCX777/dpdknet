import os
import time
from functools import partial
from threading import Thread
from typing import override

from sqlalchemy.orm import Session

import docker
import docker.errors
from docker.models.containers import Container
from dpdknet.db.models.host import HostModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser
from dpdknet.utils.commands import run_command_throw


class Host(BaseWrapper):
    model: HostModel
    session: Session

    dcli: docker.DockerClient
    container: Container | None

    environment: dict[str, str]

    scheduled_funcs: list[partial[None]]
    scheduler_thread: Thread | None
    scheduler_thread_stop: bool

    @classmethod
    def get(cls, name: str):
        from dpdknet import g_session

        model = g_session.query(HostModel).filter_by(name=name).first()
        if not model:
            return None
        return cls(model, g_session)

    @classmethod
    def all(cls):
        from dpdknet import g_session

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
        self.scheduled_funcs = []
        self.scheduler_thread = None
        self.scheduler_thread_stop = False

    def __del__(self):
        self._stop_thread()

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
        self._on_start()

    def _stop_thread(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread_stop = True
            self.scheduler_thread.join()
            self.scheduler_thread = None

    def stop(self):
        if self.container:
            self.container.stop()
        self._stop_thread()

    def _delete(self):
        if self.container:
            print(f'[{self.name}] Deleting container...')
            self.container.remove(force=True)
            self.container = None
        self._stop_thread()

    def delete(self):
        self._delete()
        self.session.delete(self.model)
        self.session.commit()

    def _wait_until_ready(self):
        while self.container is None:
            time.sleep(0.2)
        while True:
            self.container.reload()
            if self.container.attrs['State']['Running']:
                break
            time.sleep(0.2)
        while True:
            pid = self.pid
            if pid and os.path.exists(f'/proc/{pid}/ns/ipc'):
                break
            time.sleep(0.2)
        print(f'[{self.name}] Container started.')

    def _run_scheduled_functions(self):
        for f in self.scheduled_funcs:
            f()
        self.scheduled_funcs.clear()

    def _scheduler_thread_func(self):
        self._wait_until_ready()
        print(f'[{self.name}] Container ready. Running scheduled functions...')
        while self.scheduler_thread_stop is False:
            self._run_scheduled_functions()
            time.sleep(0.5)

    def _on_start(self):
        self.scheduler_thread = Thread(target=self._scheduler_thread_func)
        self.scheduler_thread.start()

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

    def _copy_file(self, src: str, dst: str):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        command = ['docker', 'cp', src, f'{self.container_name}:{dst}']
        retcode, output = run_command_throw(command)
        if retcode != 0:
            raise RuntimeError(f"Failed to copy file to container: {output}")

    def copy_file(self, src: str, dst: str):
        self.scheduled_funcs.append(partial(self._copy_file, src, dst))

    def _exec_cmd(self, command: list[str], detach: bool = False):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        retcode, output = self.container.exec_run(command, detach=detach)
        if detach:
            print(f'[{self.name}] Command scheduled: {" ".join(command)}')
            return
        if retcode != 0:
            raise RuntimeError(f"Command execution failed: {output.decode()}")

    def exec_cmd(self, command: list[str], detach: bool = False):
        self.scheduled_funcs.append(partial(self._exec_cmd, command, detach))


class DpdkHost(Host):
    container: Container | None

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
    def start(self):
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
        self._on_start()

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
