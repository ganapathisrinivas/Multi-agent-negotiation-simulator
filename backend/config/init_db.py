from backend.config.database import Base, engine
from backend.models import Task


def init_db() -> None:
    Base.metadata.create_all(bind=engine)