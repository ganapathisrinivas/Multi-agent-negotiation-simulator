import os
import re
import random
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from agents.practice_store import PracticeNegotiationSession


# ============================================================
# PRICE HELPERS
# ============================================================

def extract_offer_from_text(text: Optional[str]) -> Optional[float]:
    """Extract INR offers written in lakhs, crores, or rupees."""
    if text is None:
        return None

    text = str(text).strip()

    patterns = [
        (r"₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh|[lL])\b", 100000),
        (r"₹?\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore|cr)\b", 10000000),
        (r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", 1),
        (r"(?:offer|price|at|pay|for)?\s*[:\-]?\s*₹?\s*([\d,]{4,}(?:\.\d+)?)", 1),
        (r"\b([\d,]{4,}(?:\.\d+)?)\b", 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = float(match.group(1).replace(",", ""))

            if multiplier == 1 and value < 1000:
                value *= 100000

            return value * multiplier

    return None


def format_inr(amount: Optional[float]) -> str:
    """Display an amount in Indian Lakhs/Crores."""
    if amount is None:
        return "N/A"

    amount = float(amount)

    return (
        f"₹{amount / 10000000:.2f} Cr"
        if amount >= 10000000
        else f"₹{amount / 100000:.2f} Lakhs"
    )


def round_price(price: float) -> float:
    """Round prices to nearest ₹1,000."""
    return float(round(float(price) / 1000) * 1000)


def detect_human_intent(message: str) -> str:
    """Return ACCEPT, REJECT, or OFFER."""
    text = message.lower().strip()

    accepts = [
        r"\bi accept\b",
        r"\bwe accept\b",
        r"\bi agree\b",
        r"\bagreed\b",
        r"\bdeal\b",
        r"\bit'?s a deal\b",
        r"\bi accept the offer\b",
        r"\bi will take it\b",
        r"\bdeal done\b",
        r"\bwe have a deal\b"
    ]

    rejects = [
        r"\bi reject\b",
        r"\bno deal\b",
        r"\bwalk away\b",
        r"\bi quit\b",
        r"\bcannot agree\b",
        r"\btoo expensive\b",
        r"\bnot interested\b",
        r"\bcancel\b"
    ]

    if any(re.search(p, text) for p in accepts):
        return "ACCEPT"

    if any(re.search(p, text) for p in rejects):
        return "REJECT"

    return "OFFER"


# ============================================================
# PRACTICE AI AGENT
# ============================================================

class PracticeAIAgent:
    """AI agent for Human-vs-AI real-estate practice."""

    def __init__(self):
        load_dotenv()

        self.client = None

        self.model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        )

        api_key = os.getenv("GEMINI_API_KEY")

        if api_key:
            try:
                from google import genai

                self.client = genai.Client(
                    api_key=api_key
                )

            except Exception as error:
                print(
                    f"[PracticeAgent] "
                    f"Gemini initialization skipped: {error}"
                )

    # ========================================================
    # INITIAL GREETING
    # ========================================================

    def generate_initial_greeting(
        self,
        session: PracticeNegotiationSession
    ) -> str:

        title = (
            session.property.get("Property Title")
            or session.property.get("Name")
            or "this property"
        )

        location = session.property.get(
            "Location",
            "Prime Location"
        )

        price = format_inr(
            session.reference_price
        )

        personality = (
            session.ai_personality
            .lower()
            .replace("-", "_")
        )

        if session.ai_role == "seller":

            if personality == "aggressive":
                return (
                    f"Welcome. I am the seller for {title} "
                    f"in {location}, listed at {price}. "
                    "This property is in high demand. "
                    "What is your opening offer?"
                )

            if personality == "risk_averse":
                return (
                    f"Hello! I represent the seller of {title} "
                    f"at {location}. The verified price is {price}. "
                    "I will consider serious and well-structured offers."
                )

            return (
                f"Hello and welcome! I am the seller of {title} "
                f"in {location}. The asking price is {price}. "
                "I am happy to work toward a fair win-win deal. "
                "What is your offer?"
            )

        if personality == "aggressive":
            return (
                f"Hello. I am a serious buyer evaluating {title} "
                f"in {location}. I reviewed the reference price "
                f"of {price}. What is your best asking price?"
            )

        if personality == "risk_averse":
            return (
                f"Greetings. I am interested in {title} "
                f"in {location}. I have reviewed the listed "
                f"price of {price}. Please share your opening "
                "price proposal."
            )

        return (
            f"Hello! I am interested in buying {title} "
            f"in {location}. I saw the listed price is {price}. "
            "I would like to reach a mutually beneficial agreement. "
            "What is your opening proposal?"
        )

    # ========================================================
    # MAIN EVALUATION
    # ========================================================

    def evaluate_and_respond(
        self,
        session: PracticeNegotiationSession,
        human_message: str,
        explicit_offer: Optional[float] = None
    ) -> Dict[str, Any]:

        personality = (
            session.ai_personality
            .lower()
            .replace("-", "_")
        )

        intent = detect_human_intent(
            human_message
        )

        offer = (
            explicit_offer
            if explicit_offer is not None
            else extract_offer_from_text(human_message)
        )

        # Human accepts the AI's previous offer.
        if (
            intent == "ACCEPT"
            and session.last_ai_offer is not None
        ):

            agreed = session.last_ai_offer

            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(
                    session,
                    agreed,
                    True
                ),
                "reason": (
                    f"Human accepted "
                    f"{format_inr(agreed)}."
                )
            }

        # Human explicitly rejects without giving another offer.
        if intent == "REJECT" and offer is None:

            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": self._generate_rejection_message(
                    session,
                    "Human participant rejected the negotiation."
                ),
                "reason": "Human indicated rejection."
            }

        # Check whether the negotiation is actually stuck.
        deadlock = self._detect_deadlock(
            session,
            offer
        )

        if deadlock:
            return deadlock

        if session.ai_role == "seller":

            return self._evaluate_as_seller(
                session,
                offer,
                personality
            )

        return self._evaluate_as_buyer(
            session,
            offer,
            personality
        )

    # ========================================================
    # DEADLOCK DETECTION
    # ========================================================

    def _detect_deadlock(
        self,
        session: PracticeNegotiationSession,
        human_offer: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a genuine negotiation deadlock.

        Deadlock rules:

        1. A single repeated offer is NOT a deadlock.
        2. Two repeated offers are NOT a deadlock.
        3. AI repeating alone is NOT a deadlock.
        4. Human repeating alone is NOT a deadlock.
        5. A small price gap is NOT a deadlock.
        6. BOTH human and AI must show no meaningful price movement.
        7. The lack of movement must continue for 3 consecutive
           stalled transitions.
        """

        if human_offer is None:
            return None

        try:
            current_human = float(
                human_offer
            )

        except (TypeError, ValueError):
            return None

        history = session.history or []

        # ====================================================
        # COLLECT HUMAN OFFERS FROM HISTORY
        # ====================================================

        human_offers = []

        for item in history:

            if item.get("sender") == (
                f"human_{session.human_role}"
            ):

                value = item.get("offer")

                if value is not None:

                    try:
                        human_offers.append(
                            float(value)
                        )

                    except (TypeError, ValueError):
                        pass

        # IMPORTANT:
        #
        # The current human offer may already exist inside
        # session.history.
        #
        # Therefore, do NOT blindly append it.
        #
        # This prevents one repeated offer from being counted
        # twice and incorrectly triggering deadlock.

        if (
            not human_offers
            or human_offers[-1] != current_human
        ):

            human_offers.append(
                current_human
            )

        # ====================================================
        # COLLECT AI OFFERS FROM HISTORY
        # ====================================================

        ai_offers = []

        for item in history:

            if item.get("sender") == (
                f"ai_{session.ai_role}"
            ):

                value = item.get("offer")

                if value is not None:

                    try:
                        ai_offers.append(
                            float(value)
                        )

                    except (TypeError, ValueError):
                        pass

        # Add current AI offer only if it is not already
        # present as the latest AI history entry.

        if session.last_ai_offer is not None:

            try:

                current_ai = float(
                    session.last_ai_offer
                )

                if (
                    not ai_offers
                    or ai_offers[-1] != current_ai
                ):

                    ai_offers.append(
                        current_ai
                    )

            except (TypeError, ValueError):
                pass

        # ====================================================
        # HUMAN STALLED FOR 3 CONSECUTIVE TRANSITIONS
        # ====================================================

        human_stalled_rounds = 0

        if len(human_offers) >= 2:

            for index in range(
                len(human_offers) - 1,
                0,
                -1
            ):

                change = abs(
                    human_offers[index]
                    - human_offers[index - 1]
                )

                # ₹1,000 or less means no meaningful movement.
                if change <= 1000:

                    human_stalled_rounds += 1

                else:

                    # Once meaningful movement is found,
                    # older rounds do not matter.
                    break

        # ====================================================
        # AI STALLED FOR 3 CONSECUTIVE TRANSITIONS
        # ====================================================

        ai_stalled_rounds = 0

        if len(ai_offers) >= 2:

            for index in range(
                len(ai_offers) - 1,
                0,
                -1
            ):

                change = abs(
                    ai_offers[index]
                    - ai_offers[index - 1]
                )

                if change <= 1000:

                    ai_stalled_rounds += 1

                else:

                    break

        # ====================================================
        # FINAL DEADLOCK DECISION
        # ====================================================

        # BOTH sides must be stalled for at least
        # 3 consecutive transitions.
        #
        # Example:
        #
        # Human:
        # ₹28.50L
        # → ₹28.50L
        #
        # = 1 stalled transition
        # = NOT deadlock
        #
        # Human:
        # ₹28.50L
        # → ₹28.50L
        # → ₹28.50L
        #
        # = 2 stalled transitions
        # = NOT deadlock
        #
        # Human:
        # ₹28.50L
        # → ₹28.50L
        # → ₹28.50L
        # → ₹28.50L
        #
        # = 3 stalled transitions
        #
        # But AI must ALSO have 3 stalled transitions.

        if (
            human_stalled_rounds >= 3
            and ai_stalled_rounds >= 3
        ):

            return self._create_deadlock_response(
                session,
                "Both the human participant and AI "
                "have shown almost no price movement "
                "for three consecutive rounds."
            )

        return None

    # ========================================================
    # DEADLOCK RESPONSE
    # ========================================================

    def _create_deadlock_response(
        self,
        session: PracticeNegotiationSession,
        reason: str
    ) -> Dict[str, Any]:

        return {
            "decision": "DEADLOCK",
            "counter_offer": None,
            "message": (
                "DEADLOCK DETECTED\n\n"
                "The negotiation appears to have stopped "
                "making meaningful progress. Both parties "
                "should review their offer strategy or "
                "restart the negotiation."
            ),
            "reason": reason
        }

    # ========================================================
    # AI SELLER
    # ========================================================

    def _evaluate_as_seller(
        self,
        session: PracticeNegotiationSession,
        offer: Optional[float],
        personality: str
    ) -> Dict[str, Any]:

        reference = float(
            session.reference_price
        )

        target = float(
            session.target_price
        )

        minimum = float(
            session.minimum_price
        )

        last = (
            float(session.last_ai_offer)
            if session.last_ai_offer is not None
            else reference
        )

        if offer is None:

            return {
                "decision": "COUNTER",
                "counter_offer": last,
                "message": (
                    "I need a specific price offer to continue. "
                    f"The property is listed at "
                    f"{format_inr(reference)}."
                ),
                "reason": (
                    "No numerical offer was provided."
                )
            }

        offer = float(offer)

        # Offer meets seller's current level.
        if offer >= last:

            return self._accept_result(
                session,
                offer
            )

        # Offer meets seller target.
        if offer >= target:

            return self._accept_result(
                session,
                offer
            )

        # Aggressive seller rejects extreme lowball offers.
        if (
            personality == "aggressive"
            and offer < reference * 0.70
        ):

            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": (
                    f"Your offer of {format_inr(offer)} "
                    "is far below the property's market "
                    "value and is unacceptable."
                ),
                "reason": (
                    "Aggressive seller rejected a "
                    "very low offer."
                )
            }

        rates = {
            "aggressive": (
                0.15,
                max(
                    minimum,
                    reference * 0.88
                )
            ),
            "risk_averse": (
                0.30,
                max(
                    minimum,
                    reference * 0.80
                )
            ),
            "collaborative": (
                0.45,
                minimum
            )
        }

        concession, floor = rates.get(
            personality,
            rates["collaborative"]
        )

        new_counter = (
            last
            - (last - offer) * concession
        )

        new_counter = round_price(
            max(
                floor,
                min(
                    new_counter,
                    last
                )
            )
        )

        # Collaborative personality can close a very small gap.
        if (
            (
                personality == "collaborative"
                and abs(
                    new_counter - offer
                ) <= reference * 0.01
            )
            or new_counter <= offer
        ):

            return self._accept_result(
                session,
                offer
            )

        return {
            "decision": "COUNTER",
            "counter_offer": new_counter,
            "message": self._generate_counter_message(
                session,
                offer,
                new_counter,
                personality,
                "seller"
            ),
            "reason": (
                f"Seller countered at "
                f"{format_inr(new_counter)} "
                f"using a {int(concession * 100)}% "
                "concession step."
            )
        }

    # ========================================================
    # AI BUYER
    # ========================================================

    def _evaluate_as_buyer(
        self,
        session: PracticeNegotiationSession,
        offer: Optional[float],
        personality: str
    ) -> Dict[str, Any]:

        reference = float(
            session.reference_price
        )

        target = float(
            session.target_price
        )

        maximum = float(
            session.maximum_price
        )

        last = (
            float(session.last_ai_offer)
            if session.last_ai_offer is not None
            else float(session.minimum_price)
        )

        if offer is None:

            return {
                "decision": "COUNTER",
                "counter_offer": last,
                "message": (
                    "I need a concrete selling price "
                    "to continue. The reference price is "
                    f"{format_inr(reference)}."
                ),
                "reason": (
                    "No numerical offer was provided."
                )
            }

        offer = float(offer)

        # Seller price meets buyer's current offer.
        if offer <= last:

            return self._accept_result(
                session,
                offer
            )

        # Seller price meets buyer target.
        if offer <= target:

            return self._accept_result(
                session,
                offer
            )

        # Aggressive buyer rejects an excessive price.
        if (
            personality == "aggressive"
            and offer > reference * 1.25
        ):

            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": (
                    f"Your price of {format_inr(offer)} "
                    "is excessively above the market "
                    "reference. I cannot proceed."
                ),
                "reason": (
                    "Aggressive buyer rejected "
                    "excessive price."
                )
            }

        rates = {
            "aggressive": (
                0.15,
                min(
                    maximum,
                    reference * 0.90
                )
            ),
            "risk_averse": (
                0.30,
                min(
                    maximum,
                    reference * 0.95
                )
            ),
            "collaborative": (
                0.45,
                maximum
            )
        }

        concession, ceiling = rates.get(
            personality,
            rates["collaborative"]
        )

        new_counter = (
            last
            + (offer - last) * concession
        )

        new_counter = round_price(
            max(
                last,
                min(
                    new_counter,
                    ceiling
                )
            )
        )

        if (
            (
                personality == "collaborative"
                and abs(
                    new_counter - offer
                ) <= reference * 0.01
            )
            or new_counter >= offer
        ):

            return self._accept_result(
                session,
                offer
            )

        return {
            "decision": "COUNTER",
            "counter_offer": new_counter,
            "message": self._generate_counter_message(
                session,
                offer,
                new_counter,
                personality,
                "buyer"
            ),
            "reason": (
                f"Buyer countered at "
                f"{format_inr(new_counter)} "
                f"using a {int(concession * 100)}% "
                "concession step."
            )
        }

    # ========================================================
    # ACCEPTANCE / REJECTION
    # ========================================================

    def _accept_result(
        self,
        session: PracticeNegotiationSession,
        price: float
    ) -> Dict[str, Any]:

        return {
            "decision": "ACCEPT",
            "counter_offer": price,
            "message": self._generate_acceptance_message(
                session,
                price
            ),
            "reason": (
                f"Offer of {format_inr(price)} "
                "is acceptable."
            )
        }

    def _generate_acceptance_message(
        self,
        session: PracticeNegotiationSession,
        price: float,
        by_human: bool = False
    ) -> str:

        title = (
            session.property.get("Property Title")
            or session.property.get("Name")
            or "the property"
        )

        if by_human:

            return (
                f"Fantastic! We have reached an "
                f"agreement on {title} at "
                f"{format_inr(price)}. "
                "The deal is officially finalized!"
            )

        return (
            "DECISION: ACCEPT\n\n"
            f"I accept your offer of "
            f"{format_inr(price)} for {title}. "
            "We have reached a successful agreement."
        )

    def _generate_rejection_message(
        self,
        session: PracticeNegotiationSession,
        reason: str
    ) -> str:

        return (
            "DECISION: REJECT\n\n"
            "We were unable to reach an agreement. "
            "The negotiation is concluded. "
            f"Reason: {reason}"
        )

    # ========================================================
    # COUNTER MESSAGE
    # ========================================================

    def _generate_counter_message(
        self,
        session: PracticeNegotiationSession,
        human_offer: float,
        counter_offer: float,
        personality: str,
        role: str
    ) -> str:

        if self.client:

            result = self._try_gemini_response(
                session,
                human_offer,
                counter_offer,
                personality,
                role
            )

            if result:
                return result

        human = format_inr(
            human_offer
        )

        counter = format_inr(
            counter_offer
        )

        if role == "seller":

            templates = {

                "aggressive": [
                    (
                        f"Your offer of {human} is too low. "
                        f"My best price right now is {counter}."
                    ),
                    (
                        f"I cannot accept {human}. "
                        f"My revised price is {counter}."
                    )
                ],

                "risk_averse": [
                    (
                        f"Thank you for {human}. "
                        "Based on the property valuation, "
                        f"I can counter at {counter}."
                    ),
                    (
                        "I appreciate your proposal. "
                        "To maintain a fair valuation, "
                        f"my counter is {counter}."
                    )
                ],

                "collaborative": [
                    (
                        f"Thank you for your offer of {human}. "
                        f"I can come down to {counter} "
                        "to help us reach a deal."
                    ),
                    (
                        f"I appreciate your proposal. "
                        f"Let's move closer to an agreement "
                        f"at {counter}."
                    )
                ]
            }

        else:

            templates = {

                "aggressive": [
                    (
                        f"Your demand of {human} is too high. "
                        f"I can only offer {counter}."
                    ),
                    (
                        f"{human} is above my valuation. "
                        f"My strict counter is {counter}."
                    )
                ],

                "risk_averse": [
                    (
                        f"I reviewed {human}. "
                        "To stay within a prudent budget, "
                        f"I can offer {counter}."
                    ),
                    (
                        "To avoid overpaying, "
                        f"my updated offer is {counter}."
                    )
                ],

                "collaborative": [
                    (
                        f"Thank you for your response of {human}. "
                        f"I can raise my offer to {counter}."
                    ),
                    (
                        f"I appreciate your flexibility. "
                        f"I can increase my offer to {counter}."
                    )
                ]
            }

        return random.choice(
            templates.get(
                personality,
                templates["collaborative"]
            )
        )

    # ========================================================
    # GEMINI RESPONSE
    # ========================================================

    def _try_gemini_response(
        self,
        session: PracticeNegotiationSession,
        human_offer: float,
        counter_offer: float,
        personality: str,
        role: str
    ) -> Optional[str]:

        try:

            prompt = f"""
You are an AI {role} negotiating real estate with a human.

Property: {session.property.get("Property Title", "Real Estate Property")}
Location: {session.property.get("Location", "Location")}
Reference Price: {format_inr(session.reference_price)}
Personality: {personality}
Human Offer: {format_inr(human_offer)}
Exact Counter Price: {format_inr(counter_offer)}

Generate a natural professional 2-3 sentence response.

Rules:
- Mention the exact counter price: {format_inr(counter_offer)}
- Do not invent other numbers.
- Aggressive = firm and assertive.
- Collaborative = warm and flexible.
- Risk-averse = careful and analytical.
- Output only the negotiation message.
"""

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            if (
                response
                and getattr(
                    response,
                    "text",
                    None
                )
            ):

                return (
                    response.text
                    .strip()
                    .replace("```", "")
                )

        except Exception as error:

            print(
                f"[PracticeAgent] "
                f"Gemini generation error: {error}"
            )

        return None