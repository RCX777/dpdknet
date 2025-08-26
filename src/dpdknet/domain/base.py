from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from dpdknet.db.session import g_session
from dpdknet.db.models.base import BaseModel


class BaseWrapper(ABC):
    @abstractmethod
    def __init__(self, model: BaseModel, session: Session): ...

    @abstractmethod
    async def _create(self): ...


async def create_wrapper[W: BaseWrapper](model: BaseModel, cls_wrapper: type[W]) -> W:
    try:
        g_session.add(model)
        g_session.commit()
        wrapper = cls_wrapper(model, g_session)
        await wrapper._create()  # pyright: ignore[reportPrivateUsage]
        return wrapper
    except Exception as e:
        g_session.rollback()
        raise e

