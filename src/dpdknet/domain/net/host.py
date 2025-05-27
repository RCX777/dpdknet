from typing import overload, override

import docker
from docker.models.containers import Container

from sqlalchemy.orm import Session

from dpdknet.db.models.host import HostModel
from dpdknet.domain import BaseWrapper
from dpdknet.domain.ovs.port import OvsPortVhostUser


class Host(BaseWrapper):
    model: HostModel
    session: Session

    dcli: docker.DockerClient
    container: Container | None = None

    environment: dict[str, str]

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

    @override
    def create(self):
        pass

    def start(self):
        _ = self.dcli.containers.run(
            image = self.docker_image,
            name = self.container_name,
            environment = self.environment,
        )
        self.container = self.dcli.containers.get(
            self.container_name
        )

    def stop(self):
        if self.container:
            self.container.stop()
            self.container.remove()
            self.container = None


class DpdkHost(Host):
    ports: list[OvsPortVhostUser] = []

    def __init__(self, model: HostModel, session: Session):
        super().__init__(model, session)

        self.environment.update({
            'DPDKNET_EAL_FLAGS': ' '.join([
                '--no-pci',
                '--single-file-segments',
                '--proc-type=auto',
                '--file-prefix=dpdk-' + self.name,
            ]),
        })


    @override
    def start(self):
        self.stop()
        _ = self.dcli.containers.run(
            image = self.docker_image,
            name = self.container_name,
            environment = self.environment,
            remove = True,
            detach = True, tty = True,
            privileged = True,
            volumes = {
                '/dev/hugepages': {'bind': '/dev/hugepages', 'mode': 'rw'},
                '/mnt/huge': {'bind': '/mnt/huge', 'mode': 'rw'},
                'openvswitch': {'bind': '/var/run/openvswitch', 'mode': 'ro'},
            },
        )

    def add_port(self, port: OvsPortVhostUser):
        if port in self.ports:
            return

        self.ports.append(port)

        portid = len(self.ports) - 1
        socket_path = f'/var/run/openvswitch/{port.name}'

        self.environment.update({
            'DPDKNET_EAL_FLAGS': self.environment['DPDKNET_EAL_FLAGS'] +
                f' --vdev virtio_user{portid},path={socket_path},queues=1',
        })

