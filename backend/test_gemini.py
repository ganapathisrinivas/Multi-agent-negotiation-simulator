from backend.services.gemini_service import gemini_service


response = gemini_service.generate(
    "Explain what a buyer agent does in a real estate negotiation in one sentence."
)

print("\nGemini response:")
print(response)