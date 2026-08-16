from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config.database import SessionLocal
from backend.models.scenario import Scenario
from backend.models.scenario_schemas import (
    ScenarioCreate,
    ScenarioResponse,
)

router = APIRouter(
    prefix="/api/scenarios",
    tags=["Scenarios"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[ScenarioResponse])
def get_scenarios(db: Session = Depends(get_db)):
    return db.query(Scenario).all()


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
):
    scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id)
        .first()
    )

    if not scenario:
        raise HTTPException(
            status_code=404,
            detail="Scenario not found",
        )

    return scenario


@router.post("/", response_model=ScenarioResponse)
def create_scenario(
    scenario_data: ScenarioCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Scenario)
        .filter(Scenario.name == scenario_data.name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Scenario with this name already exists",
        )

    scenario = Scenario(
        name=scenario_data.name,
        description=scenario_data.description,
        category=scenario_data.category,
        agents=scenario_data.agents,
        constraints=scenario_data.constraints,
        negotiation_config=scenario_data.negotiation_config,
    )

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return scenario