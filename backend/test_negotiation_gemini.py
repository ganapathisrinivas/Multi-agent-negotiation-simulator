from backend.services.gemini_service import gemini_service


buyer = {
    "name": "Buyer Agent",
    "role": "Buyer Representative",
    "goal": "Get the best possible property price",
    "personality": "collaborative",
}

constraints = {
    "maximum_budget": 500000,
    "property_price": 480000,
}


result = gemini_service.generate_negotiation_decision(
    agent=buyer,
    current_offer=450000,
    opponent_offer=470000,
    constraints=constraints,
    round_number=3,
)

print("\nGemini Negotiation Decision:")
print(result)