from typing import List, Dict, Any
import re


class DeadlockDetector:
    """
    Detects a genuinely stalled negotiation.

    Important:
    - Does NOT decide prices.
    - Does NOT modify Buyer/Seller offers.
    - CounterofferEvaluator remains responsible for prices.
    - Only observes negotiation history.

    Deadlock is detected when BOTH agents have stopped
    making meaningful progress for the configured number
    of consecutive rounds.

    Repeating a price once or twice does NOT automatically
    mean deadlock.
    """

    def __init__(
        self,
        stall_rounds: int = 3,
        minimum_price_change: float = 1000.0
    ):
        self.stall_rounds = max(1, int(stall_rounds))
        self.minimum_price_change = float(
            minimum_price_change
        )

        # Prevent repeated resolution attempts.
        self.resolution_attempted = False

    # =========================================================
    # CHECK DEADLOCK
    # =========================================================

    def check_deadlock(
        self,
        history: List[Dict[str, Any]],
        current_round: int,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Check whether the negotiation is genuinely stalled.

        Rules:
        1. Finished negotiations cannot be deadlocked.
        2. One repeated price is not enough.
        3. Each agent is checked separately.
        4. Both agents must be stalled.
        5. Exact agreement is handled by the negotiation runner.
        """

        if str(status).lower() != "active":
            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason="Negotiation is no longer active."
            )

        if not history:
            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason="No negotiation history available."
            )

        offer_entries = self._extract_offer_entries(history)

        if len(offer_entries) < 2:
            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason="Not enough offers to detect deadlock."
            )

        # Check each agent separately.
        buyer_stalled = self._agent_stalled_rounds(
            offer_entries,
            "buyer"
        )

        seller_stalled = self._agent_stalled_rounds(
            offer_entries,
            "seller"
        )

        # Deadlock requires BOTH agents to be stuck.
        stalled_rounds = min(
            buyer_stalled,
            seller_stalled
        )

        # -----------------------------------------------------
        # Negotiation is still progressing.
        # -----------------------------------------------------

        if (
            buyer_stalled < self.stall_rounds
            or seller_stalled < self.stall_rounds
        ):
            return self._build_result(
                deadlock=False,
                stalled_rounds=stalled_rounds,
                action="CONTINUE",
                reason=(
                    "Negotiation is still progressing. "
                    f"Buyer stalled rounds: {buyer_stalled}; "
                    f"Seller stalled rounds: {seller_stalled}."
                )
            )

        # -----------------------------------------------------
        # First detection → resolution attempt.
        # -----------------------------------------------------

        if not self.resolution_attempted:

            self.resolution_attempted = True

            return self._build_result(
                deadlock=True,
                stalled_rounds=stalled_rounds,
                action="RESOLUTION_ATTEMPT",
                reason=(
                    "Both Buyer and Seller have stopped "
                    "making meaningful price progress for "
                    f"{stalled_rounds} consecutive rounds."
                )
            )

        # -----------------------------------------------------
        # Still stalled after resolution attempt.
        # -----------------------------------------------------

        return self._build_result(
            deadlock=True,
            stalled_rounds=stalled_rounds,
            action="BREAKDOWN",
            reason=(
                "Both parties remained stalled after "
                "the resolution attempt."
            )
        )

    # =========================================================
    # EXTRACT OFFERS
    # =========================================================

    def _extract_offer_entries(
        self,
        history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract numeric offers from negotiation history.
        """

        entries = []

        for entry in history:

            if not isinstance(entry, dict):
                continue

            offer = entry.get("offer")

            # If offer is not explicitly stored,
            # extract it from the message.
            if offer is None:

                message = entry.get(
                    "message",
                    ""
                )

                offer = self._extract_offer_from_message(
                    message
                )

            if offer is None:
                continue

            try:
                offer = float(offer)

            except (
                TypeError,
                ValueError
            ):
                continue

            entries.append(
                {
                    "round": entry.get("round"),
                    "agent": entry.get("agent"),
                    "offer": offer
                }
            )

        return entries

    # =========================================================
    # EXTRACT PRICE FROM MESSAGE
    # =========================================================

    def _extract_offer_from_message(
        self,
        message
    ):
        """
        Supports:

            ₹54.00 lakhs
            ₹65.50 lakhs
            ₹5400000
            ₹2 crore
        """

        if message is None:
            return None

        text = str(message)

        # -----------------------------------------------------
        # Lakhs
        # -----------------------------------------------------

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

            try:
                return float(value) * 100000

            except ValueError:
                return None

        # -----------------------------------------------------
        # Crores
        # -----------------------------------------------------

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

            try:
                return float(value) * 10000000

            except ValueError:
                return None

        # -----------------------------------------------------
        # Direct rupee amount
        # -----------------------------------------------------

        match = re.search(
            r'₹\s*([\d,]+(?:\.\d+)?)',
            text
        )

        if match:

            value = (
                match.group(1)
                .replace(",", "")
            )

            try:
                return float(value)

            except ValueError:
                return None

        return None

    # =========================================================
    # AGENT-SPECIFIC STALL CHECK
    # =========================================================

    def _agent_stalled_rounds(
        self,
        offer_entries: List[Dict[str, Any]],
        agent_type: str
    ) -> int:
        """
        Count consecutive stalled offers for ONE agent.

        Buyer offers are compared only with previous
        Buyer offers.

        Seller offers are compared only with previous
        Seller offers.

        This is important because Buyer and Seller naturally
        move in opposite directions.
        """

        agent_entries = []

        for entry in offer_entries:

            agent = str(
                entry.get("agent", "")
            ).lower()

            if agent_type == "buyer":

                if "buyer" in agent:
                    agent_entries.append(entry)

            elif agent_type == "seller":

                if "seller" in agent:
                    agent_entries.append(entry)

        if len(agent_entries) < 2:
            return 0

        stalled = 0

        # Start from the latest offer and move backwards.
        for index in range(
            len(agent_entries) - 1,
            0,
            -1
        ):

            current_offer = (
                agent_entries[index]["offer"]
            )

            previous_offer = (
                agent_entries[index - 1]["offer"]
            )

            difference = abs(
                current_offer -
                previous_offer
            )

            # Same or very small movement.
            if difference < self.minimum_price_change:

                stalled += 1

            else:

                # Meaningful movement found.
                break

            if stalled >= self.stall_rounds:
                break

        return stalled

    # =========================================================
    # BUILD RESULT
    # =========================================================

    def _build_result(
        self,
        deadlock: bool,
        stalled_rounds: int,
        action: str,
        reason: str
    ) -> Dict[str, Any]:

        return {
            "deadlock": deadlock,
            "stalled_rounds": stalled_rounds,
            "threshold": self.stall_rounds,
            "action": action,
            "reason": reason
        }

    # =========================================================
    # SIMPLE BOOLEAN CHECK
    # =========================================================

    def is_deadlocked(
        self,
        history: List[Dict[str, Any]],
        status: str = "active"
    ) -> bool:
        """
        Simple True/False deadlock check.
        """

        result = self.check_deadlock(
            history=history,
            current_round=0,
            status=status
        )

        return result["deadlock"]