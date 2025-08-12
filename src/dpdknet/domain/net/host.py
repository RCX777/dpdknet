import os
import time
from functools import partial
from typing import override

from sqlalchemy.orm import Session

import docker
import docker.errors
from docker.models.containers import Container
from dpdknet.db.models.host import HostModel
from dpdknet.domain.base import BaseWrapper, create_wrapper
from dpdknet.domain.ovs.port import OvsPortVeth, OvsPortVhostUser
from dpdknet.utils.commands import run_command_throw
from dpdknet.utils.threading import ManagedThread as Thread


class Host(BaseWrapper):
    model: HostModel
    session: Session

    dcli: docker.DockerClient
    container: Container | None

    environment: dict[str, str]

    scheduled_funcs: list[partial[None]]
    scheduler_thread: Thread | None

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
        self.scheduler_thread = Thread.get(f'{self.name}_scheduler')
        print(f'[{self.name}] Scheduler thread found:', self.scheduler_thread is not None)

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
        if self.scheduler_thread:
            self.scheduler_thread.stop()


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

    def _wait_until_ready(self, timeout: float = 10):
        def check_timeout(timeout: float):
            if timeout <= 0:
                raise TimeoutError(f'Timeout while waiting for container {self.container_name} to be ready.')
        while self.container is None:
            time.sleep(0.2)
            timeout -= 0.2
            check_timeout(timeout)
        while True:
            self.container.reload()
            if self.container.attrs['State']['Running']:
                break
            time.sleep(0.2)
            timeout -= 0.2
            check_timeout(timeout)
        while True:
            pid = self.pid
            if pid and os.path.exists(f'/proc/{pid}/ns/ipc'):
                break
            time.sleep(0.2)
            timeout -= 0.2
            check_timeout(timeout)
        print(f'[{self.name}] Container started.')

    def _run_scheduled_functions(self):
        for f in self.scheduled_funcs:
            f()
        self.scheduled_funcs.clear()

    def _run_async(self, func: partial[None]):
        thread = Thread(f'{self.name}_{func.__hash__()}', target=func)
        thread.start()

    def _scheduler_thread_func(self, thread: Thread):
        self._wait_until_ready()
        print(f'[{self.name}] Container ready. Running scheduled functions...')
        while not thread.should_stop:
            self._run_scheduled_functions()
            time.sleep(0.5)

    def _on_start(self):
        if not self.scheduler_thread:
            self.scheduler_thread = Thread(f'{self.name}_scheduler',
                                           target=self._scheduler_thread_func)
        else:
            self.scheduler_thread.stop()
        self.scheduler_thread.start()

    def _add_veth(self, veth: OvsPortVeth):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        command = ['ip', 'link', 'set', veth.name, 'netns', str(self.pid)]
        _ = run_command_throw(command)
        command = ['ip', 'link', 'set', f'{veth.name}-ovs', 'up']
        _ = run_command_throw(command)
        command = ['ip', 'link', 'set', veth.name, 'up']
        retcode, output = self.container.exec_run(command, detach=False)
        if retcode != 0:
            raise RuntimeError(f"Failed to set veth '{veth.name}' up: {output.decode()}")

    def add_veth(self, veth: OvsPortVeth):
        self.scheduled_funcs.append(partial(self._add_veth, veth))

    def _copy_file(self, src: str, dst: str,
                   src_container: str | None = None,
                   dst_container: str | None = None):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        if src_container:
            src = f'{src_container}:{src}'
        if dst_container:
            dst = f'{dst_container}:{dst}'
        command = ['docker', 'cp', src, dst]
        retcode, output = run_command_throw(command)
        if retcode != 0:
            raise RuntimeError(f"Failed to copy file to container: {output}")

    def copy_file_scheduled(self, src: str, dst: str,
                            src_container: str | None = None,
                            dst_container: str | None = None):
        self.scheduled_funcs.append(partial(self._copy_file, src, dst, src_container, dst_container))

    def copy_file(self, src: str, dst: str,
                  src_container: str | None = None,
                  dst_container: str | None = None):
        self._copy_file(src, dst, src_container, dst_container)

    def _schedule_cmd(self,
                      command: list[str],
                      show_output: bool = False,
                      detach: bool = False):
        if self.container is None:
            raise RuntimeError('Container is not running.')
        print(f'[{self.name}] Running command: {" ".join(command)}')
        retcode, output = self.container.exec_run(command, detach=detach)
        if retcode != 0:
            raise RuntimeError(f"Command failed: {output}")
        if show_output:
            print(f'[{self.name}] Command output:\n{output}')

    def schedule_cmd(self,
                     command: list[str],
                     output: bool = False,
                     detach: bool = False):
        self.scheduled_funcs.append(partial(self._schedule_cmd,
                                            command,
                                            show_output=output,
                                            detach=detach))
        print(f'[{self.name}] Command scheduled: {" ".join(command)}')

    def exec_cmd(self, command: list[str],
                 print_output: bool = True,
                 blocking: bool = False):
        '''Executes a command in the container and prints the output.
        '''
        self._wait_until_ready()

        def __exec_cmd(command: list[str], print_output: bool = True, *args, **kwargs):
            retcode, output = self.container.exec_run(command, detach=False)
            if retcode != 0:
                raise RuntimeError(f"Command failed: {output.decode()}")
            if print_output:
                print(f'[{self.name}] Command output:\n{output.decode()}')

        if not blocking:
            self._run_async(partial(__exec_cmd, command, print_output))
        else:
            __exec_cmd(command, print_output)


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
