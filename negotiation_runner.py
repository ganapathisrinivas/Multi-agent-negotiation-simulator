
import re


# ============================================================
# PRICE EXTRACTION
# ============================================================

def extract_offer_amount(text):
    """
    Extract an offer amount from an agent response.

    Examples:

        ₹54.00 lakhs -> 5400000
        ₹65.50 lakhs -> 6550000
        ₹54 lakh     -> 5400000
        ₹5400000     -> 5400000
    """

    if text is None:
        return None

    if isinstance(text, (int, float)):
        return float(text)

    text = str(text)

    # --------------------------------------------------------
    # Lakhs
    # --------------------------------------------------------

    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*'
        r'(?:lakhs?|lakh)\b',
        text,
        re.IGNORECASE
    )

    if match:

        value = (
            match.group(1)
            .replace(",", "")
        )

        return float(value) * 100000

    # --------------------------------------------------------
    # L format
    # --------------------------------------------------------

    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*[lL]\b',
        text
    )

    if match:

        value = (
            match.group(1)
            .replace(",", "")
        )

        return float(value) * 100000

    # --------------------------------------------------------
    # Crores
    # --------------------------------------------------------

    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*'
        r'(?:crores?|crore)\b',
        text,
        re.IGNORECASE
    )

    if match:

        value = (
            match.group(1)
            .replace(",", "")
        )

        return float(value) * 10000000

    # --------------------------------------------------------
    # Rupees
    # --------------------------------------------------------

    match = re.search(
        r'₹\s*([\d,]+(?:\.\d+)?)',
        text
    )

    if match:

        value = (
            match.group(1)
            .replace(",", "")
        )

        return float(value)

    # --------------------------------------------------------
    # Counteroffer without ₹
    # --------------------------------------------------------

    match = re.search(
        r'(?:COUNTEROFFER|COUNTER OFFER|OFFER)'
        r'\s*[:\-]?\s*'
        r'₹?\s*([\d,]+(?:\.\d+)?)'
        r'\s*(?:lakhs?|lakh|L)?',
        text,
        re.IGNORECASE
    )

    if match:

        value = (
            match.group(1)
            .replace(",", "")
        )

        number = float(value)

        if number < 10000:
            return number * 100000

        return number

    return None


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(amount):

    if amount is None:
        return "N/A"

    return (
        f"₹{float(amount) / 100000:.2f} lakhs"
    )


# ============================================================
# EXACT MATCH ONLY
# ============================================================

def offers_match_exactly(
    buyer_offer,
    seller_offer
):

    if buyer_offer is None:
        return False

    if seller_offer is None:
        return False

    return (
        float(buyer_offer) ==
        float(seller_offer)
    )


# ============================================================
# ORCHESTRATOR STATE
# ============================================================

def update_orchestrator_state(
    orchestrator,
    status,
    current_agent,
    last_offer
):

    try:

        state = orchestrator.get_state()

        state["status"] = status
        state["current_agent"] = current_agent
        state["last_offer"] = last_offer

    except Exception:
        pass


# ============================================================
# ADD HISTORY
# ============================================================

def add_history(
    history,
    round_number,
    agent,
    message
):

    history.append(
        {
            "round": round_number,
            "agent": agent,
            "message": message
        }
    )


# ============================================================
# ADD ORCHESTRATOR MESSAGE
# ============================================================

def add_orchestrator_message(
    orchestrator,
    agent,
    message
):

    try:

        orchestrator.add_message(
            agent,
            message
        )

    except Exception:
        pass


# ============================================================
# NEGOTIATION RUNNER
# ============================================================

def run_negotiation(
    orchestrator,
    buyer_reasoning,
    seller_reasoning,
    buyer_evaluator,
    seller_evaluator,
    property_data,
    reference_price,
    max_rounds=10
):
    """
    Main AI-vs-AI negotiation loop.

    FINAL NEGOTIATION RULES:

    1. Buyer starts.

    2. Seller responds.

    3. One round = one Buyer turn + one Seller turn.

    4. Buyer moves upward.

    5. Seller starts at the reference/property price.

    6. Seller moves downward.

    7. Exact equality is the ONLY agreement condition.

    8. Close prices are NOT agreement.

    9. No tolerance is used.

    10. Gemini does not control prices.

    11. Evaluators control prices.

    12. If exact equality is not reached by max_rounds,
        status is REJECTED.

    13. AGREEMENT_REACHED always has agreed_price.
    """

    if max_rounds is None:
        max_rounds = 10

    try:
        max_rounds = int(max_rounds)
    except Exception:
        max_rounds = 10

    if max_rounds <= 0:
        max_rounds = 10

    reference_price = float(
        reference_price
    )

    # ========================================================
    # STATE
    # ========================================================

    buyer_offer = None
    seller_offer = None

    last_buyer_offer = None
    last_seller_offer = None

    agreed_price = None

    history = []

    status = "REJECTED"

    # ========================================================
    # START NEGOTIATION
    # ========================================================

    try:
        orchestrator.start_negotiation()
    except Exception:
        pass

    update_orchestrator_state(
        orchestrator,
        "Negotiation Started",
        "Buyer Agent",
        None
    )

    print("\n===================================")
    print("       NEGOTIATION STARTED")
    print("===================================")

    print(
        f"Reference Price: "
        f"{format_price(reference_price)}"
    )

    # ========================================================
    # ROUND LOOP
    # ========================================================

    for round_number in range(
        1,
        max_rounds + 1
    ):

        print("\n===================================")
        print(f"ROUND {round_number}")
        print("===================================")

        # ====================================================
        # BUYER TURN
        # ====================================================

        print("CURRENT AGENT: Buyer Agent")

        buyer_evaluation = (
            buyer_evaluator.evaluate(
                incoming_offer=seller_offer,
                previous_offer=last_buyer_offer,
                reference_price=reference_price
            )
        )

        print(
            "\nGenerating Buyer response..."
        )

        try:

            buyer_response = (
                buyer_reasoning.generate_response(
                    history,
                    buyer_evaluation
                )
            )

        except Exception as error:

            print(
                "\nReasoning engine error:"
            )

            print(str(error))

            buyer_response = (
                _fallback_response_from_evaluation(
                    buyer_evaluation
                )
            )

        # ----------------------------------------------------
        # Price comes ONLY from evaluator
        # ----------------------------------------------------

        buyer_decision = str(
            buyer_evaluation.get(
                "decision",
                "COUNTER"
            )
        ).upper()

        if buyer_decision == "ACCEPT":

            buyer_offer = (
                buyer_evaluation.get(
                    "accepted_price"
                )
            )

        else:

            buyer_offer = (
                buyer_evaluation.get(
                    "counter_price"
                )
            )

        # ----------------------------------------------------
        # Safety fallback
        # ----------------------------------------------------

        if buyer_offer is None:

            if last_buyer_offer is not None:
                buyer_offer = last_buyer_offer
            else:
                buyer_offer = (
                    reference_price * 0.90
                )

            buyer_offer = _round_price(
                buyer_offer
            )

            buyer_response = (
                _fallback_counter_response(
                    buyer_offer
                )
            )

        buyer_offer = _round_price(
            buyer_offer
        )

        # ----------------------------------------------------
        # Buyer output
        # ----------------------------------------------------

        print("\nBuyer Agent:")
        print(buyer_response)

        print(
            f"\nDecision: {buyer_decision}"
        )

        print(
            f"Buyer Offer: "
            f"{format_price(buyer_offer)}"
        )

        add_history(
            history,
            round_number,
            "Buyer Agent",
            buyer_response
        )

        add_orchestrator_message(
            orchestrator,
            "Buyer Agent",
            buyer_response
        )

        # ----------------------------------------------------
        # Exact agreement after buyer turn
        # ----------------------------------------------------

        if offers_match_exactly(
            buyer_offer,
            seller_offer
        ):

            agreed_price = float(
                buyer_offer
            )

            status = "AGREEMENT_REACHED"

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")

            print(
                f"Buyer Offer: "
                f"{format_price(buyer_offer)}"
            )

            print(
                f"Seller Offer: "
                f"{format_price(seller_offer)}"
            )

            print(
                f"Agreed Price: "
                f"{format_price(agreed_price)}"
            )

            update_orchestrator_state(
                orchestrator,
                "Agreement Reached",
                "Negotiation Completed",
                format_price(agreed_price)
            )

            break

        last_buyer_offer = buyer_offer

        # ====================================================
        # SELLER TURN
        # ====================================================

        print("\nCURRENT AGENT: Seller Agent")

        seller_evaluation = (
            seller_evaluator.evaluate(
                incoming_offer=buyer_offer,
                previous_offer=last_seller_offer,
                reference_price=reference_price
            )
        )

        print(
            "\nGenerating Seller response..."
        )

        try:

            seller_response = (
                seller_reasoning.generate_response(
                    history,
                    seller_evaluation
                )
            )

        except Exception as error:

            print(
                "\nReasoning engine error:"
            )

            print(str(error))

            seller_response = (
                _fallback_response_from_evaluation(
                    seller_evaluation
                )
            )

        # ----------------------------------------------------
        # Price comes ONLY from evaluator
        # ----------------------------------------------------

        seller_decision = str(
            seller_evaluation.get(
                "decision",
                "COUNTER"
            )
        ).upper()

        if seller_decision == "ACCEPT":

            seller_offer = (
                seller_evaluation.get(
                    "accepted_price"
                )
            )

        else:

            seller_offer = (
                seller_evaluation.get(
                    "counter_price"
                )
            )

        # ----------------------------------------------------
        # Safety fallback
        # ----------------------------------------------------

        if seller_offer is None:

            if last_seller_offer is not None:
                seller_offer = last_seller_offer
            else:
                seller_offer = reference_price

            seller_offer = _round_price(
                seller_offer
            )

            seller_response = (
                _fallback_counter_response(
                    seller_offer
                )
            )

        seller_offer = _round_price(
            seller_offer
        )

        # ----------------------------------------------------
        # Seller output
        # ----------------------------------------------------

        print("\nSeller Agent:")
        print(seller_response)

        print(
            f"\nDecision: {seller_decision}"
        )

        print(
            f"Seller Offer: "
            f"{format_price(seller_offer)}"
        )

        add_history(
            history,
            round_number,
            "Seller Agent",
            seller_response
        )

        add_orchestrator_message(
            orchestrator,
            "Seller Agent",
            seller_response
        )

        # ----------------------------------------------------
        # Exact agreement after seller turn
        # ----------------------------------------------------

        if offers_match_exactly(
            buyer_offer,
            seller_offer
        ):

            agreed_price = float(
                buyer_offer
            )

            status = "AGREEMENT_REACHED"

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")

            print(
                f"Buyer Offer: "
                f"{format_price(buyer_offer)}"
            )

            print(
                f"Seller Offer: "
                f"{format_price(seller_offer)}"
            )

            print(
                f"Agreed Price: "
                f"{format_price(agreed_price)}"
            )

            update_orchestrator_state(
                orchestrator,
                "Agreement Reached",
                "Negotiation Completed",
                format_price(agreed_price)
            )

            break

        last_seller_offer = seller_offer

        # ====================================================
        # CONTINUE TO NEXT ROUND
        # ====================================================

        update_orchestrator_state(
            orchestrator,
            "Negotiation In Progress",
            "Buyer Agent",
            format_price(seller_offer)
        )

    # ========================================================
    # MAX ROUNDS REACHED
    # ========================================================

    if agreed_price is None:

        status = "REJECTED"

        last_offer = (
            seller_offer
            if seller_offer is not None
            else buyer_offer
        )

        update_orchestrator_state(
            orchestrator,
            "Negotiation Rejected",
            "Negotiation Completed",
            format_price(last_offer)
        )

        print("\n===================================")
        print("       NEGOTIATION REJECTED")
        print("===================================")

        print(
            "Buyer and Seller did not reach "
            "the exact same offer."
        )

        print(
            f"Maximum rounds reached: "
            f"{max_rounds}"
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {
        "status": status,
        "agreed_price": agreed_price,
        "negotiation_history": history
    }

    # --------------------------------------------------------
    # Safety invariant:
    #
    # AGREEMENT_REACHED can NEVER have null agreed_price.
    # --------------------------------------------------------

    if (
        result["status"] == "AGREEMENT_REACHED"
        and result["agreed_price"] is None
    ):

        result["status"] = "REJECTED"

    return result


# ============================================================
# FALLBACK FROM EVALUATION
# ============================================================

def _fallback_response_from_evaluation(
    evaluation
):

    decision = str(
        evaluation.get(
            "decision",
            "COUNTER"
        )
    ).upper()

    if decision == "ACCEPT":

        price = evaluation.get(
            "accepted_price"
        )

        return (
            "DECISION: ACCEPT\n\n"
            "We accept the current offer.\n\n"
            f"ACCEPTED OFFER: "
            f"{format_price(price)}"
        )

    price = evaluation.get(
        "counter_price"
    )

    return (
        "DECISION: COUNTER\n\n"
        "We appreciate the offer and "
        "would like to continue negotiating.\n\n"
        f"COUNTEROFFER: "
        f"{format_price(price)}"
    )


# ============================================================
# FALLBACK COUNTER RESPONSE
# ============================================================

def _fallback_counter_response(
    price
):

    return (
        "DECISION: COUNTER\n\n"
        "We would like to continue the "
        "negotiation with the following offer.\n\n"
        f"COUNTEROFFER: "
        f"{format_price(price)}"
    )


# ============================================================
# ROUND PRICE
# ============================================================

def _round_price(
    price
):

    return float(
        round(
            float(price) / 1000
        ) * 1000
    )