'''class CounterofferEvaluator:
    """
    Controls the negotiation price.

    Buyer:
        - Starts below the reference price.
        - Moves upward toward the seller.

    Seller:
        - Starts above the buyer.
        - Moves downward toward the buyer.

    Agreement:
        - ONLY when both offers are exactly equal.

    The evaluator never considers two offers
    "close enough".
    """

    def __init__(
        self,
        role,
        target_price,
        minimum_price,
        maximum_price
    ):

        self.role = role.lower()

        self.target_price = float(
            target_price
        )

        self.minimum_price = float(
            minimum_price
        )

        self.maximum_price = float(
            maximum_price
        )

    # =========================================================
    # EVALUATE
    # =========================================================

    def evaluate(
        self,
        incoming_offer,
        previous_offer=None,
        reference_price=None
    ):
        """
        Return:

            decision
            incoming_offer
            previous_offer
            counter_price
            accepted_price

        Agreement is NOT created here merely because
        offers are close.

        Exact equality is handled by the negotiation runner.
        """

        if incoming_offer is None:

            return {
                "decision": "COUNTER",
                "incoming_offer": None,
                "previous_offer": previous_offer,
                "counter_price": self._initial_offer(
                    reference_price
                ),
                "accepted_price": None
            }

        incoming_offer = float(
            incoming_offer
        )

        if previous_offer is not None:

            previous_offer = float(
                previous_offer
            )

        # =====================================================
        # EXACT MATCH
        # =====================================================

        if (
            previous_offer is not None
            and incoming_offer == previous_offer
        ):

            return {
                "decision": "ACCEPT",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": None,
                "accepted_price": incoming_offer
            }

        # =====================================================
        # BUYER
        # =====================================================

        if self.role == "buyer":

            counter = self._buyer_counter(
                incoming_offer=incoming_offer,
                previous_offer=previous_offer,
                reference_price=reference_price
            )

            return {
                "decision": "COUNTER",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": counter,
                "accepted_price": None
            }

        # =====================================================
        # SELLER
        # =====================================================

        if self.role == "seller":

            counter = self._seller_counter(
                incoming_offer=incoming_offer,
                previous_offer=previous_offer,
                reference_price=reference_price
            )

            return {
                "decision": "COUNTER",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": counter,
                "accepted_price": None
            }

        raise ValueError(
            "Role must be 'buyer' or 'seller'."
        )

    # =========================================================
    # INITIAL OFFER
    # =========================================================

    def _initial_offer(
        self,
        reference_price
    ):

        if reference_price is None:
            reference_price = self.target_price

        reference_price = float(
            reference_price
        )

        if self.role == "buyer":

            # Buyer starts at target or below.
            offer = min(
                self.target_price,
                self.maximum_price
            )

        else:

            # Seller starts from the higher side.
            # This is intentionally based on the
            # reference/listed price.
            offer = min(
                reference_price,
                self.maximum_price
            )

            # Never start below seller target.
            offer = max(
                offer,
                self.target_price
            )

        return self._round_price(
            offer
        )

    # =========================================================
    # BUYER COUNTER
    # =========================================================

    def _buyer_counter(
        self,
        incoming_offer,
        previous_offer,
        reference_price
    ):

        incoming_offer = float(
            incoming_offer
        )

        # -----------------------------------------------------
        # First buyer offer
        # -----------------------------------------------------

        if previous_offer is None:

            counter = min(
                self.target_price,
                self.maximum_price
            )

            # If seller has already offered lower than
            # buyer target, match that exact offer.
            if incoming_offer <= counter:

                return self._round_price(
                    incoming_offer
                )

            return self._round_price(
                counter
            )

        # -----------------------------------------------------
        # Buyer must move UP, never DOWN
        # -----------------------------------------------------

        previous_offer = float(
            previous_offer
        )

        # Seller has reached or crossed buyer's offer.
        # Match exactly.
        if incoming_offer >= previous_offer:

            gap = (
                incoming_offer -
                previous_offer
            )

            # If gap is small, exact match.
            if gap <= 1000:

                return self._round_price(
                    incoming_offer
                )

            # Otherwise move upward.
            counter = (
                previous_offer +
                incoming_offer
            ) / 2

        else:

            # Never reduce buyer's offer.
            counter = previous_offer

        # Buyer must not exceed maximum.
        counter = min(
            counter,
            self.maximum_price
        )

        # Buyer should never go below previous offer.
        counter = max(
            counter,
            previous_offer
        )

        # If buyer reaches seller offer exactly,
        # return seller's exact price.
        if counter >= incoming_offer:

            counter = incoming_offer

        return self._round_price(
            counter
        )

    # =========================================================
    # SELLER COUNTER
    # =========================================================

    def _seller_counter(
        self,
        incoming_offer,
        previous_offer,
        reference_price
    ):

        incoming_offer = float(
            incoming_offer
        )

        # -----------------------------------------------------
        # First seller response
        # -----------------------------------------------------

        if previous_offer is None:

            if reference_price is None:

                reference_price = (
                    self.maximum_price
                )

            # Seller starts from the high side.
            starting_price = min(
                float(reference_price),
                self.maximum_price
            )

            starting_price = max(
                starting_price,
                self.target_price
            )

            # If buyer already offered at/above seller
            # target, match buyer exactly.
            if incoming_offer >= self.target_price:

                return self._round_price(
                    incoming_offer
                )

            # Move downward from listed/reference price,
            # but remain above buyer.
            counter = (
                starting_price +
                incoming_offer
            ) / 2

            counter = max(
                counter,
                incoming_offer
            )

            return self._round_price(
                counter
            )

        # -----------------------------------------------------
        # Seller must move DOWN, never UP
        # -----------------------------------------------------

        previous_offer = float(
            previous_offer
        )

        # If buyer reaches seller's previous offer,
        # exact match is possible.
        if incoming_offer >= previous_offer:

            gap = (
                previous_offer -
                incoming_offer
            )

            if gap <= 1000:

                return self._round_price(
                    incoming_offer
                )

            counter = (
                previous_offer +
                incoming_offer
            ) / 2

        else:

            # Seller must move DOWN toward buyer.
            counter = (
                previous_offer +
                incoming_offer
            ) / 2

        # Seller cannot increase.
        counter = min(
            counter,
            previous_offer
        )

        # Seller should not go below minimum.
        counter = max(
            counter,
            self.minimum_price
        )

        # If minimum prevents reaching buyer,
        # keep seller at minimum.
        if counter <= incoming_offer:

            counter = incoming_offer

        return self._round_price(
            counter
        )

    # =========================================================
    # ROUND PRICE
    # =========================================================

    def _round_price(
        self,
        price
    ):

        # Negotiation uses ₹1,000 precision.
        return float(
            round(
                float(price) / 1000
            ) * 1000
        )'''


class CounterofferEvaluator:
    """
    Controls negotiation prices.

    BUYER:
        - Starts below the reference price using its target price.
        - Moves upward toward the seller's offer.
        - Never moves downward.

    SELLER:
        - Starts from the reference/property price.
        - Moves downward toward the buyer.
        - Never moves upward.

    AGREEMENT:
        - Exact equality only.
        - No tolerance is used.

    The evaluator controls the actual price.
    Gemini does not decide prices.
    """

    def __init__(
        self,
        role,
        target_price,
        minimum_price,
        maximum_price
    ):
        self.role = role.lower()

        self.target_price = float(target_price)
        self.minimum_price = float(minimum_price)
        self.maximum_price = float(maximum_price)

    # =========================================================
    # EVALUATE
    # =========================================================

    def evaluate(
        self,
        incoming_offer,
        previous_offer=None,
        reference_price=None
    ):
        """
        Returns:

            decision
            incoming_offer
            previous_offer
            counter_price
            accepted_price

        Exact equality is handled by the runner as well.
        """

        if incoming_offer is None:
            return {
                "decision": "COUNTER",
                "incoming_offer": None,
                "previous_offer": previous_offer,
                "counter_price": self._initial_offer(
                    reference_price
                ),
                "accepted_price": None
            }

        incoming_offer = float(incoming_offer)

        if previous_offer is not None:
            previous_offer = float(previous_offer)

        # =====================================================
        # EXACT MATCH
        # =====================================================

        if (
            previous_offer is not None
            and incoming_offer == previous_offer
        ):
            return {
                "decision": "ACCEPT",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": None,
                "accepted_price": incoming_offer
            }

        # =====================================================
        # BUYER
        # =====================================================

        if self.role == "buyer":

            counter = self._buyer_counter(
                incoming_offer=incoming_offer,
                previous_offer=previous_offer,
                reference_price=reference_price
            )

            return {
                "decision": "COUNTER",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": counter,
                "accepted_price": None
            }

        # =====================================================
        # SELLER
        # =====================================================

        if self.role == "seller":

            counter = self._seller_counter(
                incoming_offer=incoming_offer,
                previous_offer=previous_offer,
                reference_price=reference_price
            )

            return {
                "decision": "COUNTER",
                "incoming_offer": incoming_offer,
                "previous_offer": previous_offer,
                "counter_price": counter,
                "accepted_price": None
            }

        raise ValueError(
            "Role must be 'buyer' or 'seller'."
        )

    # =========================================================
    # INITIAL OFFER
    # =========================================================

    def _initial_offer(
        self,
        reference_price
    ):
        """
        Buyer:
            Starts from its target price.

        Seller:
            Starts from the property/reference price.
        """

        if reference_price is None:
            reference_price = self.target_price

        reference_price = float(reference_price)

        if self.role == "buyer":

            offer = min(
                self.target_price,
                self.maximum_price
            )

            offer = max(
                offer,
                self.minimum_price
            )

        else:

            # Seller starts from the actual
            # property/reference price.
            offer = reference_price

            offer = min(
                offer,
                self.maximum_price
            )

            offer = max(
                offer,
                self.minimum_price
            )

        return self._round_price(offer)

    # =========================================================
    # BUYER COUNTER
    # =========================================================

    def _buyer_counter(
        self,
        incoming_offer,
        previous_offer,
        reference_price
    ):
        """
        Buyer always moves upward.

        Example:

            Buyer: 50L
            Seller: 67.2L

            Next buyer:
                58.6L

        The buyer never moves downward.
        """

        incoming_offer = float(incoming_offer)

        # -----------------------------------------------------
        # First buyer offer
        # -----------------------------------------------------

        if previous_offer is None:

            counter = min(
                self.target_price,
                self.maximum_price
            )

            counter = max(
                counter,
                self.minimum_price
            )

            return self._round_price(counter)

        previous_offer = float(previous_offer)

        # -----------------------------------------------------
        # Exact match
        # -----------------------------------------------------

        if incoming_offer == previous_offer:
            return self._round_price(
                incoming_offer
            )

        # -----------------------------------------------------
        # Seller is below buyer's previous offer.
        # Buyer must NOT decrease.
        # -----------------------------------------------------

        if incoming_offer < previous_offer:
            return self._round_price(
                previous_offer
            )

        # -----------------------------------------------------
        # Move upward toward seller.
        # -----------------------------------------------------

        counter = (
            previous_offer +
            incoming_offer
        ) / 2

        counter = self._round_price(counter)

        # -----------------------------------------------------
        # Guarantee upward movement if rounding
        # would otherwise keep the same price.
        # -----------------------------------------------------

        if counter <= previous_offer:

            counter = (
                previous_offer + 1000
            )

        # -----------------------------------------------------
        # Never exceed seller's current offer.
        # If it reaches seller exactly, that is valid.
        # -----------------------------------------------------

        if counter >= incoming_offer:

            counter = incoming_offer

        # -----------------------------------------------------
        # Buyer maximum
        # -----------------------------------------------------

        counter = min(
            counter,
            self.maximum_price
        )

        # Never go below previous offer.
        counter = max(
            counter,
            previous_offer
        )

        return self._round_price(counter)

    # =========================================================
    # SELLER COUNTER
    # =========================================================

    def _seller_counter(
        self,
        incoming_offer,
        previous_offer,
        reference_price
    ):
        """
        Seller always moves downward.

        First seller response:
            Seller starts from reference/property price.

        Later:
            Seller gradually moves downward toward buyer.
        """

        incoming_offer = float(incoming_offer)

        # -----------------------------------------------------
        # FIRST SELLER RESPONSE
        # -----------------------------------------------------

        if previous_offer is None:

            if reference_price is None:
                reference_price = self.maximum_price

            starting_price = float(reference_price)

            starting_price = min(
                starting_price,
                self.maximum_price
            )

            starting_price = max(
                starting_price,
                self.minimum_price
            )

            # IMPORTANT:
            # Do NOT average with buyer's offer.
            #
            # Seller starts from the property/reference price.
            return self._round_price(
                starting_price
            )

        previous_offer = float(previous_offer)

        # -----------------------------------------------------
        # EXACT MATCH
        # -----------------------------------------------------

        if incoming_offer == previous_offer:

            return self._round_price(
                incoming_offer
            )

        # -----------------------------------------------------
        # Buyer is already above seller's previous offer.
        # Matching the buyer exactly creates an agreement.
        # -----------------------------------------------------

        if incoming_offer > previous_offer:

            return self._round_price(
                incoming_offer
            )

        # -----------------------------------------------------
        # Seller must move DOWN.
        # -----------------------------------------------------

        counter = (
            previous_offer +
            incoming_offer
        ) / 2

        counter = self._round_price(counter)

        # -----------------------------------------------------
        # Guarantee downward movement if rounding
        # would otherwise keep the same price.
        # -----------------------------------------------------

        if counter >= previous_offer:

            counter = (
                previous_offer - 1000
            )

        # -----------------------------------------------------
        # Never go below buyer's current offer.
        #
        # If it reaches buyer exactly, that creates an
        # exact-match agreement in the runner.
        # -----------------------------------------------------

        if counter <= incoming_offer:

            counter = incoming_offer

        # -----------------------------------------------------
        # Seller minimum
        # -----------------------------------------------------

        counter = max(
            counter,
            self.minimum_price
        )

        # Seller must not increase.
        counter = min(
            counter,
            previous_offer
        )

        return self._round_price(counter)

    # =========================================================
    # ROUND PRICE
    # =========================================================

    def _round_price(
        self,
        price
    ):
        """
        Negotiation uses ₹1,000 precision.
        """

        return float(
            round(
                float(price) / 1000
            ) * 1000
        )