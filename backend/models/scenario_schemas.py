from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Any


class ScenarioBase(BaseModel):
    name: str
    description: str
    category: str
    agents: Any
    constraints: Any
    negotiation_config: Any


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioResponse(ScenarioBase):
    id: int

    model_config = ConfigDict(from_attributes=True)