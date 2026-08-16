from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    description: str


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)