# agents/counteroffer_evaluator.py

import re


class CounterofferEvaluator:
    """
    Evaluates the incoming negotiation offer.

    Buyer:
        - Accepts when seller price is at/below target.
        - Otherwise makes a higher counteroffer.

    Seller:
        - Accepts when buyer price is at/above target.
        - Otherwise makes a lower counteroffer.

    The evaluator also remembers the previous counteroffer so
    the negotiation continues moving instead of repeating
    the same amount.
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

        self.previous_offer = None
        self.concession_count = 0

    # =====================================================
    # EXTRACT PRICE
    # =====================================================

    def extract_price(self, text):

        if not text:
            return None

        text = text.replace(",", "")

        # -------------------------------------------------
        # 1. Explicit counteroffer
        # -------------------------------------------------

        patterns = [
            r"COUNTEROFFER\s*:\s*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"counter\s*offer\s*(?:is|of)?\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"counteroffer\s*(?:is|of)?\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"our\s+counteroffer\s+is\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"counteroffer\s*[:\-]?\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                return (
                    float(match.group(1))
                    * 100000
                )

        # -------------------------------------------------
        # 2. Accepted offer
        # -------------------------------------------------

        accepted_patterns = [

            r"ACCEPTED OFFER\s*:\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"accept\s+(?:your\s+)?offer\s+of\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)",

            r"accept(?:ed)?\s*[:\-]?\s*₹?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)"
        ]

        for pattern in accepted_patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                return (
                    float(match.group(1))
                    * 100000
                )

        # -------------------------------------------------
        # 3. Rupee + lakhs
        # -------------------------------------------------

        lakh_pattern = re.search(
            r"(?:₹|Rs\.?|INR)?\s*"
            r"(\d+(?:\.\d+)?)\s*"
            r"(?:lakhs?|lacs?)",
            text,
            re.IGNORECASE
        )

        if lakh_pattern:

            return (
                float(lakh_pattern.group(1))
                * 100000
            )

        # -------------------------------------------------
        # 4. Rupee amount
        # -------------------------------------------------

        rupee_pattern = re.search(
            r"(?:₹|Rs\.?|INR)\s*"
            r"(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )

        if rupee_pattern:

            value = float(
                rupee_pattern.group(1)
            )

            if value < 1000:
                return value * 100000

            return value

        # -------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT extract random numbers from the message.
        #
        # For example:
        # "1 RK"
        # "500 square feet"
        # "6th floor"
        #
        # must NOT become a property price.
        # -------------------------------------------------

        return None

    # =====================================================
    # EVALUATE
    # =====================================================

    def evaluate(
        self,
        incoming_message
    ):

        offer_price = self.extract_price(
            incoming_message
        )

        # -------------------------------------------------
        # No price detected
        # -------------------------------------------------

        if offer_price is None:

            return {
                "decision": "COUNTER",
                "offer_price": None,
                "counter_price": self._fallback_counter(),
                "reason": (
                    "No clear monetary offer "
                    "was detected."
                )
            }

        # =================================================
        # SELLER
        # =================================================

        if self.role == "seller":

            # ---------------------------------------------
            # Accept
            # ---------------------------------------------

            if offer_price >= self.target_price:

                self.previous_offer = (
                    offer_price
                )

                return {
                    "decision": "ACCEPT",
                    "offer_price": offer_price,
                    "counter_price": None,
                    "reason": (
                        "Offer meets the "
                        "seller's target."
                    )
                }

            # ---------------------------------------------
            # Counter
            # ---------------------------------------------

            counter_price = (
                self.calculate_seller_counter(
                    offer_price
                )
            )

            self.previous_offer = (
                counter_price
            )

            self.concession_count += 1

            return {
                "decision": "COUNTER",
                "offer_price": offer_price,
                "counter_price": counter_price,
                "reason": (
                    "Offer is below the "
                    "seller's target."
                )
            }

        # =================================================
        # BUYER
        # =================================================

        else:

            # ---------------------------------------------
            # Accept
            # ---------------------------------------------

            if offer_price <= self.target_price:

                self.previous_offer = (
                    offer_price
                )

                return {
                    "decision": "ACCEPT",
                    "offer_price": offer_price,
                    "counter_price": None,
                    "reason": (
                        "Offer is within the "
                        "buyer's target."
                    )
                }

            # ---------------------------------------------
            # Counter
            # ---------------------------------------------

            counter_price = (
                self.calculate_buyer_counter(
                    offer_price
                )
            )

            self.previous_offer = (
                counter_price
            )

            self.concession_count += 1

            return {
                "decision": "COUNTER",
                "offer_price": offer_price,
                "counter_price": counter_price,
                "reason": (
                    "Offer is above the "
                    "buyer's target."
                )
            }

    # =====================================================
    # SELLER COUNTER
    # =====================================================

    def calculate_seller_counter(
        self,
        buyer_offer
    ):

        if self.previous_offer is None:

            current_position = (
                self.target_price
            )

        else:

            current_position = (
                self.previous_offer
            )

        # Move 20% toward buyer offer.
        counter = (
            current_position
            - (
                (
                    current_position
                    - buyer_offer
                )
                * 0.20
            )
        )

        # Never go below seller minimum.
        counter = max(
            counter,
            self.minimum_price
        )

        # Never go above seller maximum.
        counter = min(
            counter,
            self.maximum_price
        )

        # Round to nearest ₹50,000.
        counter = (
            round(
                counter / 50000
            )
            * 50000
        )

        return int(counter)

    # =====================================================
    # BUYER COUNTER
    # =====================================================

    def calculate_buyer_counter(
        self,
        seller_offer
    ):

        if self.previous_offer is None:

            current_position = (
                self.target_price
            )

        else:

            current_position = (
                self.previous_offer
            )

        # Move 20% toward seller offer.
        counter = (
            current_position
            + (
                (
                    seller_offer
                    - current_position
                )
                * 0.20
            )
        )

        # Never go below buyer minimum.
        counter = max(
            counter,
            self.minimum_price
        )

        # Never exceed buyer maximum.
        counter = min(
            counter,
            self.maximum_price
        )

        # Round to nearest ₹50,000.
        counter = (
            round(
                counter / 50000
            )
            * 50000
        )

        return int(counter)

    # =====================================================
    # FALLBACK COUNTER
    # =====================================================

    def _fallback_counter(self):

        if self.previous_offer is not None:

            return int(
                self.previous_offer
            )

        return int(
            self.target_price
        )