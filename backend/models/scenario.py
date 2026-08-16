from sqlalchemy import Column, Integer, String, Text, JSON
from backend.config.database import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)

    agents = Column(JSON, nullable=False)
    constraints = Column(JSON, nullable=False)
    negotiation_config = Column(JSON, nullable=False)