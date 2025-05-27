from sqlalchemy.orm import Mapped, mapped_column

from dpdknet.db.models.base import BaseModel

class HostModel(BaseModel):
    __tablename__: str = 'hosts'

    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    docker_image: Mapped[str] = mapped_column(nullable=False)

