# negotiation_runner.py


def format_price(price):
    """Convert rupees into lakhs."""

    if price is None:
        return "Unknown"

    return f"₹{price / 100000:.2f} lakhs"


def print_evaluation(evaluation):
    """
    Display the evaluation after the agent response.

    offer_price   = price offered by the other agent
    counter_price = price proposed by the current agent
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

    print(
        f"\nDecision: {decision}"
    )

    if offer_price is not None:
        print(
            f"Offer detected: "
            f"{format_price(offer_price)}"
        )

    if (
        decision == "COUNTER"
        and counter_price is not None
    ):
        print(
            f"Counteroffer: "
            f"{format_price(counter_price)}"
        )


def create_initial_buyer_evaluation(
    reference_price
):
    """
    Create the Buyer's opening offer.

    Opening offer = 75% of reference price.
    """

    initial_offer = (
        reference_price * 0.75
    )

    return {
        "decision": "COUNTER",
        "offer_price": initial_offer,
        "counter_price": initial_offer,
        "reason": (
            "Buyer is making the opening "
            "offer below the reference price."
        )
    }


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

    # =====================================================
    # START NEGOTIATION
    # =====================================================

    print("\n===================================")
    print("       NEGOTIATION STARTED")
    print("===================================")

    orchestrator.start_negotiation()

    # =====================================================
    # ROUND 1 - BUYER OPENING
    # =====================================================

    current_round = orchestrator.round_count

    print("\n===================================")
    print(f"ROUND {current_round}")
    print("CURRENT AGENT: Buyer Agent")
    print("===================================")

    print(
        "Generating Buyer response using Gemini..."
    )

    # -----------------------------------------------------
    # Initial Buyer offer
    # -----------------------------------------------------

    buyer_evaluation = (
        create_initial_buyer_evaluation(
            reference_price
        )
    )

    # -----------------------------------------------------
    # Generate Buyer response
    # -----------------------------------------------------

    buyer_message = (
        buyer_reasoning.generate_response(
            orchestrator.get_history(),
            buyer_evaluation
        )
    )

    print("\nBuyer Agent:")
    print(buyer_message)

    # -----------------------------------------------------
    # Display evaluation
    # -----------------------------------------------------

    print_evaluation(
        buyer_evaluation
    )

    # -----------------------------------------------------
    # Store Buyer message
    # -----------------------------------------------------

    orchestrator.add_message(
        "Buyer Agent",
        buyer_message
    )

    # The Seller will respond to this message.
    current_message = buyer_message

    # =====================================================
    # MOVE TO SELLER
    # =====================================================

    orchestrator.next_turn()

    # =====================================================
    # MAIN NEGOTIATION LOOP
    # =====================================================

    while (
        orchestrator.round_count
        <= max_rounds
    ):

        # =================================================
        # SELLER TURN
        # =================================================

        current_round = (
            orchestrator.round_count
        )

        print("\n===================================")
        print(f"ROUND {current_round}")
        print("CURRENT AGENT: Seller Agent")
        print("===================================")

        print(
            "Generating Seller response using Gemini..."
        )

        # -------------------------------------------------
        # Evaluate Buyer's message
        # -------------------------------------------------

        seller_evaluation = (
            seller_evaluator.evaluate(
                current_message
            )
        )

        # -------------------------------------------------
        # Generate Seller response
        # -------------------------------------------------

        seller_message = (
            seller_reasoning.generate_response(
                orchestrator.get_history(),
                seller_evaluation
            )
        )

        print("\nSeller Agent:")
        print(seller_message)

        # -------------------------------------------------
        # Display evaluation
        # -------------------------------------------------

        print_evaluation(
            seller_evaluation
        )

        # -------------------------------------------------
        # Store Seller message
        # -------------------------------------------------

        orchestrator.add_message(
            "Seller Agent",
            seller_message
        )

        # =================================================
        # CHECK SELLER ACCEPTANCE
        # =================================================

        if (
            seller_evaluation.get(
                "decision"
            )
            == "ACCEPT"
        ):

            agreed_price = (
                seller_evaluation.get(
                    "offer_price"
                )
            )

            if agreed_price is None:
                agreed_price = (
                    seller_evaluation.get(
                        "counter_price"
                    )
                )

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")

            print(
                f"Agreed Price: "
                f"{format_price(agreed_price)}"
            )

            return {
                "status": "AGREED",
                "price": agreed_price
            }

        # =================================================
        # SELLER COUNTEROFFER BECOMES BUYER'S NEXT OFFER
        # =================================================

        current_message = seller_message

        # -------------------------------------------------
        # Move to Buyer
        # -------------------------------------------------

        orchestrator.next_turn()

        # Check maximum rounds.
        if (
            orchestrator.round_count
            > max_rounds
        ):
            break

        # =================================================
        # BUYER TURN
        # =================================================

        current_round = (
            orchestrator.round_count
        )

        print("\n===================================")
        print(f"ROUND {current_round}")
        print("CURRENT AGENT: Buyer Agent")
        print("===================================")

        print(
            "Generating Buyer response using Gemini..."
        )

        # -------------------------------------------------
        # Evaluate Seller's message
        # -------------------------------------------------

        buyer_evaluation = (
            buyer_evaluator.evaluate(
                current_message
            )
        )

        # -------------------------------------------------
        # Generate Buyer response
        # -------------------------------------------------

        buyer_message = (
            buyer_reasoning.generate_response(
                orchestrator.get_history(),
                buyer_evaluation
            )
        )

        print("\nBuyer Agent:")
        print(buyer_message)

        # -------------------------------------------------
        # Display evaluation
        # -------------------------------------------------

        print_evaluation(
            buyer_evaluation
        )

        # -------------------------------------------------
        # Store Buyer message
        # -------------------------------------------------

        orchestrator.add_message(
            "Buyer Agent",
            buyer_message
        )

        # =================================================
        # CHECK BUYER ACCEPTANCE
        # =================================================

        if (
            buyer_evaluation.get(
                "decision"
            )
            == "ACCEPT"
        ):

            agreed_price = (
                buyer_evaluation.get(
                    "offer_price"
                )
            )

            if agreed_price is None:
                agreed_price = (
                    buyer_evaluation.get(
                        "counter_price"
                    )
                )

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")

            print(
                f"Agreed Price: "
                f"{format_price(agreed_price)}"
            )

            return {
                "status": "AGREED",
                "price": agreed_price
            }

        # =================================================
        # BUYER COUNTEROFFER BECOMES SELLER'S NEXT OFFER
        # =================================================

        current_message = buyer_message

        # -------------------------------------------------
        # Move to Seller
        # -------------------------------------------------

        orchestrator.next_turn()

    # =====================================================
    # MAXIMUM ROUNDS REACHED
    # =====================================================

    print("\n===================================")
    print("       NEGOTIATION ENDED")
    print("===================================")

    print(
        "Maximum negotiation rounds reached "
        "without an agreement."
    )

    return {
        "status": "NO_AGREEMENT",
        "price": None
    }