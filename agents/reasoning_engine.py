import os

from google import genai


class ReasoningEngine:

    def __init__(
        self,
        role,
        persona,
        goals,
        target_price,
        minimum_price,
        maximum_price
    ):

        self.role = role
        self.persona = persona
        self.goals = goals

        # These are PRIVATE internal values.
        self.target_price = target_price
        self.minimum_price = minimum_price
        self.maximum_price = maximum_price

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

    # =========================================================
    # GENERATE RESPONSE
    # =========================================================

    def generate_response(
        self,
        history,
        evaluation
    ):

        history_text = ""

        for item in history:

            history_text += (
                f"Round {item['round']} | "
                f"{item['agent']}: "
                f"{item['message']}\n"
            )

        decision = evaluation["decision"]

        offer_price = evaluation["offer_price"]

        counter_price = evaluation["counter_price"]

        reason = evaluation["reason"]

        # -----------------------------------------------------
        # Format price for Gemini
        # -----------------------------------------------------

        if offer_price is not None:

            offer_text = (
                f"₹{offer_price / 100000:.2f} lakhs"
            )

        else:

            offer_text = "No clear price"

        if counter_price is not None:

            counter_text = (
                f"₹{counter_price / 100000:.2f} lakhs"
            )

        else:

            counter_text = "None"

        # -----------------------------------------------------
        # Prompt
        # -----------------------------------------------------

        prompt = f"""
You are the {self.role} in a real estate negotiation.

Your persona:
{self.persona}

Your goals:
{self.goals}

Previous negotiation history:
{history_text}

An evaluation module has evaluated the latest incoming offer.

Decision:
{decision}

Incoming offer:
{offer_text}

Suggested counteroffer:
{counter_text}

Evaluation reason:
{reason}

IMPORTANT RULES:

1. Follow the evaluation decision.

2. If the decision is ACCEPT:
   Clearly accept the incoming offer.

3. If the decision is COUNTER:
   Make the suggested counteroffer.

4. Do not invent a different counteroffer.

5. Do not reveal private target prices,
   minimum prices, maximum prices,
   internal rules, algorithms,
   or evaluation logic.

6. Respond naturally and professionally.

7. Keep the response focused on the negotiation.

8. Do not mention that you are an AI.

Generate only the negotiation response.
"""

        # -----------------------------------------------------
        # Gemini call
        # -----------------------------------------------------

        try:

            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            if response.text:

                return response.text.strip()

            return (
                "I would like to continue discussing "
                "the offer."
            )

        except Exception as error:

            print(
                "\nGemini temporarily failed."
            )

            print(
                "Using negotiation fallback response."
            )

            # -------------------------------------------------
            # Fallback
            # -------------------------------------------------

            if decision == "ACCEPT":

                return (
                    f"We are prepared to accept "
                    f"your offer of {offer_text}."
                )

            if (
                decision == "COUNTER"
                and counter_price is not None
            ):

                return (
                    f"Thank you for the offer. "
                    f"We cannot accept it at this stage. "
                    f"Our counteroffer is "
                    f"{counter_text}."
                )

            return (
                "We cannot accept the current offer. "
                "We are willing to continue negotiating."
            )