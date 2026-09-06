import re
from typing import Any, Dict, Optional

from agents.practice_store import PracticeNegotiationSession


def extract_offer_from_text(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    value_text = str(text).strip()
    patterns = [
        (r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore|cr)\b", 10000000),
        (r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh|lacs?|lac|[lL])\b", 100000),
        (r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", 1),
        (r"\b([\d,]{4,}(?:\.\d+)?)\b", 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, value_text, re.IGNORECASE)
        if not match:
            continue
        amount = float(match.group(1).replace(",", "")) * multiplier
        if multiplier == 1 and amount < 1000:
            amount *= 100000
        return amount
    return None


def extract_offer_from_message(text: Optional[str]) -> Optional[float]:
    return extract_offer_from_text(text)


def format_inr(amount: Optional[float]) -> str:
    if amount is None:
        return "N/A"
    amount = float(amount)
    if amount >= 10000000:
        return f"₹{amount / 10000000:.2f} Cr"
    return f"₹{amount / 100000:.2f} Lakhs"


def _round_price(amount: float) -> float:
    return float(round(float(amount) / 1000) * 1000)


def detect_human_intent(message: str) -> str:
    text = (message or "").lower().strip()
    if re.search(r"\b(i accept|i agree|agreed|deal(?: done)?|i will take it)\b", text):
        return "ACCEPT"
    if re.search(r"\b(i reject|no deal|walk away|i quit|cannot agree|too expensive|not interested|cancel)\b", text):
        return "REJECT"
    return "OFFER"


class PracticeAIAgent:
    def extract_offer_from_text(self, text: Optional[str]) -> Optional[float]:
        return extract_offer_from_text(text)

    def generate_initial_greeting(self, session: PracticeNegotiationSession) -> str:
        title = session.property.get("Property Title") or session.property.get("Name") or "this property"
        location = session.property.get("Location", "the area")
        price = format_inr(session.reference_price)
        if session.ai_role == "seller":
            return f"Hello! I am the seller of {title} in {location}. The asking price is {price}. What is your offer?"
        return f"Hello! I am interested in buying {title} in {location}. The listed price is {price}. What is your opening proposal?"

    def evaluate_and_respond(self, session: PracticeNegotiationSession, human_message: str, explicit_offer: Optional[float] = None) -> Dict[str, Any]:
        offer = explicit_offer if explicit_offer is not None else extract_offer_from_text(human_message)
        intent = detect_human_intent(human_message)
        if intent == "ACCEPT" and session.last_ai_offer is not None:
            return self._accept(session, session.last_ai_offer, "Human accepted the AI's latest offer.")
        if intent == "REJECT" and offer is None:
            return {"decision": "REJECT", "counter_offer": None, "message": "I understand. We will end this negotiation.", "reason": "Human indicated rejection."}
        if session.ai_role == "seller":
            return self._seller_response(session, offer)
        return self._buyer_response(session, offer)

    def _seller_response(self, session: PracticeNegotiationSession, offer: Optional[float]) -> Dict[str, Any]:
        reference = float(session.reference_price)
        last = float(session.last_ai_offer or reference)
        if offer is None:
            return {"decision": "COUNTER", "counter_offer": last, "message": f"Please share a specific offer. The property is listed at {format_inr(reference)}.", "reason": "No numerical offer was provided."}
        offer = float(offer)
        if offer >= session.target_price:
            return self._accept(session, offer, "The offer meets the seller's target price.")
        if session.ai_personality == "aggressive" and offer < reference * 0.70:
            return {"decision": "REJECT", "counter_offer": None, "message": f"Your offer of {format_inr(offer)} is too far below market value.", "reason": "Aggressive seller rejected a low offer."}
        concession = {"aggressive": 0.15, "risk_averse": 0.30, "collaborative": 0.45}.get(session.ai_personality, 0.45)
        counter = _round_price(max(session.minimum_price, min(last - (last - offer) * concession, last)))
        return {"decision": "COUNTER", "counter_offer": counter, "message": f"Thank you for your offer of {format_inr(offer)}. I can reduce the price to {format_inr(counter)}.", "reason": f"Seller used a {int(concession * 100)}% concession step."}

    def _buyer_response(self, session: PracticeNegotiationSession, offer: Optional[float]) -> Dict[str, Any]:
        reference = float(session.reference_price)
        last = float(session.last_ai_offer or session.minimum_price)
        if offer is None:
            return {"decision": "COUNTER", "counter_offer": last, "message": f"Please share a specific selling price. I am considering {format_inr(last)}.", "reason": "No numerical offer was provided."}
        offer = float(offer)
        if offer <= session.target_price:
            return self._accept(session, offer, "The seller's price meets the buyer's target.")
        if session.ai_personality == "aggressive" and offer > reference * 1.25:
            return {"decision": "REJECT", "counter_offer": None, "message": f"The price of {format_inr(offer)} is above my limit.", "reason": "Aggressive buyer rejected an excessive price."}
        concession = {"aggressive": 0.15, "risk_averse": 0.30, "collaborative": 0.45}.get(session.ai_personality, 0.45)
        counter = _round_price(min(session.maximum_price, max(last, last + (offer - last) * concession)))
        return {"decision": "COUNTER", "counter_offer": counter, "message": f"I can improve my offer to {format_inr(counter)}.", "reason": f"Buyer used a {int(concession * 100)}% concession step."}

    def _accept(self, session: PracticeNegotiationSession, amount: float, reason: str) -> Dict[str, Any]:
        return {"decision": "ACCEPT", "counter_offer": float(amount), "message": f"Agreed. We have a deal at {format_inr(amount)}.", "reason": reason}
