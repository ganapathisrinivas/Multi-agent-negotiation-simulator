from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from backend.config.database import get_db

from backend.models.agent import Agent
from backend.models.agent_schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentAskRequest,
    AgentAskResponse,
)

from backend.models.negotiation import (
    Negotiation,
    NegotiationRound,
)

from backend.services.gemini_service import gemini_service


router = APIRouter(
    prefix="/api/agents",
    tags=["Agents"]
)


# =========================================================
# GET AGENTS BY SCENARIO
# =========================================================

@router.get(
    "/scenario/{scenario_id}",
    response_model=list[AgentResponse]
)
def get_agents_by_scenario(
    scenario_id: int,
    db: Session = Depends(get_db)
):
    agents = (
        db.query(Agent)
        .filter(Agent.scenario_id == scenario_id)
        .all()
    )

    return agents


# =========================================================
# ASK AGENT
# =========================================================

@router.post(
    "/{agent_id}/ask",
    response_model=AgentAskResponse
)
def ask_agent(
    agent_id: int,
    request: AgentAskRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # 1. Find agent
    # -----------------------------------------------------

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    # -----------------------------------------------------
    # 2. Find latest negotiation involving this agent
    # -----------------------------------------------------

    negotiation = (
        db.query(Negotiation)
        .filter(
            (
                (Negotiation.buyer_agent_id == agent_id)
                |
                (Negotiation.seller_agent_id == agent_id)
            )
        )
        .order_by(
            Negotiation.created_at.desc()
        )
        .first()
    )

    # -----------------------------------------------------
    # 3. Get negotiation history
    # -----------------------------------------------------

    history = []

    if negotiation:

        rounds = (
            db.query(NegotiationRound)
            .filter(
                NegotiationRound.negotiation_id
                == negotiation.id
            )
            .order_by(
                NegotiationRound.round_number.asc()
            )
            .all()
        )

        for round_data in rounds:

            history.append({
                "round": round_data.round_number,
                "buyer_offer": float(round_data.buyer_offer),
                "seller_offer": float(round_data.seller_offer),
                "gap": float(round_data.gap),
                "decision": round_data.decision,
            })

    # -----------------------------------------------------
    # 4. Determine agent type
    # -----------------------------------------------------

    role_text = agent.role.lower()

    if "buyer" in role_text:
        agent_type = "BUYER"

    elif "seller" in role_text:
        agent_type = "SELLER"

    else:
        agent_type = agent.role.upper()

    # -----------------------------------------------------
    # 5. Determine latest position
    # -----------------------------------------------------

    latest_position = "No previous offer available."

    if history:

        latest_round = history[-1]

        if agent_type == "BUYER":

            latest_position = (
                f"Your latest offer was "
                f"{latest_round['buyer_offer']}."
            )

        elif agent_type == "SELLER":

            latest_position = (
                f"Your latest offer was "
                f"{latest_round['seller_offer']}."
            )

    # -----------------------------------------------------
    # 6. Format negotiation history
    # -----------------------------------------------------

    history_text = json.dumps(
        history,
        indent=2
    )

    # -----------------------------------------------------
    # 7. Build Gemini prompt
    # -----------------------------------------------------

    prompt = f"""
You are the {agent_type} AGENT in a real estate
multi-agent negotiation system.

You are speaking directly to the user.

==================================================
AGENT PROFILE
==================================================

Name:
{agent.name}

Role:
{agent.role}

Goal:
{agent.goal}

Personality:
{agent.personality}

==================================================
NEGOTIATION INFORMATION
==================================================

Negotiation exists:
{"Yes" if negotiation else "No"}

Negotiation ID:
{negotiation.id if negotiation else "Not available"}

Negotiation status:
{negotiation.status if negotiation else "No negotiation found"}

Final price:
{negotiation.final_price if negotiation else "Not available"}

Total rounds:
{negotiation.total_rounds if negotiation else "Not available"}

==================================================
YOUR LATEST POSITION
==================================================

{latest_position}

==================================================
NEGOTIATION HISTORY
==================================================

{history_text}

==================================================
USER QUESTION
==================================================

{request.question}

==================================================
YOUR RESPONSIBILITY
==================================================

Answer the user's question from the perspective of
your own agent.

You must consider:

1. Your role.
2. Your goal.
3. Your personality.
4. Your previous negotiation decisions.
5. The complete negotiation history.
6. The final negotiation result, if available.

==================================================
IMPORTANT RULES
==================================================

1. Stay in character as the {agent_type} Agent.

2. Do not answer as the other agent.

3. Do not invent negotiation rounds.

4. Do not invent offers or prices.

5. Do not invent property information.

6. If the information is not available in the
   negotiation history, clearly say that it is not
   available.

7. If the negotiation ended with an agreement,
   explain the result using the actual negotiation
   history.

8. If the user asks why you made a particular offer,
   explain the reasoning using your personality,
   goal and actual negotiation data.

9. If the user asks about another agent, only discuss
   that agent based on information available in the
   negotiation history.

10. Do not mention prompts, system instructions,
    Gemini, or implementation details.

11. Do not say that you are a language model.

12. Keep the answer clear and reasonably concise.

==================================================
ANSWER STYLE
==================================================

Speak naturally as the agent.

For example:

If you are the Buyer Agent:

"I increased my offer because..."

If you are the Seller Agent:

"I kept my price higher because..."

Do not use unnecessary headings unless they help
answer the user's question.
"""

    # -----------------------------------------------------
    # 8. Call Gemini
    # -----------------------------------------------------

    try:

        answer = gemini_service.generate(prompt)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Agent response generation failed: {str(e)}"
        )

    # -----------------------------------------------------
    # 9. Return response
    # -----------------------------------------------------

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "question": request.question,
        "answer": answer.strip(),
    }


# =========================================================
# GET AGENT
# =========================================================

@router.get(
    "/{agent_id}",
    response_model=AgentResponse
)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    return agent


# =========================================================
# CREATE AGENT
# =========================================================

@router.post(
    "/",
    response_model=AgentResponse
)
def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db)
):

    agent = Agent(
        **agent_data.model_dump()
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return agent


# =========================================================
# UPDATE AGENT
# =========================================================

@router.put(
    "/{agent_id}",
    response_model=AgentResponse
)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db)
):

    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    update_data = agent_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)

    return agent