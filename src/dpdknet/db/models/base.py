from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class BaseModel(DeclarativeBase):
    __abstract__: bool = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

