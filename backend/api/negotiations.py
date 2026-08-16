from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config.database import get_db
from backend.models import (
    Scenario,
    Agent,
    Negotiation,
    NegotiationRound,
)

from backend.services.negotiation_orchestrator import (
    negotiation_orchestrator,
)


router = APIRouter(
    prefix="/api/negotiations",
    tags=["Negotiations"],
)


# =========================================================
# START NEGOTIATION
# =========================================================

@router.post("/")
def start_negotiation(
    scenario_id: int,
    db: Session = Depends(get_db),
):

    # ---------------------------------------------------------
    # 1. Get scenario
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. Get agents belonging to scenario
    # ---------------------------------------------------------

    agents = (
        db.query(Agent)
        .filter(Agent.scenario_id == scenario_id)
        .all()
    )

    if len(agents) < 2:
        raise HTTPException(
            status_code=400,
            detail="Scenario must have at least two agents",
        )

    # ---------------------------------------------------------
    # 3. Identify Buyer and Seller
    # ---------------------------------------------------------

    buyer = next(
        (
            agent
            for agent in agents
            if "buyer" in agent.role.lower()
        ),
        None,
    )

    seller = next(
        (
            agent
            for agent in agents
            if "seller" in agent.role.lower()
        ),
        None,
    )

    if not buyer or not seller:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not identify buyer and seller agents. "
                "The scenario must contain a Buyer and Seller role."
            ),
        )

    # ---------------------------------------------------------
    # 4. Convert agents to dictionaries
    # ---------------------------------------------------------

    buyer_data = {
        "id": buyer.id,
        "name": buyer.name,
        "role": buyer.role,
        "goal": buyer.goal,
        "personality": buyer.personality,
    }

    seller_data = {
        "id": seller.id,
        "name": seller.name,
        "role": seller.role,
        "goal": seller.goal,
        "personality": seller.personality,
    }

    # ---------------------------------------------------------
    # 5. Read scenario constraints
    # ---------------------------------------------------------

    constraints = scenario.constraints or {}

    # ---------------------------------------------------------
    # 6. Get initial offers
    # ---------------------------------------------------------

    initial_buyer_offer = float(
        constraints.get(
            "buyer_initial_offer",
            415000,
        )
    )

    initial_seller_offer = float(
        constraints.get(
            "seller_initial_offer",
            490000,
        )
    )

    # ---------------------------------------------------------
    # 7. Validate required financial constraints
    # ---------------------------------------------------------

    if "buyer_max_budget" not in constraints:
        raise HTTPException(
            status_code=400,
            detail="Scenario is missing buyer_max_budget",
        )

    if "seller_min_price" not in constraints:
        raise HTTPException(
            status_code=400,
            detail="Scenario is missing seller_min_price",
        )

    # ---------------------------------------------------------
    # 8. Run multi-agent negotiation
    # ---------------------------------------------------------

    result = negotiation_orchestrator.run_negotiation(
        buyer_agent=buyer_data,
        seller_agent=seller_data,
        constraints=constraints,
        initial_buyer_offer=initial_buyer_offer,
        initial_seller_offer=initial_seller_offer,
        max_rounds=10,
    )

    # ---------------------------------------------------------
    # 9. Create negotiation record
    # ---------------------------------------------------------

    negotiation = Negotiation(
        scenario_id=scenario.id,
        buyer_agent_id=buyer.id,
        seller_agent_id=seller.id,
        status=result["status"],
        final_price=result.get("final_price"),
        total_rounds=len(result.get("rounds", [])),
    )

    db.add(negotiation)

    # Generate negotiation ID
    db.flush()

    # ---------------------------------------------------------
    # 10. Save every negotiation round
    # ---------------------------------------------------------

    for round_data in result.get("rounds", []):

        negotiation_round = NegotiationRound(
            negotiation_id=negotiation.id,
            round_number=round_data["round"],
            buyer_offer=round_data["buyer_offer"],
            seller_offer=round_data["seller_offer"],
            gap=round_data.get(
                "gap",
                abs(
                    round_data["seller_offer"]
                    - round_data["buyer_offer"]
                ),
            ),
            decision=round_data.get(
                "decision",
                "counter_offer",
            ),
        )

        db.add(negotiation_round)

    # ---------------------------------------------------------
    # 11. Commit
    # ---------------------------------------------------------

    db.commit()

    db.refresh(negotiation)

    # ---------------------------------------------------------
    # 12. Return complete response
    # ---------------------------------------------------------

    return {
        "negotiation": {
            "id": negotiation.id,
            "status": negotiation.status,
            "final_price": negotiation.final_price,
            "total_rounds": negotiation.total_rounds,
        },

        "scenario": {
            "id": scenario.id,
            "name": scenario.name,
            "category": scenario.category,
        },

        "agents": {
            "buyer": buyer_data,
            "seller": seller_data,
        },

        "result": result,
    }


# =========================================================
# GET NEGOTIATION HISTORY
# =========================================================

@router.get("/{negotiation_id}")
def get_negotiation_history(
    negotiation_id: int,
    db: Session = Depends(get_db),
):

    negotiation = (
        db.query(Negotiation)
        .filter(Negotiation.id == negotiation_id)
        .first()
    )

    if not negotiation:
        raise HTTPException(
            status_code=404,
            detail="Negotiation not found",
        )

    scenario = (
        db.query(Scenario)
        .filter(Scenario.id == negotiation.scenario_id)
        .first()
    )

    buyer = (
        db.query(Agent)
        .filter(Agent.id == negotiation.buyer_agent_id)
        .first()
    )

    seller = (
        db.query(Agent)
        .filter(Agent.id == negotiation.seller_agent_id)
        .first()
    )

    rounds = (
        db.query(NegotiationRound)
        .filter(
            NegotiationRound.negotiation_id == negotiation_id
        )
        .order_by(
            NegotiationRound.round_number
        )
        .all()
    )

    round_data = []

    for negotiation_round in rounds:

        round_data.append({
            "round": negotiation_round.round_number,
            "buyer_offer": negotiation_round.buyer_offer,
            "seller_offer": negotiation_round.seller_offer,
            "gap": negotiation_round.gap,
            "decision": negotiation_round.decision,
        })

    return {
        "negotiation": {
            "id": negotiation.id,
            "status": negotiation.status,
            "final_price": negotiation.final_price,
            "total_rounds": negotiation.total_rounds,
            "created_at": negotiation.created_at,
        },

        "scenario": {
            "id": scenario.id if scenario else None,
            "name": scenario.name if scenario else None,
            "category": scenario.category if scenario else None,
        },

        "agents": {
            "buyer": {
                "id": buyer.id if buyer else None,
                "name": buyer.name if buyer else None,
                "role": buyer.role if buyer else None,
                "personality": buyer.personality if buyer else None,
            },

            "seller": {
                "id": seller.id if seller else None,
                "name": seller.name if seller else None,
                "role": seller.role if seller else None,
                "personality": seller.personality if seller else None,
            },
        },

        "rounds": round_data,
    }


# =========================================================
# GET ALL NEGOTIATIONS
# =========================================================

@router.get("/")
def get_negotiations(
    db: Session = Depends(get_db),
):

    negotiations = (
        db.query(Negotiation)
        .order_by(
            Negotiation.created_at.desc()
        )
        .all()
    )

    result = []

    for negotiation in negotiations:

        scenario = (
            db.query(Scenario)
            .filter(
                Scenario.id == negotiation.scenario_id
            )
            .first()
        )

        buyer = (
            db.query(Agent)
            .filter(
                Agent.id == negotiation.buyer_agent_id
            )
            .first()
        )

        seller = (
            db.query(Agent)
            .filter(
                Agent.id == negotiation.seller_agent_id
            )
            .first()
        )

        result.append({
            "id": negotiation.id,
            "scenario": (
                scenario.name
                if scenario
                else None
            ),
            "buyer": (
                buyer.name
                if buyer
                else None
            ),
            "seller": (
                seller.name
                if seller
                else None
            ),
            "status": negotiation.status,
            "final_price": negotiation.final_price,
            "total_rounds": negotiation.total_rounds,
            "created_at": negotiation.created_at,
        })

    return result