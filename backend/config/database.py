from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config.settings import settings


engine = create_engine(
    settings.database_url,
    echo=settings.debug,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()