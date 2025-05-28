from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from dpdknet import g_session as _session
from dpdknet.db.models.base import BaseModel


class BaseWrapper(ABC):
    @abstractmethod
    def __init__(self, model: BaseModel, session: Session): ...

    @abstractmethod
    def _create(self): ...


def create_wrapper[W: BaseWrapper](model: BaseModel, cls_wrapper: type[W]) -> W:
    try:
        _session.add(model)
        _session.commit()
        wrapper = cls_wrapper(model, _session)
        wrapper._create()  # pyright: ignore[reportPrivateUsage]
        return wrapper
    except Exception as e:
        _session.rollback()
        raise e


def get_wrapper[W: BaseWrapper](model: BaseModel, cls_wrapper: type[W]) -> W:
    return cls_wrapper(model, _session)
