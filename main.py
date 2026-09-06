import sys
import os
import uuid
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from dataset_manager import load_dataset
from negotiation_runner import run_negotiation
from agents.orchestrator_agent import OrchestratorAgent
from agents.reasoning_engine import ReasoningEngine
from agents.counteroffer_evaluator import CounterofferEvaluator
from agents.practice_store import (
    PracticeNegotiationSession,
    InMemoryNegotiationStore
)
from agents.practice_agent import (
    PracticeAIAgent,
    extract_offer_from_message,
    extract_offer_from_text,
    format_inr
)


tags_metadata = [
    {
        "name": "Human vs AI Practice Mode",
        "description": "Interactive Human vs AI real-estate negotiation chat. Direct UI available at [**/practice**](/practice).",
    },
    {
        "name": "AI vs AI Simulation",
        "description": "Autonomous multi-agent simulation where AI Buyer and AI Seller negotiate across rounds.",
    },
    {
        "name": "Properties & Scenarios",
        "description": "Dataset queries and scenario definitions.",
    },
]

app = FastAPI(
    title="Real Estate Negotiation Platform",
    description="""
## 🏢 Real Estate Negotiation Platform & AI Practice Mode

### 💬 **[👉 Click Here to Open Live Chat UI (`/practice`)](/practice)**

- **Interactive Practice UI**: [`/practice`](/practice)
- **Human vs AI APIs**: `POST /negotiations/practice` & `POST /negotiations/{negotiation_id}/message`
- **AI vs AI Multi-Agent Simulation**: `POST /negotiations`
- **Property Catalog**: `GET /properties`
""",
    version="1.2.0",
    openapi_tags=tags_metadata
)


# =====================================================
# LOAD DATASET & MANAGERS
# =====================================================

try:
    dataset = load_dataset("dataset_real.csv")
    if dataset is None:
        dataset = []
except Exception as error:
    print("Dataset loading error:", error)
    dataset = []

# In-Memory store for practice mode sessions (pluggable with DB)
practice_store = InMemoryNegotiationStore()

# Practice AI Agent
practice_agent = PracticeAIAgent()


# =====================================================
# ROOT & HEALTH ENDPOINTS
# =====================================================

@app.get("/")
def home():
    return {
        "message": "Real Estate Negotiation Platform API is running",
        "docs": "/docs",
        "practice_ui": "/practice",
        "features": [
            "AI vs AI Multi-Agent Simulation (/negotiations)",
            "Human vs AI Interactive Practice Mode (/negotiations/practice)",
            "Interactive Web UI (/practice)"
        ]
    }


@app.get("/practice", response_class=HTMLResponse, summary="Human vs AI Practice Mode Web UI", tags=["Human vs AI Practice Mode"])
@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def practice_ui():
    """
    Serves the interactive Human vs AI negotiation practice chat user interface.
    """
    template_path = os.path.join(os.path.dirname(__file__), "templates", "practice.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Practice UI template not found</h1>", status_code=404)


@app.get("/health")
def health():
    if dataset is None:
        dataset_loaded = False
        property_count = 0
    elif hasattr(dataset, "empty"):
        dataset_loaded = not dataset.empty
        property_count = len(dataset)
    else:
        dataset_loaded = len(dataset) > 0
        property_count = len(dataset)

    return {
        "status": "running",
        "dataset_loaded": dataset_loaded,
        "property_count": property_count,
        "active_practice_sessions": len(practice_store.list())
    }


# =====================================================
# CONSTANTS & MAPS
# =====================================================

SCENARIOS = {
    1: "Land / Plot",
    2: "Apartment / Flat",
    3: "Villa / Independent House"
}

PERSONALITIES = {
    1: "Aggressive",
    2: "Collaborative",
    3: "Risk-Averse"
}

PERSONALITY_NAME_MAP = {
    "aggressive": "Aggressive",
    "1": "Aggressive",
    "collaborative": "Collaborative",
    "2": "Collaborative",
    "risk_averse": "Risk-Averse",
    "risk-averse": "Risk-Averse",
    "riskaverse": "Risk-Averse",
    "3": "Risk-Averse"
}


# =====================================================
# REQUEST & RESPONSE MODELS
# =====================================================

class NegotiationRequest(BaseModel):
    scenario: int = Field(..., description="Scenario ID (1: Land, 2: Apartment, 3: Villa)", examples=[2])
    buyer_personality: int = Field(..., description="Buyer personality (1: Aggressive, 2: Collaborative, 3: Risk-Averse)", examples=[2])
    seller_personality: int = Field(..., description="Seller personality (1: Aggressive, 2: Collaborative, 3: Risk-Averse)", examples=[2])
    property_index: Optional[int] = Field(0, description="Index of property in dataset", examples=[0])
    max_rounds: int = Field(10, description="Maximum negotiation rounds", examples=[10])


class PracticeNegotiationRequest(BaseModel):
    scenario: int = Field(1, description="Scenario ID (1: Land / Plot, 2: Apartment / Flat, 3: Villa / House)", examples=[2])
    property_index: Optional[int] = Field(None, description="Property index from dataset (0 to total properties - 1, or None for auto-selection)", examples=[0])
    human_role: str = Field("buyer", description="Role of the human participant: 'buyer' or 'seller'", examples=["buyer"])
    ai_personality: str = Field("collaborative", description="AI personality: 'aggressive', 'collaborative', or 'risk_averse'", examples=["collaborative"])
    max_rounds: int = Field(10, description="Maximum number of negotiation rounds", examples=[10])

    model_config = {
        "json_schema_extra": {
            "example": {
                "scenario": 2,
                "property_index": 0,
                "human_role": "buyer",
                "ai_personality": "collaborative",
                "max_rounds": 10
            }
        }
    }


class PracticeNegotiationStartResponse(BaseModel):
    negotiation_id: str = Field(..., description="Unique negotiation session ID", examples=["abc123"])
    mode: str = Field("human_vs_ai", description="Mode identifier", examples=["human_vs_ai"])
    human_role: str = Field(..., description="Human role", examples=["buyer"])
    ai_role: str = Field(..., description="AI agent role", examples=["seller"])
    personality: str = Field("collaborative", description="AI personality", examples=["collaborative"])
    ai_personality: Optional[str] = Field(None, description="AI personality alias", examples=["collaborative"])
    status: str = Field("active", description="Negotiation status", examples=["active"])
    property: Dict[str, Any] = Field(..., description="Selected property details")
    ai_message: str = Field(..., description="Initial greeting from AI agent", examples=["Hello! I am the seller. The property is available. What would you like to offer?"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "negotiation_id": "abc123",
                "mode": "human_vs_ai",
                "human_role": "buyer",
                "ai_role": "seller",
                "personality": "collaborative",
                "status": "active",
                "property": {
                    "Name": "Casagrand ECR 14",
                    "Price": "65.50 Lakhs",
                    "Location": "ECR, Chennai",
                    "Total_Area": "1200 sq.ft"
                },
                "ai_message": "Hello! I am the seller. The property is available. What would you like to offer?"
            }
        }
    }


class HumanMessageRequest(BaseModel):
    message: str = Field(
        ...,
        description="Natural language message or negotiation statement",
        examples=["I will give 25 lakhs for this property"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "I will give 25 lakhs for this property"
            }
        }
    }


class AIResponseDetail(BaseModel):
    decision: str = Field(..., description="Decision: 'ACCEPT', 'REJECT', 'COUNTER', or 'RESPOND'", examples=["COUNTER"])
    counter_offer: Optional[float] = Field(None, description="Counter-offer amount in INR (if decision is COUNTER or ACCEPT)", examples=[6000000])
    message: str = Field(..., description="Natural language AI response", examples=["Thank you for your offer of ₹25 lakhs. Based on the property's value, I can offer ₹35 lakhs."])
    reason: Optional[str] = Field(None, description="Short explanation of AI reasoning", examples=["The human offer is below the target range."])


class PracticeMessageResponse(BaseModel):
    negotiation_id: str = Field(..., examples=["abc123"])
    round: int = Field(..., description="Current round number", examples=[1])
    human_message: str = Field(..., examples=["I will give 25 lakhs for this property"])
    detected_offer: Optional[float] = Field(None, description="Automatically detected offer in INR", examples=[2500000])
    decision: str = Field(..., description="Decision: 'ACCEPT', 'REJECT', 'COUNTER', or 'RESPOND'", examples=["COUNTER"])
    counter_offer: Optional[float] = Field(None, description="Counter offer amount in INR", examples=[3500000])
    ai_message: str = Field(..., description="Natural language AI response message", examples=["Thank you for your offer. Based on the property's value, I counter with ₹35 lakhs."])
    reason: Optional[str] = Field(None, description="AI reasoning summary", examples=["Seller made a concession step."])
    human_offer: Optional[float] = Field(None, description="Human offer in INR (detected from message)", examples=[2500000])
    ai_response: AIResponseDetail = Field(..., description="Detailed AI response object")
    status: str = Field(..., description="Current negotiation status ('active', 'accepted', 'rejected', 'completed')", examples=["active"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "negotiation_id": "abc123",
                "round": 1,
                "human_message": "I will give 25 lakhs for this property",
                "detected_offer": 2500000,
                "decision": "COUNTER",
                "counter_offer": 3500000,
                "ai_message": "Thank you for your offer. Based on the property's value, I counter with ₹35 lakhs.",
                "status": "active"
            }
        }
    }


class NegotiationStateResponse(BaseModel):
    negotiation_id: str
    mode: str
    status: str
    round: int
    max_rounds: int
    human_role: str
    ai_role: str
    ai_personality: str
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
    history: List[Dict[str, Any]]


class NegotiationHistoryResponse(BaseModel):
    negotiation_id: str
    status: str
    total_messages: int
    history: List[Dict[str, Any]]


# =====================================================
# SCENARIOS & PERSONALITIES ENDPOINTS
# =====================================================

@app.get("/scenarios", tags=["Properties & Scenarios"], summary="List Available Property Scenarios")
def get_scenarios():
    return {
        "scenarios": SCENARIOS
    }


@app.get("/personalities", tags=["Properties & Scenarios"], summary="List Supported AI Personalities")
def get_personalities():
    return {
        "personalities": PERSONALITIES
    }


# =====================================================
# PROPERTIES ENDPOINT
# =====================================================

@app.get("/properties", tags=["Properties & Scenarios"], summary="Get Property Catalog from Dataset")
def get_properties(
    scenario: Optional[int] = None,
    start: int = 0,
    limit: int = 1000
):
    if dataset is None or (hasattr(dataset, "empty") and dataset.empty) or (not hasattr(dataset, "empty") and not dataset):
        raise HTTPException(
            status_code=500,
            detail="Dataset is not loaded."
        )

    if start < 0:
        raise HTTPException(status_code=400, detail="Start cannot be negative.")
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than 0.")
    if limit > 1000:
        limit = 1000

    end = start + limit
    properties = []

    if hasattr(dataset, "iloc"):
        selected_data = dataset.iloc[start:end].to_dict(orient="records")
        for index, property_data in enumerate(selected_data, start=start):
            properties.append({
                "index": index,
                "property": property_data
            })
    else:
        selected_data = dataset[start:end]
        for index, property_data in enumerate(selected_data, start=start):
            properties.append({
                "index": index,
                "property": property_data
            })

    return {
        "total_properties": len(dataset),
        "start": start,
        "limit": limit,
        "returned": len(properties),
        "properties": properties
    }


# =====================================================
# PRACTICE MODE ENDPOINTS (HUMAN VS AI)
# =====================================================

@app.post(
    "/negotiations/practice",
    response_model=PracticeNegotiationStartResponse,
    summary="Start a new Human vs AI Practice Negotiation",
    tags=["Human vs AI Practice Mode"]
)
def start_practice_negotiation(request: PracticeNegotiationRequest):
    """
    Initializes an interactive Human vs AI practice negotiation session.
    - Human selects role ('buyer' or 'seller').
    - AI acts as the opposing counterparty with the selected personality ('aggressive', 'collaborative', or 'risk_averse').
    """
    # 1. Validate scenario
    if request.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{request.scenario}'. Choose from: 1 ({SCENARIOS[1]}), 2 ({SCENARIOS[2]}), 3 ({SCENARIOS[3]})."
        )

    # 2. Validate human role
    human_role_clean = request.human_role.strip().lower()
    if human_role_clean not in ["buyer", "seller"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid human_role. Must be either 'buyer' or 'seller'."
        )
    ai_role_clean = "seller" if human_role_clean == "buyer" else "buyer"

    # 3. Validate AI personality
    norm_personality = request.ai_personality.strip().lower().replace("-", "_")
    if norm_personality in ["1", "aggressive"]:
        personality_key = "aggressive"
    elif norm_personality in ["2", "collaborative"]:
        personality_key = "collaborative"
    elif norm_personality in ["3", "risk_averse", "riskaverse"]:
        personality_key = "risk_averse"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ai_personality '{request.ai_personality}'. Choose from 'aggressive', 'collaborative', or 'risk_averse'."
        )

    # 4. Validate Dataset & Property Index
    if dataset is None or (hasattr(dataset, "empty") and dataset.empty):
        raise HTTPException(status_code=500, detail="Dataset is not loaded.")

    if request.property_index is not None and request.property_index >= 0:
        prop_index = request.property_index
        if prop_index < 0 or prop_index >= len(dataset):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid property_index {prop_index}. Dataset contains {len(dataset)} properties (0 to {len(dataset)-1})."
            )
        if hasattr(dataset, "iloc"):
            property_data = dataset.iloc[prop_index].to_dict()
        else:
            property_data = dataset[prop_index]
    else:
        # Automatically select property matching scenario from dataset_real.csv
        from scenarios import SCENARIOS as SCENARIO_DEFS
        from dataset_manager import select_property
        scenario_info = SCENARIO_DEFS.get(request.scenario, {"name": "Apartment / Flat", "keywords": ["flat", "apartment", "bhk"]})
        selected_row = select_property(dataset, scenario_info)
        property_data = selected_row.to_dict() if hasattr(selected_row, "to_dict") else dict(selected_row)
        prop_index = getattr(selected_row, "name", 0)

    reference_price = extract_price(property_data)
    if reference_price is None or reference_price <= 0:
        reference_price = 5000000.0  # Safe 50 Lakh fallback if unparsed

    # 5. Determine Pricing Boundaries based on Roles
    if ai_role_clean == "seller":
        asking_price = reference_price
        target_price = reference_price * 0.95
        minimum_price = reference_price * 0.75
        maximum_price = reference_price * 1.10
    else:  # AI is buyer
        asking_price = reference_price
        target_price = reference_price * 0.90
        minimum_price = reference_price * 0.70
        maximum_price = reference_price * 1.00

    # 6. Generate Session ID and Create Session
    session_id = uuid.uuid4().hex[:8]
    print("[BACKEND] Practice endpoint called")
    print("[PRACTICE_STORE] Creating negotiation")
    print("[BACKEND] Negotiation ID created:", session_id)

    session = PracticeNegotiationSession(
        negotiation_id=session_id,
        mode="human_vs_ai",
        status="active",
        round=1,
        max_rounds=max(1, request.max_rounds),
        human_role=human_role_clean,
        ai_role=ai_role_clean,
        ai_personality=personality_key,
        property_index=prop_index,
        property=property_data,
        reference_price=reference_price,
        asking_price=asking_price,
        target_price=target_price,
        minimum_price=minimum_price,
        maximum_price=maximum_price,
        current_offer=reference_price if ai_role_clean == "seller" else None,
        last_human_offer=None,
        last_ai_offer=reference_price if ai_role_clean == "seller" else None,
        agreed_price=None,
        history=[]
    )

    # 7. Generate Initial Greeting from AI
    ai_greeting = practice_agent.generate_initial_greeting(session)
    
    # Save greeting to history
    session.history.append({
        "round": 0,
        "sender": f"ai_{ai_role_clean}",
        "message": ai_greeting,
        "decision": "INITIAL_GREETING",
        "offer": session.last_ai_offer,
        "timestamp": time.time()
    })

    practice_store.save(session)

    return PracticeNegotiationStartResponse(
        negotiation_id=session.negotiation_id,
        mode=session.mode,
        human_role=session.human_role,
        ai_role=session.ai_role,
        personality=session.ai_personality,
        ai_personality=session.ai_personality,
        status=session.status,
        property=session.property,
        ai_message=ai_greeting
    )


@app.post(
    "/negotiations/{negotiation_id}/message",
    response_model=PracticeMessageResponse,
    summary="Send Human Message or Offer in Practice Mode",
    tags=["Human vs AI Practice Mode"]
)
def send_practice_message(
    negotiation_id: str,
    request: HumanMessageRequest
):
    """
    Submits a message and/or offer from the human participant to the AI counterparty.
    - AI evaluates the offer against property limits, personality rules, and previous history.
    - AI returns an immediate intelligent response with decision ('ACCEPT', 'REJECT', 'COUNTER', 'RESPOND'), counter-offer, and reasoning.
    """
    # 1. Fetch & Validate Session
    print("[API] Message endpoint received")
    print(f"[PRACTICE_STORE] Loading negotiation: {negotiation_id}")
    session = practice_store.get(negotiation_id)
    if not session:
        print(f"[DEBUG] ERROR: Negotiation session '{negotiation_id}' not found in practice_store.")
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation session '{negotiation_id}' not found."
        )

    # 2. Check Active Status
    if session.status != "active":
        print(f"[DEBUG] ERROR: Negotiation '{negotiation_id}' is not active (Status: {session.status}).")
        raise HTTPException(
            status_code=400,
            detail=f"Negotiation '{negotiation_id}' is not active (Current status: '{session.status}')."
        )

    print("[BACKEND] negotiation_id:", negotiation_id)
    print("[BACKEND] Human message:", request.message)
    print(f"[BACKEND] AI personality: {session.ai_personality}")
    print("[PRACTICE_AGENT] Processing human message")

    # 3. Resolve Human Offer via Automatic Analysis
    detected_offer = extract_offer_from_message(request.message)
    print("[BACKEND] Detected offer:", detected_offer)
    print(f"[PRACTICE_AGENT] Detected offer: {detected_offer}")

    # 4. Record Human Turn in History
    human_turn_entry = {
        "round": session.round,
        "sender": f"human_{session.human_role}",
        "message": request.message,
        "offer": detected_offer,
        "timestamp": time.time()
    }
    session.history.append(human_turn_entry)

    if detected_offer is not None:
        session.last_human_offer = detected_offer
        session.current_offer = detected_offer

    # 5. AI Agent Evaluates Context & Generates Response
    ai_result = practice_agent.evaluate_and_respond(
        session=session,
        human_message=request.message,
        explicit_offer=detected_offer
    )

    decision = ai_result["decision"]
    counter_offer = ai_result["counter_offer"]
    ai_message = ai_result["message"]
    reason = ai_result["reason"]

    print("[BACKEND] AI response:", ai_message)
    if counter_offer is not None:
        print(f"[BACKEND] Counter offer: {counter_offer}")

    # 6. Update Session State
    if decision == "ACCEPT":
        session.status = "accepted"
        session.agreed_price = counter_offer or detected_offer
        session.current_offer = session.agreed_price
    elif decision == "REJECT":
        session.status = "rejected"
    elif decision == "COUNTER":
        if counter_offer is not None:
            session.last_ai_offer = counter_offer
            session.current_offer = counter_offer

    # Check Max Rounds
    if session.status == "active" and session.round >= session.max_rounds:
        session.status = "completed"
        ai_message += f"\n\n[Negotiation ended: Maximum rounds ({session.max_rounds}) reached.]"

    # 7. Record AI Turn in History
    ai_turn_entry = {
        "round": session.round,
        "sender": f"ai_{session.ai_role}",
        "decision": decision,
        "offer": counter_offer,
        "message": ai_message,
        "reason": reason,
        "timestamp": time.time()
    }
    session.history.append(ai_turn_entry)

    # Prepare response data before round increment
    current_round = session.round
    if session.status == "active":
        session.round += 1

    practice_store.save(session)
    print("[BACKEND] Saving negotiation history")
    print("[PRACTICE_STORE] Saving updated negotiation state")

    return PracticeMessageResponse(
        negotiation_id=session.negotiation_id,
        round=current_round,
        human_message=request.message,
        detected_offer=detected_offer,
        decision=decision,
        counter_offer=counter_offer,
        ai_message=ai_message,
        reason=reason,
        human_offer=detected_offer,
        ai_response=AIResponseDetail(
            decision=decision,
            counter_offer=counter_offer,
            message=ai_message,
            reason=reason
        ),
        status=session.status
    )


@app.get(
    "/negotiations/{negotiation_id}",
    response_model=NegotiationStateResponse,
    summary="Get Negotiation State",
    tags=["Human vs AI Practice Mode"]
)
def get_negotiation_state(negotiation_id: str):
    """
    Returns full current state and metrics for the given negotiation session.
    """
    session = practice_store.get(negotiation_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation session '{negotiation_id}' not found."
        )

    return NegotiationStateResponse(
        negotiation_id=session.negotiation_id,
        mode=session.mode,
        status=session.status,
        round=session.round,
        max_rounds=session.max_rounds,
        human_role=session.human_role,
        ai_role=session.ai_role,
        ai_personality=session.ai_personality,
        property=session.property,
        reference_price=session.reference_price,
        asking_price=session.asking_price,
        target_price=session.target_price,
        minimum_price=session.minimum_price,
        maximum_price=session.maximum_price,
        current_offer=session.current_offer,
        last_human_offer=session.last_human_offer,
        last_ai_offer=session.last_ai_offer,
        agreed_price=session.agreed_price,
        history=session.history
    )


@app.get(
    "/negotiations/{negotiation_id}/history",
    response_model=NegotiationHistoryResponse,
    summary="Get Negotiation History",
    tags=["Human vs AI Practice Mode"]
)
def get_negotiation_history(negotiation_id: str):
    """
    Returns complete chronological transcript of messages and turns in the negotiation.
    """
    session = practice_store.get(negotiation_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation session '{negotiation_id}' not found."
        )

    return NegotiationHistoryResponse(
        negotiation_id=session.negotiation_id,
        status=session.status,
        total_messages=len(session.history),
        history=session.history
    )


@app.post(
    "/negotiations/{negotiation_id}/cancel",
    summary="Cancel / End Practice Negotiation",
    tags=["Human vs AI Practice Mode"]
)
def cancel_negotiation(negotiation_id: str):
    """
    Allows a participant to explicitly end and cancel an active negotiation session.
    """
    session = practice_store.get(negotiation_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation session '{negotiation_id}' not found."
        )

    if session.status != "active":
        return {
            "negotiation_id": session.negotiation_id,
            "status": session.status,
            "message": f"Session was already {session.status}."
        }

    session.status = "cancelled"
    session.history.append({
        "round": session.round,
        "sender": "system",
        "message": "Negotiation session was cancelled by the user.",
        "timestamp": time.time()
    })
    practice_store.save(session)

    return {
        "negotiation_id": session.negotiation_id,
        "status": "cancelled",
        "message": "Negotiation cancelled successfully."
    }


# =====================================================
# AI-VS-AI SIMULATION ENDPOINT (EXISTING)
# =====================================================

@app.post(
    "/negotiations",
    summary="Start AI vs AI Multi-Agent Simulation",
    tags=["AI vs AI Simulation"]
)
def start_negotiation(
    request: NegotiationRequest
):
    if request.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail="Invalid scenario. Choose 1, 2 or 3."
        )

    if request.buyer_personality not in PERSONALITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid buyer personality."
        )

    if request.seller_personality not in PERSONALITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid seller personality."
        )

    if dataset is None or (hasattr(dataset, "empty") and dataset.empty):
        raise HTTPException(
            status_code=500,
            detail="Dataset is not loaded."
        )

    property_index = request.property_index or 0

    if property_index < 0 or property_index >= len(dataset):
        raise HTTPException(
            status_code=400,
            detail="Invalid property index."
        )

    if hasattr(dataset, "iloc"):
        property_data = dataset.iloc[property_index].to_dict()
    else:
        property_data = dataset[property_index]

    reference_price = extract_price(property_data)
    if reference_price is None:
        raise HTTPException(
            status_code=400,
            detail="Could not determine property price."
        )

    buyer_personality = PERSONALITIES[request.buyer_personality]
    seller_personality = PERSONALITIES[request.seller_personality]

    buyer_target = reference_price * 0.90
    buyer_minimum = reference_price * 0.70
    buyer_maximum = reference_price

    seller_target = reference_price * 0.95
    seller_minimum = reference_price * 0.75
    seller_maximum = reference_price

    buyer_evaluator = CounterofferEvaluator(
        role="buyer",
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    seller_evaluator = CounterofferEvaluator(
        role="seller",
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    buyer_reasoning = ReasoningEngine(
        role="Buyer Agent",
        persona=buyer_personality,
        goals="Buy the property at a reasonable price while staying within budget.",
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    seller_reasoning = ReasoningEngine(
        role="Seller Agent",
        persona=seller_personality,
        goals="Sell the property at a good price while remaining willing to negotiate.",
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    orchestrator = OrchestratorAgent(["Buyer Agent", "Seller Agent"])

    try:
        result = run_negotiation(
            orchestrator=orchestrator,
            buyer_reasoning=buyer_reasoning,
            seller_reasoning=seller_reasoning,
            buyer_evaluator=buyer_evaluator,
            seller_evaluator=seller_evaluator,
            property_data=property_data,
            reference_price=reference_price,
            max_rounds=request.max_rounds
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    return {
        "status": result.get("status"),
        "agreed_price": result.get("agreed_price"),
        "scenario": SCENARIOS[request.scenario],
        "buyer_personality": buyer_personality,
        "seller_personality": seller_personality,
        "property": property_data,
        "negotiation_history": orchestrator.get_history(),
        "current_state": orchestrator.get_state()
    }


# =====================================================
# PRICE EXTRACTION HELPER
# =====================================================

def extract_price(property_data):
    if not isinstance(property_data, dict):
        return None

    possible_columns = [
        "Price",
        "price",
        "PRICE",
        "Property Price",
        "property_price"
    ]

    for column in possible_columns:
        if column not in property_data:
            continue

        value = property_data[column]
        if value is None:
            continue

        try:
            value_string = str(value).strip()
            cleaned = (
                value_string
                .replace(",", "")
                .replace("₹", "")
                .replace("Rs.", "")
                .replace("Rs", "")
                .strip()
            )
            lower_value = cleaned.lower()

            if "lakhs" in lower_value:
                number = float(lower_value.replace("lakhs", "").strip())
                return number * 100000

            if "lakh" in lower_value:
                number = float(lower_value.replace("lakh", "").strip())
                return number * 100000

            if lower_value.endswith("l"):
                number = float(lower_value[:-1].strip())
                return number * 100000

            if "crores" in lower_value:
                number = float(lower_value.replace("crores", "").strip())
                return number * 10000000

            if "crore" in lower_value:
                number = float(lower_value.replace("crore", "").strip())
                return number * 10000000

            if lower_value.endswith("cr"):
                number = float(lower_value[:-2].strip())
                return number * 10000000

            number = float(cleaned)
            if number < 10000:
                return number * 100000

            return number
        except Exception:
            continue

    return None