import json

from google import genai
from google.genai import types

from backend.config.settings import settings


class GeminiService:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )
        self.model = settings.gemini_model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return response.text

    def generate_negotiation_decision(
        self,
        agent: dict,
        current_offer: float,
        opponent_offer: float,
        constraints: dict,
        round_number: int,
    ) -> dict:

        prompt = f"""
You are an AI negotiation agent participating in a real-estate negotiation.

AGENT:
Name: {agent["name"]}
Role: {agent["role"]}
Goal: {agent["goal"]}
Personality: {agent["personality"]}

NEGOTIATION:
Round: {round_number}
Agent's current offer: {current_offer}
Opponent's offer: {opponent_offer}

CONSTRAINTS:
{json.dumps(constraints, indent=2)}

Your task is to decide the agent's next negotiation action.

Possible decisions:
- counter_offer
- accept
- reject

Rules:
1. Respect the agent's goal and personality.
2. Never violate the provided constraints.
3. Consider the opponent's latest offer.
4. Make a realistic negotiation decision.
5. Return ONLY valid JSON.
6. Do not include markdown.
7. The JSON must contain exactly these fields:

{{
    "decision": "counter_offer",
    "offer": 450000,
    "reasoning": "Short explanation of the decision."
}}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        try:
            result = json.loads(response.text)

            return {
                "decision": result["decision"],
                "offer": float(result["offer"]),
                "reasoning": result["reasoning"],
            }

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid Gemini negotiation response: {response.text}"
            ) from exc


gemini_service = GeminiService()