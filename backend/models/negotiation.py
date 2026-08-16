from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from datetime import datetime

from backend.config.database import Base


class Negotiation(Base):
    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True, index=True)

    scenario_id = Column(
        Integer,
        ForeignKey("scenarios.id"),
        nullable=False
    )

    buyer_agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=False
    )

    seller_agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=False
    )

    status = Column(
        String(50),
        nullable=False
    )

    final_price = Column(
        Float,
        nullable=True
    )

    total_rounds = Column(
        Integer,
        nullable=False,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class NegotiationRound(Base):
    __tablename__ = "negotiation_rounds"

    id = Column(Integer, primary_key=True, index=True)

    negotiation_id = Column(
        Integer,
        ForeignKey("negotiations.id"),
        nullable=False
    )

    round_number = Column(
        Integer,
        nullable=False
    )

    buyer_offer = Column(
        Float,
        nullable=False
    )

    seller_offer = Column(
        Float,
        nullable=False
    )

    gap = Column(
        Float,
        nullable=False
    )

    decision = Column(
        String(50),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )