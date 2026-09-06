import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PracticeNegotiationSession:
    negotiation_id: str
    mode: str
    status: str
    round: int
    max_rounds: int
    human_role: str
    ai_role: str
    ai_personality: str
    property_index: int
    property: Dict[str, Any]
    reference_price: float
    asking_price: float
    target_price: float
    minimum_price: float
    maximum_price: float
    current_offer: Optional[float] = None
    last_human_offer: Optional[float] = None
    last_ai_offer: Optional[float] = None
    agreed_price: Optional[float] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    repeated_offer_count: int = 0
    stagnant_round_count: int = 0
    deadlock_tolerance: float = 1000.0
    deadlock_threshold: int = 3
    deadlock_reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseNegotiationStore(ABC):
    @abstractmethod
    def save(self, session: PracticeNegotiationSession) -> None:
        pass

    @abstractmethod
    def get(self, negotiation_id: str) -> Optional[PracticeNegotiationSession]:
        pass

    @abstractmethod
    def list(self) -> List[PracticeNegotiationSession]:
        pass

    @abstractmethod
    def delete(self, negotiation_id: str) -> bool:
        pass


class InMemoryNegotiationStore(BaseNegotiationStore):
    def __init__(self):
        self._sessions: Dict[str, PracticeNegotiationSession] = {}

    def save(self, session: PracticeNegotiationSession) -> None:
        session.updated_at = time.time()
        self._sessions[session.negotiation_id] = session

    def get(self, negotiation_id: str) -> Optional[PracticeNegotiationSession]:
        return self._sessions.get(negotiation_id)

    def list(self) -> List[PracticeNegotiationSession]:
        return list(self._sessions.values())

    def delete(self, negotiation_id: str) -> bool:
        if negotiation_id not in self._sessions:
            return False
        del self._sessions[negotiation_id]
        return True
