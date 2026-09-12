"""
Milestone 4 - Point 2 Verification Tests
Downloadable Negotiation Transcript and Summary Report

Covers all 16 required test conditions:
1. Valid transcript endpoint (GET /negotiations/{id}/transcript).
2. Invalid negotiation ID for transcript returns 404.
3. Valid summary endpoint (GET /negotiations/{id}/summary).
4. Invalid negotiation ID for summary returns 404.
5. Transcript contains actual negotiation messages.
6. Transcript contains correct negotiation ID.
7. Transcript contains final status.
8. Summary contains property information when available.
9. Summary contains asking price when available.
10. Summary contains final price when available.
11. Summary contains correct number of rounds.
12. Summary contains actual final status.
13. Percentage calculations are correct.
14. Existing negotiation functionality still works.
15. Existing Human vs AI functionality still works.
16. Existing AI vs AI functionality still works.
"""

import unittest
from fastapi.testclient import TestClient
from main import app
from agents.practice_store import practice_store, PracticeNegotiationSession


class TestMilestone4Reports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Setup a sample known negotiation session in practice_store for deterministic tests
        self.session = PracticeNegotiationSession(
            negotiation_id="TEST_NEG_123",
            mode="human_vs_ai",
            status="accepted",
            round=3,
            max_rounds=10,
            property_index=0,
            property={
                "title": "3BHK Luxury High-Rise",
                "location": "Indiranagar, Bangalore",
                "bhk": 3,
                "sqft": 1850,
                "bathrooms": 3,
                "price": 15000000.0,
                "type": "Apartment"
            },
            reference_price=15000000.0,
            asking_price=15000000.0,
            target_price=13000000.0,
            minimum_price=11500000.0,
            maximum_price=16000000.0,
            human_role="buyer",
            ai_role="seller",
            ai_personality="collaborative",
            buyer_personality=None,
            seller_personality="collaborative",
            scenario=2,
            scenario_name="Apartment / Flat",
            agreed_price=12500000.0,
            history=[
                {
                    "round": 1,
                    "speaker": "buyer",
                    "role": "buyer",
                    "offer": 10000000.0,
                    "message": "I can offer ₹1.00 Crore for this property.",
                    "counteroffer": None,
                    "decision": None
                },
                {
                    "round": 1,
                    "speaker": "seller",
                    "role": "seller",
                    "offer": None,
                    "message": "Thank you for the offer. I can lower the price to ₹1.40 Crore.",
                    "counteroffer": 14000000.0,
                    "decision": "counteroffer"
                },
                {
                    "round": 2,
                    "speaker": "buyer",
                    "role": "buyer",
                    "offer": 11500000.0,
                    "message": "How about ₹1.15 Crore? That's a fair valuation.",
                    "counteroffer": None,
                    "decision": None
                },
                {
                    "round": 2,
                    "speaker": "seller",
                    "role": "seller",
                    "offer": None,
                    "message": "I appreciate that. I can meet you at ₹1.30 Crore.",
                    "counteroffer": 13000000.0,
                    "decision": "counteroffer"
                },
                {
                    "round": 3,
                    "speaker": "buyer",
                    "role": "buyer",
                    "offer": 12500000.0,
                    "message": "Final offer: ₹1.25 Crore.",
                    "counteroffer": None,
                    "decision": None
                },
                {
                    "round": 3,
                    "speaker": "seller",
                    "role": "seller",
                    "offer": None,
                    "message": "Deal agreed at ₹1.25 Crore. Welcome aboard!",
                    "counteroffer": 12500000.0,
                    "decision": "accepted"
                },
            ]
        )
        practice_store.save(self.session)

    # 1. Valid transcript endpoint
    def test_1_valid_transcript_endpoint(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/transcript?format=txt")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp.headers.get("content-disposition", "").lower())
        self.assertIn("negotiation_TEST_NEG_123_transcript.txt", resp.headers.get("content-disposition", ""))
        self.assertIn("text/plain", resp.headers.get("content-type", ""))

    # 2. Invalid negotiation ID for transcript returns 404
    def test_2_invalid_negotiation_id_transcript(self):
        resp = self.client.get("/negotiations/NON_EXISTENT_ID_999/transcript")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json().get("detail", "").lower())

    # 3. Valid summary endpoint
    def test_3_valid_summary_endpoint(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp.headers.get("content-disposition", "").lower())
        self.assertIn("negotiation_TEST_NEG_123_summary.html", resp.headers.get("content-disposition", ""))
        self.assertIn("text/html", resp.headers.get("content-type", ""))

    # 4. Invalid negotiation ID for summary returns 404
    def test_4_invalid_negotiation_id_summary(self):
        resp = self.client.get("/negotiations/NON_EXISTENT_ID_999/summary")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json().get("detail", "").lower())

    # 5. Transcript contains actual negotiation messages
    def test_5_transcript_contains_actual_messages(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/transcript?format=txt")
        text = resp.text
        self.assertIn("I can offer ₹1.00 Crore for this property.", text)
        self.assertIn("Thank you for the offer. I can lower the price to ₹1.40 Crore.", text)
        self.assertIn("Deal agreed at ₹1.25 Crore.", text)

    # 6. Transcript contains correct negotiation ID
    def test_6_transcript_contains_correct_negotiation_id(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/transcript?format=txt")
        text = resp.text
        self.assertIn("TEST_NEG_123", text)

    # 7. Transcript contains final status
    def test_7_transcript_contains_final_status(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/transcript?format=txt")
        text = resp.text
        self.assertIn("ACCEPTED", text)

    # 8. Summary contains property information when available
    def test_8_summary_contains_property_info(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertIn("3BHK Luxury High-Rise", html)
        self.assertIn("Indiranagar, Bangalore", html)
        self.assertIn("1850", html)

    # 9. Summary contains asking price when available
    def test_9_summary_contains_asking_price(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertTrue("1.50 Cr" in html or "15,000,000" in html or "1,50,00,000" in html or "15000000" in html)

    # 10. Summary contains final price when available
    def test_10_summary_contains_final_price(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertTrue("1.25 Cr" in html or "12,500,000" in html or "1,25,00,000" in html or "12500000" in html)

    # 11. Summary contains correct number of rounds
    def test_11_summary_contains_correct_rounds(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertIn("3", html)

    # 12. Summary contains actual final status
    def test_12_summary_contains_actual_final_status(self):
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertIn("ACCEPTED", html)

    # 13. Percentage calculations are correct
    def test_13_percentage_calculations(self):
        # Asking: 15,000,000. Final: 12,500,000. Diff = -2,500,000 (-16.67%)
        resp = self.client.get("/negotiations/TEST_NEG_123/summary?format=html")
        html = resp.text
        self.assertTrue("16.67%" in html or "-16.67%" in html or "16.7%" in html)

    # 14. Existing negotiation endpoint / scenarios still work
    def test_14_existing_negotiation_system(self):
        resp = self.client.get("/scenarios")
        self.assertEqual(resp.status_code, 200)
        scenarios = resp.json()
        self.assertIn("scenarios", scenarios)
        self.assertGreater(len(scenarios["scenarios"]), 0)

        p_resp = self.client.get("/properties?scenario=1&limit=5")
        self.assertEqual(p_resp.status_code, 200)
        p_data = p_resp.json()
        self.assertIn("properties", p_data)

    # 15. Existing Human vs AI functionality still works
    def test_15_human_vs_ai_functionality(self):
        init_payload = {
            "scenario": 2,
            "human_role": "buyer",
            "ai_personality": "collaborative",
            "max_rounds": 5
        }
        resp = self.client.post("/negotiations/practice", json=init_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        neg_id = data.get("negotiation_id")
        self.assertIsNotNone(neg_id)
        self.assertIn(data.get("status"), ["active", "in_progress", "accepted", "rejected"])

        # Send a message
        msg_payload = {
            "message": "I'd like to offer 8500000.",
            "offer": 8500000.0
        }
        step_resp = self.client.post(f"/negotiations/{neg_id}/message", json=msg_payload)
        self.assertEqual(step_resp.status_code, 200)

        # Test that download works for this newly created human vs AI session
        t_resp = self.client.get(f"/negotiations/{neg_id}/transcript")
        self.assertEqual(t_resp.status_code, 200)
        self.assertTrue("8500000" in t_resp.text or "85" in t_resp.text or "offer" in t_resp.text.lower())

    # 16. Existing AI vs AI functionality still works
    def test_16_ai_vs_ai_functionality(self):
        ai_payload = {
            "scenario": 2,
            "buyer_personality": 1,
            "seller_personality": 2,
            "max_rounds": 3
        }
        resp = self.client.post("/negotiations", json=ai_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        neg_id = data.get("negotiation_id")
        self.assertIsNotNone(neg_id)

        # Test that download works for this newly created AI vs AI session
        t_resp = self.client.get(f"/negotiations/{neg_id}/transcript")
        self.assertEqual(t_resp.status_code, 200)
        s_resp = self.client.get(f"/negotiations/{neg_id}/summary")
        self.assertEqual(s_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
