import os
import re
import random
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from agents.practice_store import PracticeNegotiationSession


def extract_offer_from_text(text: Optional[str]) -> Optional[float]:
    """
    Extract an offer amount in INR from a user text message.
    Supports formats like:
        - 2400000 / 2,400,000 / ₹2400000
        - 24 lakhs / 24.5 lakhs / ₹24.5 lakh / 24L
        - 2.5 crore / 2.5 cr / ₹2.5 crore
    """
    if text is None:
        return None

    text = str(text).strip()

    # Lakhs format: 24 lakhs, 24.5 lakh, ₹24L
    match = re.search(r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh|[lL])\b', text, re.IGNORECASE)
    if match:
        val = float(match.group(1).replace(',', ''))
        return val * 100000

    # Crores format: 2.5 crore, 2.5cr
    match = re.search(r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore|cr)\b', text, re.IGNORECASE)
    if match:
        val = float(match.group(1).replace(',', ''))
        return val * 10000000

    # Plain rupees with ₹ or INR or Rs.: ₹2400000
    match = re.search(r'(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
    if match:
        val = float(match.group(1).replace(',', ''))
        if val < 1000:
            return val * 100000
        return val

    # Direct number in offer statement: "I offer 2400000", "offer is 2400000", "at 2500000"
    match = re.search(r'(?:offer|price|at|pay|for|budget)?\s*[:\-]?\s*₹?\s*([\d,]{4,}(?:\.\d+)?)', text, re.IGNORECASE)
    if match:
        val = float(match.group(1).replace(',', ''))
        return val

    # Generic number search
    match = re.search(r'\b([\d,]{4,}(?:\.\d+)?)\b', text)
    if match:
        val = float(match.group(1).replace(',', ''))
        return val

    return None


def format_inr(amount: Optional[float]) -> str:
    """Format an amount in INR Lakhs / Crores string."""
    if amount is None:
        return "N/A"
    amount = float(amount)
    if amount >= 10000000:
        return f"₹{amount / 10000000:.2f} Cr"
    return f"₹{amount / 100000:.2f} Lakhs"


def round_price(price: float) -> float:
    """Round price to nearest 1,000 precision."""
    return float(round(float(price) / 1000) * 1000)


def detect_human_intent(message: str) -> str:
    """
    Detect human message intent: 'ACCEPT', 'REJECT', or 'OFFER' / 'NORMAL'
    """
    lower = message.lower().strip()
    
    # Check for acceptance phrases
    accept_patterns = [
        r'\bi accept\b', r'\bwe accept\b', r'\bi agree\b', r'\bagreed\b',
        r'\bdeal\b', r'\bit\'?s a deal\b', r'\bi accept the offer\b',
        r'\bi will take it\b', r'\bdeal done\b', r'\bwe have a deal\b'
    ]
    for pattern in accept_patterns:
        if re.search(pattern, lower):
            return "ACCEPT"

    # Check for rejection / walk away phrases
    reject_patterns = [
        r'\bi reject\b', r'\bno deal\b', r'\bwalk away\b', r'\bi quit\b',
        r'\bcannot agree\b', r'\btoo expensive\b', r'\bnot interested\b',
        r'\bcancel\b'
    ]
    for pattern in reject_patterns:
        if re.search(pattern, lower):
            return "REJECT"

    return "OFFER"


class PracticeAIAgent:
    """
    Intelligent AI Agent for Human-vs-AI Practice Mode.
    Can act as either AI Seller or AI Buyer.
    Supports Aggressive, Collaborative, and Risk-Averse personalities.
    Integrates with Gemini LLM when available, and uses deterministic reasoning when offline.
    """

    def __init__(self):
        load_dotenv()
        self.client = None
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[PracticeAgent] Gemini initialization skipped: {e}")
                self.client = None

    def generate_initial_greeting(self, session: PracticeNegotiationSession) -> str:
        """
        Generate a welcoming, contextual initial message from the AI when practice starts.
        """
        prop_title = session.property.get("Property Title") or session.property.get("Name") or "this property"
        loc = session.property.get("Location", "Prime Location")
        formatted_price = format_inr(session.reference_price)
        personality = session.ai_personality.lower().replace("-", "_")

        if session.ai_role == "seller":
            if personality == "aggressive":
                return (
                    f"Welcome. I am the seller for {prop_title} in {loc}, listed at {formatted_price}. "
                    f"This property is in high demand with strong market interest. What is your opening offer?"
                )
            elif personality == "risk_averse":
                return (
                    f"Hello! I am representing the seller for {prop_title} at {loc}. "
                    f"The property is verified and priced at {formatted_price} reflecting fair market conditions. "
                    f"I am happy to consider serious and well-structured offers."
                )
            else:  # collaborative
                return (
                    f"Hello and welcome! I am the seller of {prop_title} in {loc}. "
                    f"The asking price is {formatted_price}. I'm eager to work together with you to find a fair, win-win deal. "
                    f"What offer would you like to put forward?"
                )
        else:  # AI is Buyer
            if personality == "aggressive":
                return (
                    f"Hello. I am a serious buyer evaluating {prop_title} in {loc}. "
                    f"I have reviewed the {formatted_price} reference price. As an investor, I only close deals that make clear financial sense. "
                    f"What is your best asking price?"
                )
            elif personality == "risk_averse":
                return (
                    f"Greetings. I am interested in purchasing {prop_title} in {loc}. "
                    f"I have studied the property details and the listed price of {formatted_price}. "
                    f"I prioritize a transparent and fair transaction. Please share your opening price proposal."
                )
            else:  # collaborative
                return (
                    f"Hello! I am very interested in buying {prop_title} located at {loc}. "
                    f"I saw the listed price is {formatted_price}. I would love to discuss a mutually beneficial agreement with you. "
                    f"Please let me know your opening price or proposal."
                )

    def evaluate_and_respond(
        self,
        session: PracticeNegotiationSession,
        human_message: str,
        explicit_offer: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Main decision-making and response generator for a human turn.
        
        Returns:
            {
                "decision": "ACCEPT" | "REJECT" | "COUNTER",
                "counter_offer": float or None,
                "message": "...",
                "reason": "..."
            }
        """
        personality = session.ai_personality.lower().replace("-", "_")
        human_intent = detect_human_intent(human_message)
        
        # 1. Determine the offer amount from human
        human_offer = explicit_offer if explicit_offer is not None else extract_offer_from_text(human_message)

        # 2. Check if human explicitly accepted the AI's previous offer
        if human_intent == "ACCEPT" and session.last_ai_offer is not None:
            agreed = session.last_ai_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed, by_human=True),
                "reason": f"Human participant accepted the AI's counter-offer of {format_inr(agreed)}."
            }

        # 3. Check if human explicitly rejected / quit
        if human_intent == "REJECT" and human_offer is None:
            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": self._generate_rejection_message(session, "Human participant expressed rejection/walked away."),
                "reason": "Human participant indicated they wish to reject or discontinue the negotiation."
            }

        # 4. If human provided an offer, evaluate based on AI Role & Personality
        if session.ai_role == "seller":
            return self._evaluate_as_ai_seller(session, human_offer, human_message, personality)
        else:
            return self._evaluate_as_ai_buyer(session, human_offer, human_message, personality)

    # =========================================================================
    # AI SELLER LOGIC
    # =========================================================================
    def _evaluate_as_ai_seller(
        self,
        session: PracticeNegotiationSession,
        human_offer: Optional[float],
        human_message: str,
        personality: str
    ) -> Dict[str, Any]:
        ref_price = session.reference_price
        target_price = session.target_price
        min_price = session.minimum_price
        last_ai_offer = session.last_ai_offer or ref_price

        # If human gave no numeric offer, ask for one
        if human_offer is None:
            msg = (
                f"I hear you, but to proceed I need a specific price offer in numbers or lakhs. "
                f"The property is listed at {format_inr(ref_price)}. What amount are you proposing?"
            )
            return {
                "decision": "COUNTER",
                "counter_offer": last_ai_offer,
                "message": msg,
                "reason": "Human provided commentary without a specific offer amount."
            }

        human_offer = float(human_offer)

        # Condition 1: Exact match with last AI counter or higher than last counter
        if last_ai_offer is not None and human_offer >= last_ai_offer:
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": f"Buyer offered {format_inr(human_offer)}, which meets or exceeds the seller's asking price of {format_inr(last_ai_offer)}."
            }

        # Condition 2: Check if offer meets seller's target price
        if human_offer >= target_price:
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": f"Buyer's offer of {format_inr(human_offer)} satisfies seller target price ({format_inr(target_price)})."
            }

        # Condition 3: Check personality-specific rejection rules (e.g. extreme lowballs)
        if personality == "aggressive" and human_offer < (ref_price * 0.70):
            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": (
                    f"Your offer of {format_inr(human_offer)} is far below market value and unacceptable for this property. "
                    f"As an aggressive seller, I cannot entertain deals at this level."
                ),
                "reason": f"Aggressive seller rejected lowball offer below 70% of reference price ({format_inr(ref_price)})."
            }

        # Condition 4: Personality-driven counter offer
        # Step concession rate towards human offer
        if personality == "aggressive":
            concession_rate = 0.15
            floor_price = max(min_price, ref_price * 0.88)
        elif personality == "risk_averse":
            concession_rate = 0.30
            floor_price = max(min_price, ref_price * 0.80)
        else:  # collaborative
            concession_rate = 0.45
            floor_price = min_price

        # Calculate new counter price
        price_gap = last_ai_offer - human_offer
        if price_gap > 0:
            reduction = price_gap * concession_rate
            new_counter = last_ai_offer - reduction
        else:
            new_counter = human_offer

        # Ensure seller does not drop below floor price or previous offer
        new_counter = max(new_counter, floor_price)
        new_counter = min(new_counter, last_ai_offer)
        new_counter = round_price(new_counter)

        # If counter reached buyer's offer or is extremely close (< 1% gap) in collaborative mode
        if (personality == "collaborative" and abs(new_counter - human_offer) <= (ref_price * 0.01)) or (new_counter <= human_offer):
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": "Collaborative seller agreed to bridge the final small gap to close the transaction."
            }

        # Format message
        ai_msg = self._generate_counter_message(
            session=session,
            decision="COUNTER",
            human_offer=human_offer,
            counter_offer=new_counter,
            personality=personality,
            role="seller"
        )

        return {
            "decision": "COUNTER",
            "counter_offer": new_counter,
            "message": ai_msg,
            "reason": f"Seller countered at {format_inr(new_counter)} with a {int(concession_rate*100)}% concession step ({personality} personality)."
        }

    # =========================================================================
    # AI BUYER LOGIC
    # =========================================================================
    def _evaluate_as_ai_buyer(
        self,
        session: PracticeNegotiationSession,
        human_offer: Optional[float],
        human_message: str,
        personality: str
    ) -> Dict[str, Any]:
        ref_price = session.reference_price
        target_price = session.target_price
        max_budget = session.maximum_price
        last_ai_offer = session.last_ai_offer or session.minimum_price

        if human_offer is None:
            msg = (
                f"Thank you for your message. As a prospective buyer, I need a concrete price figure for this property. "
                f"The reference price is {format_inr(ref_price)}. What price are you offering to sell at?"
            )
            return {
                "decision": "COUNTER",
                "counter_offer": last_ai_offer,
                "message": msg,
                "reason": "Human seller provided response without a clear numerical price."
            }

        human_offer = float(human_offer)

        # Condition 1: Exact match with last AI counter or lower
        if last_ai_offer is not None and human_offer <= last_ai_offer:
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": f"Seller agreed to a price of {format_inr(human_offer)}, which is within buyer's target."
            }

        # Condition 2: Check if seller offer is within buyer target
        if human_offer <= target_price:
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": f"Seller's asking price of {format_inr(human_offer)} is within buyer's target threshold ({format_inr(target_price)})."
            }

        # Condition 3: Check personality rejection rules (e.g. seller demands way above budget)
        if personality == "aggressive" and human_offer > (ref_price * 1.25):
            return {
                "decision": "REJECT",
                "counter_offer": None,
                "message": (
                    f"Your demanded price of {format_inr(human_offer)} is excessively inflated above market reality. "
                    f"I cannot proceed with this negotiation."
                ),
                "reason": f"Aggressive buyer rejected asking price exceeding 125% of reference price ({format_inr(ref_price)})."
            }

        # Condition 4: Personality-driven counter offer
        if personality == "aggressive":
            concession_rate = 0.15
            ceiling_price = min(max_budget, ref_price * 0.90)
        elif personality == "risk_averse":
            concession_rate = 0.30
            ceiling_price = min(max_budget, ref_price * 0.95)
        else:  # collaborative
            concession_rate = 0.45
            ceiling_price = max_budget

        # Calculate new counter price upward towards seller
        price_gap = human_offer - last_ai_offer
        if price_gap > 0:
            increase = price_gap * concession_rate
            new_counter = last_ai_offer + increase
        else:
            new_counter = human_offer

        # Ensure buyer does not exceed ceiling price or drop below previous offer
        new_counter = min(new_counter, ceiling_price)
        new_counter = max(new_counter, last_ai_offer)
        new_counter = round_price(new_counter)

        # If counter reached seller's offer or is within 1% gap in collaborative mode
        if (personality == "collaborative" and abs(new_counter - human_offer) <= (ref_price * 0.01)) or (new_counter >= human_offer):
            agreed = human_offer
            return {
                "decision": "ACCEPT",
                "counter_offer": agreed,
                "message": self._generate_acceptance_message(session, agreed),
                "reason": "Collaborative buyer agreed to meet the seller's price to complete the deal."
            }

        # Format message
        ai_msg = self._generate_counter_message(
            session=session,
            decision="COUNTER",
            human_offer=human_offer,
            counter_offer=new_counter,
            personality=personality,
            role="buyer"
        )

        return {
            "decision": "COUNTER",
            "counter_offer": new_counter,
            "message": ai_msg,
            "reason": f"Buyer countered at {format_inr(new_counter)} with a {int(concession_rate*100)}% concession step ({personality} personality)."
        }

    # =========================================================================
    # MESSAGE GENERATION (DETERMINISTIC & GEMINI)
    # =========================================================================
    def _generate_counter_message(
        self,
        session: PracticeNegotiationSession,
        decision: str,
        human_offer: float,
        counter_offer: float,
        personality: str,
        role: str
    ) -> str:
        """
        Generate natural language counter response using Gemini (if available) or rich templates.
        """
        # Try Gemini LLM first if configured
        if self.client is not None:
            llm_text = self._try_gemini_response(session, decision, human_offer, counter_offer, personality, role)
            if llm_text:
                return llm_text

        # High-quality deterministic templates
        h_str = format_inr(human_offer)
        c_str = format_inr(counter_offer)

        if role == "seller":
            if personality == "aggressive":
                templates = [
                    f"Your offer of {h_str} is too low for a premium property in this locality. The absolute best I can do right now is {c_str}.",
                    f"I cannot accept {h_str} as it undervalues the asset. My revised price is {c_str}, and I expect serious counter-proposals.",
                    f"Considering the strong interest from other prospective buyers, {h_str} won't work. I can reduce my asking price to {c_str}."
                ]
            elif personality == "risk_averse":
                templates = [
                    f"Thank you for the offer of {h_str}. To ensure a balanced and fair agreement in line with market benchmarks, I can counter at {c_str}.",
                    f"I appreciate your proposal of {h_str}. Based on verified valuation for this property, my safe counter-offer is {c_str}.",
                    f"While {h_str} is below my target, I am willing to adjust conservatively to {c_str} to move towards a secure closing."
                ]
            else:  # collaborative
                templates = [
                    f"Thank you for your offer of {h_str}! I really appreciate your interest. In the spirit of finding a mutually beneficial deal, I can come down to {c_str}.",
                    f"I appreciate your proposal of {h_str}. Let's meet closer to the middle — how does {c_str} sound to you?",
                    f"Thanks for taking a step forward with {h_str}. To help make this work for both of us, I am happy to offer {c_str}."
                ]
        else:  # buyer
            if personality == "aggressive":
                templates = [
                    f"Your demand of {h_str} is higher than comparable units in this area. I can only increase my offer to {c_str}.",
                    f"I have inspected the market carefully and {h_str} is steep. My strict counter is {c_str}.",
                    f"{h_str} exceeds my financial model. The most I am willing to offer at this stage is {c_str}."
                ]
            elif personality == "risk_averse":
                templates = [
                    f"I have reviewed your price of {h_str}. To stay within a prudent risk-adjusted budget, I can propose {c_str}.",
                    f"Thank you for sharing {h_str}. In order to maintain safety and avoid overpaying, my updated offer is {c_str}.",
                    f"I understand your valuation of {h_str}, but based on verified price per sq.ft. metrics, I can comfortably offer {c_str}."
                ]
            else:  # collaborative
                templates = [
                    f"Thank you for your response of {h_str}. I am eager to make this work, so I'm pleased to raise my offer to {c_str}.",
                    f"I appreciate your flexibility! To move us closer to an agreement, I can increase my offer to {c_str}.",
                    f"Thanks for working with me. In the spirit of reaching a great deal today, I am happy to counter at {c_str}."
                ]

        return random.choice(templates)

    def _generate_acceptance_message(
        self,
        session: PracticeNegotiationSession,
        agreed_price: float,
        by_human: bool = False
    ) -> str:
        agreed_str = format_inr(agreed_price)
        prop = session.property.get("Property Title") or "the property"
        
        if by_human:
            return (
                f"Fantastic! We have reached an agreement on {prop} at {agreed_str}. "
                f"Thank you for a constructive negotiation. The deal is officially finalized!"
            )
        else:
            return (
                f"DECISION: ACCEPT\n\n"
                f"I accept your offer of {agreed_str} for {prop}. "
                f"We have reached a successful agreement. Thank you for negotiating with me!"
            )

    def _generate_rejection_message(self, session: PracticeNegotiationSession, reason: str) -> str:
        return (
            f"DECISION: REJECT\n\n"
            f"We were unable to reach an agreement on the property price. "
            f"The negotiation is concluded without a deal. Reason: {reason}"
        )

    def _try_gemini_response(
        self,
        session: PracticeNegotiationSession,
        decision: str,
        human_offer: float,
        counter_offer: float,
        personality: str,
        role: str
    ) -> Optional[str]:
        """
        Optional LLM phrasing generation with strict constraints to preserve evaluator prices.
        """
        try:
            prompt = f"""
You are an AI {role} negotiating a real estate property with a human participant.
Property: {session.property.get('Property Title', 'Real Estate Property')} in {session.property.get('Location', 'Location')}
Reference Price: {format_inr(session.reference_price)}
Personality: {personality}
Human offer: {format_inr(human_offer)}
Evaluator Decision: {decision}
Exact Counter Price to use: {format_inr(counter_offer)}

Generate a natural, professional 2-3 sentence negotiation response matching your {personality} personality.
Rules:
1. You MUST mention your counter-offer price of exactly {format_inr(counter_offer)}.
2. Do not invent any other numbers or prices.
3. Match the tone of {personality} personality ({'firm, assertive, demanding' if personality=='aggressive' else 'warm, flexible, win-win' if personality=='collaborative' else 'careful, analytical, prudent'}).
4. Output only the message text.
"""
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            if response and hasattr(response, "text") and response.text:
                return response.text.strip().replace("```", "")
        except Exception as e:
            print(f"[PracticeAgent] Gemini generation error: {e}")
        return None
