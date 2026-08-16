from typing import Dict, Any, List
import json

from backend.services.gemini_service import gemini_service


class NegotiationService:

    # =========================================================
    # ASK AGENT
    # =========================================================

    def _ask_agent(
        self,
        agent: Dict[str, Any],
        role: str,
        current_offer: float,
        opponent_offer: float,
        constraints: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        # -----------------------------------------------------
        # Agent financial limit
        # -----------------------------------------------------

        if role == "buyer":
            limit = float(constraints["buyer_max_budget"])
            limit_name = "maximum budget"
        else:
            limit = float(constraints["seller_min_price"])
            limit_name = "minimum acceptable price"

        personality = agent.get(
            "personality",
            "collaborative"
        ).lower()

        # -----------------------------------------------------
        # Gemini prompt
        # -----------------------------------------------------

        prompt = f"""
You are the {role.upper()} AGENT in an AI-powered
real estate negotiation system.

Your job is to negotiate intelligently with another AI agent.

==================================================
AGENT PROFILE
==================================================

Name: {agent["name"]}
Role: {agent["role"]}
Goal: {agent["goal"]}
Personality: {personality}

==================================================
FINANCIAL CONSTRAINT
==================================================

Your {limit_name}: {limit}

You MUST respect this limit.

==================================================
CURRENT NEGOTIATION
==================================================

Your previous/current offer: {current_offer}
Opponent's current offer: {opponent_offer}

Current gap:
{abs(opponent_offer - current_offer)}

==================================================
NEGOTIATION HISTORY
==================================================

{json.dumps(history, indent=2)}

==================================================
PERSONALITY RULES
==================================================

COLLABORATIVE:
- Seek a fair agreement.
- Make reasonable concessions.
- Gradually move toward the opponent.
- Avoid unnecessary conflict.

AGGRESSIVE:
- Protect your side strongly.
- Make smaller concessions.
- Apply negotiation pressure.
- Do not accept an unfavorable deal.

CONSERVATIVE:
- Make very careful concessions.
- Protect your financial limit.
- Avoid large movements.

FLEXIBLE:
- Adapt to the opponent's behavior.
- Move toward agreement when the gap becomes small.

==================================================
NEGOTIATION STRATEGY
==================================================

Analyze:

1. Your goal.
2. Your personality.
3. Your financial constraint.
4. The opponent's latest offer.
5. Previous negotiation rounds.
6. How much the opponent has moved.
7. Whether the remaining gap is small enough to close.
8. Whether you should make a counter-offer or agree.

Do NOT blindly split the difference every time.

Your offer should represent your negotiation strategy.

==================================================
STRICT RULES
==================================================

1. Buyer MUST NEVER offer more than:
   {constraints["buyer_max_budget"]}

2. Seller MUST NEVER offer below:
   {constraints["seller_min_price"]}

3. Never violate your financial constraint.

4. Do not invent property information.

5. Consider the complete negotiation history.

6. Avoid repeating the exact same offer unnecessarily.

7. Use smaller concessions as the negotiation gets closer.

8. Select "agreement" only when accepting the current
   negotiation position is reasonable for your agent.

9. Keep reasoning short and specific.

10. Return ONLY valid JSON.

==================================================
RESPONSE FORMAT
==================================================

Return exactly:

{{
    "decision": "counter_offer",
    "offer": 450000,
    "reasoning": "Short explanation of the negotiation decision."
}}

The decision MUST be either:

"counter_offer"

or

"agreement"

==================================================
IMPORTANT
==================================================

If you select "agreement", your offer should represent
the price you are willing to accept.

If you select "counter_offer", provide your next offer.

Do not include markdown.
Do not include ```json.
Return JSON only.
"""

        # -----------------------------------------------------
        # Call Gemini
        # -----------------------------------------------------

        response = gemini_service.generate(prompt)

        try:

            # -------------------------------------------------
            # Clean Gemini response
            # -------------------------------------------------

            cleaned = response.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "")
                cleaned = cleaned.replace("```", "")
                cleaned = cleaned.strip()

            # -------------------------------------------------
            # Parse JSON
            # -------------------------------------------------

            result = json.loads(cleaned)

            # -------------------------------------------------
            # Extract decision
            # -------------------------------------------------

            offer = float(result["offer"])

            decision = result.get(
                "decision",
                "counter_offer"
            )

            reasoning = result.get(
                "reasoning",
                "No reasoning provided."
            )

            # -------------------------------------------------
            # Validate decision
            # -------------------------------------------------

            if decision not in [
                "counter_offer",
                "agreement"
            ]:
                decision = "counter_offer"

            # -------------------------------------------------
            # Enforce financial constraints
            # -------------------------------------------------

            if role == "buyer":

                if offer > limit:
                    offer = limit

            else:

                if offer < limit:
                    offer = limit

            # -------------------------------------------------
            # Return agent decision
            # -------------------------------------------------

            return {
                "decision": decision,
                "offer": offer,
                "reasoning": reasoning,
            }

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:

            # -------------------------------------------------
            # Gemini returned invalid JSON
            # -------------------------------------------------

            return {
                "decision": "counter_offer",
                "offer": current_offer,
                "reasoning": (
                    f"Gemini returned an invalid negotiation response: "
                    f"{str(e)}"
                ),
            }

    # =========================================================
    # NEGOTIATE
    # =========================================================

    def negotiate(
        self,
        buyer: Dict[str, Any],
        seller: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:

        # -----------------------------------------------------
        # Initial values
        # -----------------------------------------------------

        buyer_max = float(
            constraints["buyer_max_budget"]
        )

        seller_min = float(
            constraints["seller_min_price"]
        )

        # -----------------------------------------------------
        # Initial offers
        # -----------------------------------------------------

        buyer_offer = float(
            constraints.get(
                "buyer_initial_offer",
                seller_min * 0.85
            )
        )

        seller_offer = float(
            constraints.get(
                "seller_initial_offer",
                buyer_max
            )
        )

        # -----------------------------------------------------
        # Negotiation history
        # -----------------------------------------------------

        history: List[Dict[str, Any]] = []
        rounds: List[Dict[str, Any]] = []

        max_rounds = int(
            constraints.get(
                "max_rounds",
                10
            )
        )

        # -----------------------------------------------------
        # Negotiation loop
        # -----------------------------------------------------

        for round_number in range(1, max_rounds + 1):

            # =================================================
            # BUYER AGENT
            # =================================================

            buyer_result = self._ask_agent(
                agent=buyer,
                role="buyer",
                current_offer=buyer_offer,
                opponent_offer=seller_offer,
                constraints=constraints,
                history=history,
            )

            buyer_offer = float(
                buyer_result["offer"]
            )

            # =================================================
            # SELLER AGENT
            # =================================================

            seller_result = self._ask_agent(
                agent=seller,
                role="seller",
                current_offer=seller_offer,
                opponent_offer=buyer_offer,
                constraints=constraints,
                history=history,
            )

            seller_offer = float(
                seller_result["offer"]
            )

            # -------------------------------------------------
            # Calculate gap
            # -------------------------------------------------

            gap = abs(
                seller_offer - buyer_offer
            )

            # -------------------------------------------------
            # Determine agreement
            # -------------------------------------------------

            agreement = (
                buyer_result["decision"] == "agreement"
                or seller_result["decision"] == "agreement"
                or gap == 0
            )

            if agreement:

                final_price = round(
                    (buyer_offer + seller_offer) / 2,
                    2
                )

                # If both offers are equal, use that exact value.
                if buyer_offer == seller_offer:
                    final_price = round(
                        buyer_offer,
                        2
                    )

                decision = "agreement"

            else:

                final_price = None
                decision = "counter_offer"

            # -------------------------------------------------
            # Round data
            # -------------------------------------------------

            round_data = {
                "round": round_number,
                "buyer_offer": round(
                    buyer_offer,
                    2
                ),
                "seller_offer": round(
                    seller_offer,
                    2
                ),
                "gap": round(
                    gap,
                    2
                ),
                "buyer_personality": buyer.get(
                    "personality",
                    "collaborative"
                ),
                "seller_personality": seller.get(
                    "personality",
                    "collaborative"
                ),
                "decision": decision,
                "buyer_reasoning": buyer_result.get(
                    "reasoning",
                    ""
                ),
                "seller_reasoning": seller_result.get(
                    "reasoning",
                    ""
                ),
            }

            rounds.append(round_data)

            # -------------------------------------------------
            # Add round to history
            # -------------------------------------------------

            history.append(round_data)

            # -------------------------------------------------
            # Stop if agreement reached
            # -------------------------------------------------

            if agreement:

                return {
                    "status": "agreement",
                    "rounds": rounds,
                    "final_price": final_price,
                    "buyer": buyer["name"],
                    "seller": seller["name"],
                    "buyer_personality": buyer.get(
                        "personality",
                        "collaborative"
                    ),
                    "seller_personality": seller.get(
                        "personality",
                        "collaborative"
                    ),
                }

        # -----------------------------------------------------
        # No agreement
        # -----------------------------------------------------

        return {
            "status": "no_agreement",
            "rounds": rounds,
            "final_price": None,
            "buyer": buyer["name"],
            "seller": seller["name"],
            "buyer_personality": buyer.get(
                "personality",
                "collaborative"
            ),
            "seller_personality": seller.get(
                "personality",
                "collaborative"
            ),
        }


# =============================================================
# SERVICE INSTANCE
# =============================================================

negotiation_service = NegotiationService()