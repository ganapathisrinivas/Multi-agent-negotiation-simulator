import re


class CounterofferEvaluator:
    """
    Evaluates an incoming offer using the agent's private
    negotiation objectives.

    The private target/minimum/maximum values are NEVER
    displayed to the user.
    """

    def __init__(
        self,
        role,
        target_price,
        minimum_price,
        maximum_price
    ):
        self.role = role.lower()
        self.target_price = target_price
        self.minimum_price = minimum_price
        self.maximum_price = maximum_price

        self.previous_offer = None
        self.concession_count = 0

    # =========================================================
    # EXTRACT PRICE
    # =========================================================

    def extract_price(self, text):

        if not text:
            return None

        text = text.lower().replace(",", "")

        # -----------------------------------------------------
        # Explicit lakh format
        # Examples:
        # 50 lakhs
        # 50 lakh
        # ₹50 lakhs
        # rs 50 lakhs
        # -----------------------------------------------------

        lakh_match = re.search(
            r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*lakh[s]?",
            text
        )

        if lakh_match:

            value = float(lakh_match.group(1))

            return value * 100000

        # -----------------------------------------------------
        # Rupee amount
        # Example:
        # ₹5000000
        # -----------------------------------------------------

        rupee_match = re.search(
            r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)",
            text
        )

        if rupee_match:

            value = float(rupee_match.group(1))

            # If the value is small, treat it as lakhs.
            if value < 1000:
                return value * 100000

            return value

        # -----------------------------------------------------
        # Plain large number
        # Example:
        # 5000000
        # -----------------------------------------------------

        large_number_match = re.search(
            r"\b(\d{6,9})\b",
            text
        )

        if large_number_match:

            return float(
                large_number_match.group(1)
            )

        # -----------------------------------------------------
        # Plain number
        #
        # Examples:
        # 50
        # 55
        # 58
        # final is 58
        # my offer is 55
        # -----------------------------------------------------

        numbers = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            text
        )

        if numbers:

            value = float(numbers[-1])

            # Negotiation is in lakhs.
            if value < 1000:

                return value * 100000

        return None

    # =========================================================
    # EVALUATE OFFER
    # =========================================================

    def evaluate(self, incoming_message):

        offer_price = self.extract_price(
            incoming_message
        )

        # -----------------------------------------------------
        # No price found
        # -----------------------------------------------------

        if offer_price is None:

            return {
                "decision": "COUNTER",
                "offer_price": None,
                "counter_price": None,
                "reason": "No clear monetary offer was detected."
            }

        # =====================================================
        # SELLER
        # =====================================================

        if self.role == "seller":

            # -------------------------------------------------
            # ACCEPT
            # Buyer meets or exceeds seller target
            # -------------------------------------------------

            if offer_price >= self.target_price:

                self.previous_offer = offer_price

                return {
                    "decision": "ACCEPT",
                    "offer_price": offer_price,
                    "counter_price": None,
                    "reason": "Offer meets the seller's acceptable objective."
                }

            # -------------------------------------------------
            # COUNTER
            # Buyer is below minimum
            # -------------------------------------------------

            if offer_price < self.minimum_price:

                counter_price = self.calculate_seller_counter(
                    offer_price
                )

                self.previous_offer = counter_price
                self.concession_count += 1

                return {
                    "decision": "COUNTER",
                    "offer_price": offer_price,
                    "counter_price": counter_price,
                    "reason": "Offer is below the seller's acceptable range."
                }

            # -------------------------------------------------
            # COUNTER
            # Offer is between minimum and target
            # -------------------------------------------------

            counter_price = self.calculate_seller_counter(
                offer_price
            )

            self.previous_offer = counter_price
            self.concession_count += 1

            return {
                "decision": "COUNTER",
                "offer_price": offer_price,
                "counter_price": counter_price,
                "reason": "Offer is negotiable but below the seller's target."
            }

        # =====================================================
        # BUYER
        # =====================================================

        else:

            # -------------------------------------------------
            # ACCEPT
            # Seller price is at or below buyer target
            # -------------------------------------------------

            if offer_price <= self.target_price:

                self.previous_offer = offer_price

                return {
                    "decision": "ACCEPT",
                    "offer_price": offer_price,
                    "counter_price": None,
                    "reason": "Offer is within the buyer's target."
                }

            # -------------------------------------------------
            # COUNTER
            # Seller price exceeds maximum
            # -------------------------------------------------

            if offer_price > self.maximum_price:

                counter_price = self.calculate_buyer_counter(
                    offer_price
                )

                self.previous_offer = counter_price
                self.concession_count += 1

                return {
                    "decision": "COUNTER",
                    "offer_price": offer_price,
                    "counter_price": counter_price,
                    "reason": "Offer exceeds the buyer's maximum budget."
                }

            # -------------------------------------------------
            # COUNTER
            # Seller price is between target and maximum
            # -------------------------------------------------

            counter_price = self.calculate_buyer_counter(
                offer_price
            )

            self.previous_offer = counter_price
            self.concession_count += 1

            return {
                "decision": "COUNTER",
                "offer_price": offer_price,
                "counter_price": counter_price,
                "reason": "Offer is negotiable but above the buyer's target."
            }

    # =========================================================
    # SELLER CONCESSION
    # =========================================================

    def calculate_seller_counter(self, buyer_offer):

        if self.previous_offer is None:

            current_position = self.target_price

        else:

            current_position = self.previous_offer

        # Move 25% toward buyer's offer
        counter = current_position - (
            (current_position - buyer_offer) * 0.25
        )

        # Never go below seller minimum
        counter = max(
            counter,
            self.minimum_price
        )

        # Round to nearest ₹50,000
        counter = round(
            counter / 50000
        ) * 50000

        return int(counter)

    # =========================================================
    # BUYER CONCESSION
    # =========================================================

    def calculate_buyer_counter(self, seller_offer):

        if self.previous_offer is None:

            current_position = self.target_price

        else:

            current_position = self.previous_offer

        # Move 25% toward seller's offer
        counter = current_position + (
            (seller_offer - current_position) * 0.25
        )

        # Never exceed buyer maximum
        counter = min(
            counter,
            self.maximum_price
        )

        # Round to nearest ₹50,000
        counter = round(
            counter / 50000
        ) * 50000

        return int(counter)