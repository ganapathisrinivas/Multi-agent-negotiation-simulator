import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("=== 1. Health Check ===")
    r = requests.get(f"{BASE_URL}/health")
    print("Health:", r.status_code, r.json())
    assert r.status_code == 200

    print("\n=== 2. Start Practice Mode (Human Buyer vs AI Seller) ===")
    req_data = {
        "scenario": 2,
        "property_index": 0,
        "human_role": "buyer",
        "ai_personality": "collaborative",
        "max_rounds": 5
    }
    r = requests.post(f"{BASE_URL}/negotiations/practice", json=req_data)
    print("Start status:", r.status_code)
    start_resp = r.json()
    print("Response:", json.dumps(start_resp, indent=2))
    assert r.status_code == 200
    neg_id = start_resp["negotiation_id"]
    assert start_resp["status"] == "active"
    assert start_resp["human_role"] == "buyer"
    assert start_resp["ai_role"] == "seller"

    print("\n=== 3. Human Round 1: Offer ₹160 Lakhs ===")
    msg_req = {"message": "I offer ₹160 Lakhs for this property"}
    r = requests.post(f"{BASE_URL}/negotiations/{neg_id}/message", json=msg_req)
    print("Round 1 status:", r.status_code)
    r1 = r.json()
    print("Round 1 response:", json.dumps(r1, indent=2))
    assert r.status_code == 200
    assert r1["human_offer"] == 16000000.0
    assert r1["ai_response"]["decision"] in ["COUNTER", "ACCEPT", "REJECT"]

    print("\n=== 4. Human Round 2: Counter with ₹180 Lakhs ===")
    msg_req = {"message": "I can increase my offer to 18000000", "offer": 18000000}
    r = requests.post(f"{BASE_URL}/negotiations/{neg_id}/message", json=msg_req)
    print("Round 2 status:", r.status_code)
    r2 = r.json()
    print("Round 2 response:", json.dumps(r2, indent=2))
    assert r.status_code == 200

    print("\n=== 5. Human Round 3: Accept AI counter ===")
    ai_counter = r2["ai_response"]["counter_offer"]
    msg_req = {"message": f"I accept your offer of {ai_counter}"}
    r = requests.post(f"{BASE_URL}/negotiations/{neg_id}/message", json=msg_req)
    print("Round 3 status:", r.status_code)
    r3 = r.json()
    print("Round 3 response:", json.dumps(r3, indent=2))
    assert r.status_code == 200
    assert r3["status"] == "accepted"

    print("\n=== 6. Get State ===")
    r = requests.get(f"{BASE_URL}/negotiations/{neg_id}")
    print("Get state status:", r.status_code)
    state = r.json()
    print("State agreed_price:", state.get("agreed_price"), "Status:", state.get("status"))
    assert state["status"] == "accepted"

    print("\n=== 7. Get History ===")
    r = requests.get(f"{BASE_URL}/negotiations/{neg_id}/history")
    print("Get history status:", r.status_code)
    hist = r.json()
    print("History count:", hist["total_messages"])
    assert hist["total_messages"] >= 4

    print("\n=== 8. Test Reverse Role (Human Seller vs AI Buyer, Aggressive) ===")
    req_data2 = {
        "scenario": 1,
        "property_index": 1,
        "human_role": "seller",
        "ai_personality": "aggressive",
        "max_rounds": 5
    }
    r = requests.post(f"{BASE_URL}/negotiations/practice", json=req_data2)
    print("Start reverse status:", r.status_code)
    s2 = r.json()
    print("Reverse start:", json.dumps(s2, indent=2))
    assert s2["human_role"] == "seller"
    assert s2["ai_role"] == "buyer"
    neg_id2 = s2["negotiation_id"]

    msg_req = {"message": "My asking price is ₹50 Lakhs", "offer": 5000000}
    r = requests.post(f"{BASE_URL}/negotiations/{neg_id2}/message", json=msg_req)
    print("Reverse round 1:", json.dumps(r.json(), indent=2))
    assert r.status_code == 200

    print("\n=== 9. Test Cancel Endpoint ===")
    r = requests.post(f"{BASE_URL}/negotiations/{neg_id2}/cancel")
    print("Cancel response:", r.json())
    assert r.json()["status"] == "cancelled"

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_all()
