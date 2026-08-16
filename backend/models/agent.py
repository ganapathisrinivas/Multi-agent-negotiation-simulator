from sqlalchemy import Column, Integer, String, Text, ForeignKey
from backend.config.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)

    scenario_id = Column(
        Integer,
        ForeignKey("scenarios.id"),
        nullable=False
    )

    name = Column(String(100), nullable=False)

    role = Column(String(100), nullable=False)

    goal = Column(Text, nullable=False)

    personality = Column(String(50), nullable=False)