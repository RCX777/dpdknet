from dpdknet.db.models.host import HostModel
from dpdknet.domain.net.host import Host, DpdkHost

from dpdknet.domain import create_wrapper


def create_host[T: Host](name: str, docker_image: str, cls: type[T] = DpdkHost) -> T:
    host = HostModel(name=name, docker_image=docker_image)
    return create_wrapper(host, cls)

