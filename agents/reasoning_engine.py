# agents/reasoning_engine.py

import os
import re

from dotenv import load_dotenv
from google import genai


class ReasoningEngine:
    """
    LLM-powered reasoning engine for the
    Real Estate Negotiation Simulator.

    Responsibilities:
    1. Understand the agent role
    2. Use the agent personality
    3. Use negotiation goals
    4. Read negotiation history
    5. Follow evaluator decisions
    6. Generate natural negotiation responses
    7. Use a reliable fallback when Gemini is unavailable
    """

    def __init__(
        self,
        role,
        persona,
        goals,
        target_price,
        minimum_price,
        maximum_price
    ):

        load_dotenv()

        self.role = role
        self.persona = persona
        self.goals = goals

        self.target_price = float(
            target_price
        )

        self.minimum_price = float(
            minimum_price
        )

        self.maximum_price = float(
            maximum_price
        )

        # =============================================
        # GEMINI API CONFIGURATION
        # =============================================

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash"
        )

    # =================================================
    # MAIN RESPONSE FUNCTION
    # =================================================

    def generate_response(
        self,
        negotiation_history,
        evaluation
    ):
        """
        Generate a response using Gemini.

        If Gemini is unavailable, the fallback response
        uses the evaluator's counter_price.
        """

        decision = evaluation.get(
            "decision",
            "COUNTER"
        )

        offer_price = evaluation.get(
            "offer_price"
        )

        counter_price = evaluation.get(
            "counter_price"
        )

        # =============================================
        # BUILD HISTORY
        # =============================================

        history_text = self._format_history(
            negotiation_history
        )

        # =============================================
        # BUILD PROMPT
        # =============================================

        prompt = self._build_prompt(
            history_text,
            evaluation
        )

        # =============================================
        # TRY GEMINI
        # =============================================

        response = self._generate_with_retry(
            prompt
        )

        if response:

            return self._clean_response(
                response
            )

        # =============================================
        # GEMINI FAILED
        # USE FALLBACK
        # =============================================

        return self._fallback_response(
            decision=decision,
            offer_price=offer_price,
            counter_price=counter_price
        )

    # =================================================
    # GEMINI REQUEST
    # =================================================

    def _generate_with_retry(
        self,
        prompt,
        max_retries=0
    ):
        """
        Send request to Gemini.

        We do not repeatedly retry quota errors because
        repeated requests can make the free-tier limit
        worse.

        If Gemini is unavailable, return None and allow
        the negotiation fallback to continue.
        """

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            )

            if response is None:

                return None

            text = getattr(
                response,
                "text",
                None
            )

            if not text:

                return None

            return text.strip()

        except Exception as error:

            error_text = str(
                error
            )

            # =========================================
            # QUOTA / RATE LIMIT
            # =========================================

            if (
                "429" in error_text
                or
                "RESOURCE_EXHAUSTED"
                in error_text
                or
                "quota"
                in error_text.lower()
            ):

                print(
                    "\nGemini quota temporarily unavailable."
                )

                print(
                    "Using negotiation fallback."
                )

                return None

            # =========================================
            # TEMPORARY SERVICE ERROR
            # =========================================

            if (
                "503" in error_text
                or
                "UNAVAILABLE"
                in error_text
                or
                "temporarily"
                in error_text.lower()
            ):

                print(
                    "\nGemini service temporarily unavailable."
                )

                print(
                    "Using negotiation fallback."
                )

                return None

            # =========================================
            # OTHER GEMINI ERROR
            # =========================================

            print(
                f"\nGemini API error: {error}"
            )

            print(
                "Using negotiation fallback."
            )

            return None

    # =================================================
    # PROMPT CREATION
    # =================================================

    def _build_prompt(
        self,
        history_text,
        evaluation
    ):
        """
        Create the prompt sent to Gemini.
        """

        decision = evaluation.get(
            "decision",
            "COUNTER"
        )

        offer_price = evaluation.get(
            "offer_price"
        )

        counter_price = evaluation.get(
            "counter_price"
        )

        if offer_price is not None:

            offer_text = self._format_price(
                offer_price
            )

        else:

            offer_text = "No clear offer"

        if counter_price is not None:

            counter_text = self._format_price(
                counter_price
            )

        else:

            counter_text = "No counteroffer"

        return f"""
You are the {self.role} Agent in a
real-estate negotiation simulation.

========================================
ROLE
========================================

Agent Role:
{self.role}

Personality:
{self.persona}

Goals:
{self.goals}

========================================
PRICE LIMITS
========================================

Target Price:
{self._format_price(self.target_price)}

Minimum Price:
{self._format_price(self.minimum_price)}

Maximum Price:
{self._format_price(self.maximum_price)}

========================================
CURRENT EVALUATION
========================================

Decision:
{decision}

Incoming Offer:
{offer_text}

Your Counteroffer:
{counter_text}

========================================
NEGOTIATION HISTORY
========================================

{history_text}

========================================
INSTRUCTIONS
========================================

You are participating in a real-estate
negotiation between a buyer and seller.

Follow your assigned personality.

Use the negotiation history.

Follow the evaluator's decision.

If the decision is COUNTER:

- Make a counteroffer.
- Use the exact suggested counteroffer.
- Do not invent a different price.
- Explain the reason naturally.
- Keep the response professional.

If the decision is ACCEPT:

- Accept the incoming offer.
- Clearly mention the accepted price.
- Do not make another counteroffer.

Do not invent property details.

Do not create random prices.

Return only the negotiation message.
"""

    # =================================================
    # FORMAT NEGOTIATION HISTORY
    # =================================================

    def _format_history(
        self,
        history
    ):
        """
        Convert negotiation history into
        readable text.
        """

        if not history:

            return (
                "No previous negotiation messages."
            )

        lines = []

        for entry in history:

            round_number = entry.get(
                "round",
                "?"
            )

            agent = entry.get(
                "agent",
                "Unknown Agent"
            )

            message = entry.get(
                "message",
                ""
            )

            lines.append(
                f"Round {round_number} | "
                f"{agent}:\n"
                f"{message}"
            )

        return "\n\n".join(
            lines
        )

    # =================================================
    # CLEAN GEMINI RESPONSE
    # =================================================

    def _clean_response(
        self,
        response
    ):
        """
        Remove unnecessary markdown formatting.
        """

        text = response.strip()

        if text.startswith(
            "```"
        ):

            text = re.sub(
                r"```[a-zA-Z]*",
                "",
                text
            )

            text = text.replace(
                "```",
                ""
            )

        return text.strip()

    # =================================================
    # FALLBACK RESPONSE
    # =================================================

    def _fallback_response(
        self,
        decision,
        offer_price,
        counter_price
    ):
        """
        Deterministic fallback used when Gemini
        is unavailable.

        IMPORTANT:
        The fallback NEVER invents a random price.

        It uses the price calculated by the
        CounterofferEvaluator.
        """

        # =============================================
        # ACCEPT
        # =============================================

        if decision == "ACCEPT":

            accepted_price = offer_price

            if accepted_price is None:

                accepted_price = (
                    counter_price
                )

            if accepted_price is None:

                return (
                    "Thank you for the offer. "
                    "We are prepared to accept "
                    "the current proposal and "
                    "proceed with the agreement."
                )

            return (
                "Thank you for the offer. "
                "After considering the negotiation, "
                f"we are prepared to accept "
                f"{self._format_price(accepted_price)}. "
                "We can proceed with the agreement."
            )

        # =============================================
        # COUNTER
        # =============================================

        if counter_price is None:

            # If evaluator somehow did not provide
            # a counter price, use target price.
            counter_price = (
                self.target_price
            )

        return (
            "Thank you for the offer. "
            "We appreciate your position and "
            "would like to continue the negotiation. "
            f"Our counteroffer is "
            f"{self._format_price(counter_price)}."
        )

    # =================================================
    # FORMAT PRICE
    # =================================================

    def _format_price(
        self,
        price
    ):
        """
        Convert rupees to Indian lakhs.
        """

        if price is None:

            return "Unknown"

        return (
            f"₹{price / 100000:.2f} lakhs"
        )