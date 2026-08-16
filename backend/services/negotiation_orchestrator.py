from typing import Dict, Any, List

from backend.services.negotiation_service import negotiation_service


class NegotiationOrchestrator:

    def run_negotiation(
        self,
        buyer_agent: Dict[str, Any],
        seller_agent: Dict[str, Any],
        constraints: Dict[str, Any],
        initial_buyer_offer: float,
        initial_seller_offer: float,
        max_rounds: int = 10,
    ) -> Dict[str, Any]:

        history: List[Dict[str, Any]] = []

        buyer_offer = float(initial_buyer_offer)
        seller_offer = float(initial_seller_offer)

        for round_number in range(1, max_rounds + 1):

            # ==============================
            # BUYER AGENT
            # ==============================

            buyer_decision = negotiation_service._ask_agent(
                agent=buyer_agent,
                role="buyer",
                current_offer=buyer_offer,
                opponent_offer=seller_offer,
                constraints=constraints,
                history=history,
            )

            buyer_offer = float(buyer_decision["offer"])

            # ==============================
            # BUYER LIMIT
            # ==============================

            buyer_max = float(
                constraints["buyer_max_budget"]
            )

            if buyer_offer > buyer_max:
                buyer_offer = buyer_max

            # ==============================
            # SELLER AGENT
            # ==============================

            seller_decision = negotiation_service._ask_agent(
                agent=seller_agent,
                role="seller",
                current_offer=seller_offer,
                opponent_offer=buyer_offer,
                constraints=constraints,
                history=history,
            )

            seller_offer = float(seller_decision["offer"])

            # ==============================
            # SELLER LIMIT
            # ==============================

            seller_min = float(
                constraints["seller_min_price"]
            )

            if seller_offer < seller_min:
                seller_offer = seller_min

            # ==============================
            # CALCULATE GAP
            # ==============================

            gap = abs(buyer_offer - seller_offer)

            # ==============================
            # CHECK AGREEMENT
            # ==============================

            if buyer_offer >= seller_offer:

                final_price = seller_offer

                history.append({
                    "round": round_number,
                    "buyer_offer": buyer_offer,
                    "seller_offer": seller_offer,
                    "gap": 0,
                    "decision": "agreement",
                    "buyer_reasoning": buyer_decision["reasoning"],
                    "seller_reasoning": seller_decision["reasoning"],
                })

                return {
                    "status": "agreement",
                    "final_price": final_price,
                    "total_rounds": round_number,
                    "rounds": history,
                }

            # ==============================
            # SAVE ROUND
            # ==============================

            history.append({
                "round": round_number,
                "buyer_offer": buyer_offer,
                "seller_offer": seller_offer,
                "gap": gap,
                "decision": "counter_offer",
                "buyer_reasoning": buyer_decision["reasoning"],
                "seller_reasoning": seller_decision["reasoning"],
            })

        # ==============================
        # NO AGREEMENT
        # ==============================

        return {
            "status": "no_agreement",
            "final_price": None,
            "total_rounds": max_rounds,
            "rounds": history,
        }


negotiation_orchestrator = NegotiationOrchestrator()