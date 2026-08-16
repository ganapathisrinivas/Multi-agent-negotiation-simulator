from pydantic import BaseModel, ConfigDict
from typing import Optional


class AgentBase(BaseModel):
    name: str
    role: str
    goal: str
    personality: str


class AgentCreate(AgentBase):
    scenario_id: int


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None
    personality: Optional[str] = None


class AgentResponse(AgentBase):
    id: int
    scenario_id: int

    model_config = ConfigDict(from_attributes=True)


class AgentAskRequest(BaseModel):
    question: str


class AgentAskResponse(BaseModel):
    agent_id: int
    agent_name: str
    question: str
    answer: str