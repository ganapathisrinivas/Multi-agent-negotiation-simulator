from backend.config.database import Base, engine
from backend.models import Task, Scenario, Agent


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database tables initialized successfully")