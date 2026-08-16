from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config.database import get_db
from backend.models.schemas import TaskCreate, TaskResponse
from backend.models.task import Task


router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"],
)


@router.post("/", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
):
    task = Task(
        title=task_data.title,
        description=task_data.description,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task