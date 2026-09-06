import json
from fastapi.testclient import TestClient

from main import app
from agents.practice_agent import extract_offer_from_message

client = TestClient(app)


# =========================================================================
# 1. UNIT TESTS: AUTOMATIC OFFER EXTRACTION (INDIAN CURRENCY FORMATS)
# =========================================================================

def test_extract_offer_from_message():
    test_cases = [
        # User prompt exact test cases
        ("I will give 25 lakhs for this property", 2500000.0),
        ("I will give 25 lakhs", 2500000.0),
        ("I can offer 2500000", 2500000.0),
        ("I will give 2500000 for this property", 2500000.0),
        ("I offer 25,00,000", 2500000.0),
        ("I can offer 50 lakh", 5000000.0),
        ("The price is too high. Can you reduce it?", None),
        ("The price is too high", None),
        ("I offer 50 lakhs", 5000000.0),
        ("I can give 75 lakh", 7500000.0),
        ("My offer is 1 crore", 10000000.0),
        ("I can pay 2.5 crore", 25000000.0),
        ("I offer 5000000", 5000000.0),
        ("I can give 50,00,000", 5000000.0),
        ("I am interested in this property", None),
        ("My final offer is 1 crore", 10000000.0),
        ("I am willing to pay 45 lakhs", 4500000.0),
        ("I offer 75 lacs", 7500000.0),
        ("My offer is 1.5 lac", 150000.0),
        ("₹50 Lakhs", 5000000.0),
        ("Rs. 50,00,000", 5000000.0),
        ("INR 75,00,000", 7500000.0),
        ("I can do 65L", 6500000.0),
        ("I can pay 2 cr", 20000000.0),
        ("What is your best price?", None),
        ("Room 101 in scenario 2", None),
        ("", None),
        (None, None)
    ]

    for msg, expected in test_cases:
        result = extract_offer_from_message(msg)
        assert result == expected, f"Failed on '{msg}': expected {expected}, got {result}"
        print(f"PASS: '{msg}' -> {result}")


# =========================================================================
# 2. UI ENDPOINT TEST
# =========================================================================

def test_practice_ui_endpoint():
    r = client.get("/practice")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    html = r.text
    # Verify presence of single text input and send button
    assert 'id="human-message-input"' in html
    assert 'id="send-button"' in html
    assert 'id="chat-messages"' in html
    print("PASS: /practice HTML UI endpoint rendered correctly.")


# =========================================================================
# 3. END-TO-END TESTS: SINGLE MESSAGE PRACTICE FLOW & STATE UPDATES
# =========================================================================

def test_single_message_negotiation_flow():
    # 1. Health check
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    # 2. Start negotiation session
    start_payload = {
        "scenario": 2,
        "property_index": 0,
        "human_role": "buyer",
        "ai_personality": "collaborative",
        "max_rounds": 5
    }
    r = client.post("/negotiations/practice", json=start_payload)
    assert r.status_code == 200
    session_data = r.json()
    neg_id = session_data["negotiation_id"]
    assert session_data["status"] == "active"
    assert session_data["human_role"] == "buyer"
    assert session_data["ai_role"] == "seller"
    assert "ai_message" in session_data

    # Verify initial state before any messages
    state_before = client.get(f"/negotiations/{neg_id}").json()
    assert state_before["round"] == 1
    assert state_before["last_human_offer"] is None

    # 3. Round 1: Send single message "I will give 2500000 for this property"
    # ONLY single message input, NO separate offer field
    msg_payload = {
        "message": "I will give 2500000 for this property"
    }
    r = client.post(f"/negotiations/{neg_id}/message", json=msg_payload)
    assert r.status_code == 200
    resp_1 = r.json()
    print("\nRound 1 response:", json.dumps(resp_1, indent=2))

    assert resp_1["round"] == 1
    assert resp_1["human_message"] == "I will give 2500000 for this property"
    assert resp_1["detected_offer"] == 2500000.0
    assert resp_1["ai_response"]["decision"] in ["COUNTER", "ACCEPT", "REJECT"]
    assert resp_1["ai_response"]["counter_offer"] is not None

    # Verify state updated ONLY after sending message
    state_after_1 = client.get(f"/negotiations/{neg_id}").json()
    assert state_after_1["last_human_offer"] == 2500000.0
    assert state_after_1["round"] == 2

    # 4. Round 2: Non-offer dialogue message "The price is too high. Can you reduce it?"
    non_offer_payload = {
        "message": "The price is too high. Can you reduce it?"
    }
    r = client.post(f"/negotiations/{neg_id}/message", json=non_offer_payload)
    assert r.status_code == 200
    resp_2 = r.json()
    print("\nRound 2 response (Non-offer):", json.dumps(resp_2, indent=2))

    assert resp_2["detected_offer"] is None
    assert resp_2["ai_response"]["decision"] == "COUNTER"
    assert resp_2["ai_response"]["counter_offer"] is not None

    # 5. Round 3: Counter with 25 lakhs format
    counter_payload = {
        "message": "I will give 25 lakhs for this property"
    }
    r = client.post(f"/negotiations/{neg_id}/message", json=counter_payload)
    assert r.status_code == 200
    resp_3 = r.json()
    assert resp_3["detected_offer"] == 2500000.0

    # 6. Verify History format contains detected offer
    r = client.get(f"/negotiations/{neg_id}/history")
    assert r.status_code == 200
    hist = r.json()
    assert hist["total_messages"] >= 6
    human_entries = [m for m in hist["history"] if m.get("sender") == "human_buyer"]
    assert human_entries[0]["offer"] == 2500000.0
    assert human_entries[1]["offer"] is None
    assert human_entries[2]["offer"] == 2500000.0


# =========================================================================
# 4. PERSONALITY TESTS: AGGRESSIVE vs COLLABORATIVE vs RISK-AVERSE
# =========================================================================

def test_personalities_behavior_difference():
    human_msg = {"message": "I will give 2500000 for this property"}
    personalities = ["aggressive", "collaborative", "risk_averse"]
    responses = {}

    for personality in personalities:
        start_payload = {
            "scenario": 2,
            "property_index": 0,
            "human_role": "buyer",
            "ai_personality": personality,
            "max_rounds": 5
        }
        r = client.post("/negotiations/practice", json=start_payload)
        assert r.status_code == 200
        neg_id = r.json()["negotiation_id"]

        r = client.post(f"/negotiations/{neg_id}/message", json=human_msg)
        assert r.status_code == 200
        resp = r.json()
        assert resp["detected_offer"] == 2500000.0
        responses[personality] = resp

    print("\n=== PERSONALITY COMPARISON ===")
    for p, resp in responses.items():
        print(f"\n--- Personality: {p.upper()} ---")
        print(f"Decision: {resp['ai_response']['decision']}")
        print(f"Counter Offer: {resp['ai_response']['counter_offer']}")
        print(f"Message: {resp['ai_response']['message']}")
        print(f"Reason: {resp['ai_response']['reason']}")

    agg_decision = responses["aggressive"]["ai_response"]["decision"]
    collab_decision = responses["collaborative"]["ai_response"]["decision"]
    risk_decision = responses["risk_averse"]["ai_response"]["decision"]
    assert agg_decision in ["REJECT", "COUNTER"]
    assert collab_decision in ["COUNTER", "ACCEPT"]
    assert risk_decision in ["COUNTER", "REJECT", "ACCEPT"]


if __name__ == "__main__":
    print("Running Offer Extraction Tests...")
    test_extract_offer_from_message()
    print("\nRunning UI Endpoint Tests...")
    test_practice_ui_endpoint()
    print("\nRunning Single Message Negotiation Flow Tests...")
    test_single_message_negotiation_flow()
    print("\nRunning Personality Difference Tests...")
    test_personalities_behavior_difference()
    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
