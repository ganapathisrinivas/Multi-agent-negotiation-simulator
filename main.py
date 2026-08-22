from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from dataset_manager import load_dataset
from negotiation_runner import run_negotiation
from agents.orchestrator_agent import OrchestratorAgent
from agents.reasoning_engine import ReasoningEngine
from agents.counteroffer_evaluator import CounterofferEvaluator


app = FastAPI(
    title="Real Estate Negotiation Platform",
    description="AI Driven Multi-Agent Negotiation Training & Simulation Platform",
    version="1.0.0"
)


# =====================================================
# LOAD DATASET
# =====================================================

try:
    dataset = load_dataset("dataset_real.csv")

    if dataset is None:
        dataset = []

except Exception as error:
    print("Dataset loading error:", error)
    dataset = []


# =====================================================
# SCENARIOS
# =====================================================

SCENARIOS = {
    1: "Land / Plot",
    2: "Apartment / Flat",
    3: "Villa / Independent House"
}


# =====================================================
# PERSONALITIES
# =====================================================

PERSONALITIES = {
    1: "Aggressive",
    2: "Collaborative",
    3: "Risk-Averse"
}


# =====================================================
# REQUEST MODEL
# =====================================================

class NegotiationRequest(BaseModel):

    scenario: int

    buyer_personality: int

    seller_personality: int

    property_index: Optional[int] = 0

    max_rounds: int = 10


# =====================================================
# ROOT ENDPOINT
# =====================================================

@app.get("/")
def home():

    return {
        "message": "Real Estate Negotiation Platform API is running",
        "docs": "/docs"
    }


# =====================================================
# HEALTH ENDPOINT
# =====================================================

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
        "property_count": property_count
    }


# =====================================================
# GET SCENARIOS
# =====================================================

@app.get("/scenarios")
def get_scenarios():

    return {
        "scenarios": SCENARIOS
    }


# =====================================================
# GET PERSONALITIES
# =====================================================

@app.get("/personalities")
def get_personalities():

    return {
        "personalities": PERSONALITIES
    }


# =====================================================
# GET PROPERTIES
# =====================================================

@app.get("/properties")
def get_properties(
    scenario: Optional[int] = None,
    start: int = 0,
    limit: int = 1000
):

    # -------------------------------------------------
    # Check dataset
    # -------------------------------------------------

    if dataset is None:

        raise HTTPException(
            status_code=500,
            detail="Dataset is not loaded."
        )

    # -------------------------------------------------
    # Check Pandas DataFrame
    # -------------------------------------------------

    if hasattr(dataset, "empty"):

        if dataset.empty:

            raise HTTPException(
                status_code=500,
                detail="Dataset is not loaded."
            )

    else:

        if not dataset:

            raise HTTPException(
                status_code=500,
                detail="Dataset is not loaded."
            )

    # -------------------------------------------------
    # Validate start
    # -------------------------------------------------

    if start < 0:

        raise HTTPException(
            status_code=400,
            detail="Start cannot be negative."
        )

    # -------------------------------------------------
    # Validate limit
    # -------------------------------------------------

    if limit <= 0:

        raise HTTPException(
            status_code=400,
            detail="Limit must be greater than 0."
        )

    # -------------------------------------------------
    # Maximum 1000 properties per response
    # -------------------------------------------------

    if limit > 1000:

        limit = 1000

    # -------------------------------------------------
    # Calculate end position
    # -------------------------------------------------

    end = start + limit

    properties = []

    # -------------------------------------------------
    # Pandas DataFrame
    # -------------------------------------------------

    if hasattr(dataset, "iloc"):

        selected_data = dataset.iloc[
            start:end
        ].to_dict(
            orient="records"
        )

        for index, property_data in enumerate(
            selected_data,
            start=start
        ):

            properties.append({
                "index": index,
                "property": property_data
            })

    # -------------------------------------------------
    # List Dataset
    # -------------------------------------------------

    else:

        selected_data = dataset[
            start:end
        ]

        for index, property_data in enumerate(
            selected_data,
            start=start
        ):

            properties.append({
                "index": index,
                "property": property_data
            })

    # -------------------------------------------------
    # Return Properties
    # -------------------------------------------------

    return {
        "total_properties": len(dataset),
        "start": start,
        "limit": limit,
        "returned": len(properties),
        "properties": properties
    }


# =====================================================
# START NEGOTIATION
# =====================================================

@app.post("/negotiations")
def start_negotiation(
    request: NegotiationRequest
):

    # -------------------------------------------------
    # Validate scenario
    # -------------------------------------------------

    if request.scenario not in SCENARIOS:

        raise HTTPException(
            status_code=400,
            detail="Invalid scenario. Choose 1, 2 or 3."
        )

    # -------------------------------------------------
    # Validate buyer personality
    # -------------------------------------------------

    if request.buyer_personality not in PERSONALITIES:

        raise HTTPException(
            status_code=400,
            detail="Invalid buyer personality."
        )

    # -------------------------------------------------
    # Validate seller personality
    # -------------------------------------------------

    if request.seller_personality not in PERSONALITIES:

        raise HTTPException(
            status_code=400,
            detail="Invalid seller personality."
        )

    # -------------------------------------------------
    # Check dataset
    # -------------------------------------------------

    if dataset is None:

        raise HTTPException(
            status_code=500,
            detail="Dataset is not loaded."
        )

    if hasattr(dataset, "empty"):

        if dataset.empty:

            raise HTTPException(
                status_code=500,
                detail="Dataset is not loaded."
            )

    else:

        if not dataset:

            raise HTTPException(
                status_code=500,
                detail="Dataset is not loaded."
            )

    # -------------------------------------------------
    # Property selection
    # -------------------------------------------------

    property_index = request.property_index or 0

    # -------------------------------------------------
    # Validate property index
    # -------------------------------------------------

    if property_index < 0 or property_index >= len(dataset):

        raise HTTPException(
            status_code=400,
            detail="Invalid property index."
        )

    # -------------------------------------------------
    # Get selected property
    # -------------------------------------------------

    if hasattr(dataset, "iloc"):

        property_data = dataset.iloc[
            property_index
        ].to_dict()

    else:

        property_data = dataset[
            property_index
        ]

    # -------------------------------------------------
    # Get property price
    # -------------------------------------------------

    reference_price = extract_price(
        property_data
    )

    if reference_price is None:

        raise HTTPException(
            status_code=400,
            detail="Could not determine property price."
        )

    # =================================================
    # PERSONALITY CONFIGURATION
    # =================================================

    buyer_personality = PERSONALITIES[
        request.buyer_personality
    ]

    seller_personality = PERSONALITIES[
        request.seller_personality
    ]

    # =================================================
    # BUYER PRICE LIMITS
    # =================================================

    buyer_target = reference_price * 0.90

    buyer_minimum = reference_price * 0.70

    buyer_maximum = reference_price

    # =================================================
    # SELLER PRICE LIMITS
    # =================================================

    seller_target = reference_price * 0.95

    seller_minimum = reference_price * 0.75

    seller_maximum = reference_price

    # =================================================
    # CREATE BUYER EVALUATOR
    # =================================================

    buyer_evaluator = CounterofferEvaluator(
        role="buyer",
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    # =================================================
    # CREATE SELLER EVALUATOR
    # =================================================

    seller_evaluator = CounterofferEvaluator(
        role="seller",
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    # =================================================
    # CREATE BUYER REASONING ENGINE
    # =================================================

    buyer_reasoning = ReasoningEngine(
        role="Buyer Agent",
        persona=buyer_personality,
        goals=(
            "Buy the property at a reasonable price "
            "while staying within the buyer's budget."
        ),
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    # =================================================
    # CREATE SELLER REASONING ENGINE
    # =================================================

    seller_reasoning = ReasoningEngine(
        role="Seller Agent",
        persona=seller_personality,
        goals=(
            "Sell the property at a good price "
            "while remaining willing to negotiate."
        ),
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    # =================================================
    # CREATE ORCHESTRATOR
    # =================================================

    orchestrator = OrchestratorAgent(
        [
            "Buyer Agent",
            "Seller Agent"
        ]
    )

    # =================================================
    # RUN NEGOTIATION
    # =================================================

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

    # =================================================
    # RETURN BROWSER RESPONSE
    # =================================================

    return {
        "status": result.get("status"),
        "agreed_price": result.get("agreed_price"),
        "scenario": SCENARIOS[
            request.scenario
        ],
        "buyer_personality": buyer_personality,
        "seller_personality": seller_personality,
        "property": property_data,
        "negotiation_history": (
            orchestrator.get_history()
        ),
        "current_state": (
            orchestrator.get_state()
        )
    }


# =====================================================
# PRICE EXTRACTION
# =====================================================

def extract_price(property_data):

    if not isinstance(
        property_data,
        dict
    ):

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

            # -------------------------------------------------
            # Convert value to string
            # -------------------------------------------------

            value_string = str(
                value
            ).strip()

            # -------------------------------------------------
            # Remove currency symbols and commas
            # -------------------------------------------------

            cleaned = (
                value_string
                .replace(",", "")
                .replace("₹", "")
                .replace("Rs.", "")
                .replace("Rs", "")
                .strip()
            )

            lower_value = cleaned.lower()

            # =================================================
            # LAKHS
            # =================================================

            if "lakhs" in lower_value:

                number = float(
                    lower_value
                    .replace("lakhs", "")
                    .strip()
                )

                return number * 100000

            if "lakh" in lower_value:

                number = float(
                    lower_value
                    .replace("lakh", "")
                    .strip()
                )

                return number * 100000

            if lower_value.endswith("l"):

                number = float(
                    lower_value[:-1].strip()
                )

                return number * 100000

            # =================================================
            # CRORES
            # =================================================

            if "crores" in lower_value:

                number = float(
                    lower_value
                    .replace("crores", "")
                    .strip()
                )

                return number * 10000000

            if "crore" in lower_value:

                number = float(
                    lower_value
                    .replace("crore", "")
                    .strip()
                )

                return number * 10000000

            if lower_value.endswith("cr"):

                number = float(
                    lower_value[:-2].strip()
                )

                return number * 10000000

            # =================================================
            # NORMAL NUMERIC PRICE
            # =================================================

            number = float(
                cleaned
            )

            # Dataset may store price directly in lakhs
            if number < 10000:

                return number * 100000

            return number

        except Exception:

            continue

    return None