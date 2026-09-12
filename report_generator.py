import json
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional


def format_inr(amount: Optional[float]) -> str:
    """Format numeric INR into readable Indian currency string (Crores/Lakhs)."""
    if amount is None:
        return "Not available"
    try:
        val = float(amount)
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Crore (₹{val:,.0f})"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} Lakhs (₹{val:,.0f})"
        else:
            return f"₹{val:,.0f}"
    except Exception:
        return str(amount)


def format_inr_short(amount: Optional[float]) -> str:
    """Format numeric INR into compact currency string."""
    if amount is None:
        return "N/A"
    try:
        val = float(amount)
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} L"
        else:
            return f"₹{val:,.0f}"
    except Exception:
        return str(amount)


def get_speaker_display_name(sender: str, session: Any) -> str:
    sender_lower = str(sender or "").lower()
    if "human_buyer" in sender_lower or (sender_lower == "buyer" and getattr(session, "human_role", "") == "buyer"):
        return "BUYER (Human)"
    if "human_seller" in sender_lower or (sender_lower == "seller" and getattr(session, "human_role", "") == "seller"):
        return "SELLER (Human)"
    if "ai_buyer" in sender_lower or "buyer agent" in sender_lower:
        personality = getattr(session, "buyer_personality", None) or getattr(session, "ai_personality", "AI")
        return f"BUYER (AI - {str(personality).title()})"
    if "ai_seller" in sender_lower or "seller agent" in sender_lower:
        personality = getattr(session, "seller_personality", None) or getattr(session, "ai_personality", "AI")
        return f"SELLER / AI ({str(personality).title()})"
    if "system" in sender_lower:
        return "SYSTEM"
    return str(sender or "Participant").upper()


def extract_property_fields(prop: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(prop, dict):
        return {}
    
    title = (
        prop.get("Property Title") or
        prop.get("title") or
        prop.get("Name") or
        prop.get("Property_Name") or
        "Real Estate Property"
    )
    location = (
        prop.get("Location") or
        prop.get("location") or
        prop.get("City") or
        prop.get("Address") or
        "Not available"
    )
    sqft = (
        prop.get("Total_Area") or
        prop.get("area") or
        prop.get("Area") or
        prop.get("Square_Feet") or
        prop.get("sqft") or
        prop.get("SQFT") or
        "Not available"
    )
    bhk = (
        prop.get("Bedrooms") or
        prop.get("BHK") or
        prop.get("bhk") or
        prop.get("No_of_Bedrooms") or
        "Not available"
    )
    baths = (
        prop.get("Baths") or
        prop.get("Bathrooms") or
        prop.get("bathrooms") or
        prop.get("No_of_Bathrooms") or
        "Not available"
    )
    price_per_sqft = (
        prop.get("Price_per_SQFT") or
        prop.get("price_per_sqft") or
        "Not available"
    )
    desc = (
        prop.get("Description") or
        prop.get("description") or
        "Not available"
    )
    return {
        "title": title,
        "location": location,
        "sqft": sqft,
        "bhk": bhk,
        "baths": baths,
        "price_per_sqft": price_per_sqft,
        "description": desc
    }


# ==============================================================================
# 1. TRANSCRIPT GENERATOR
# ==============================================================================

def generate_transcript(session: Any, format_type: str = "txt") -> Tuple[str, str, str]:
    """
    Generate downloadable negotiation transcript representing actual conversation.
    Returns: (content_string, media_type, filename)
    """
    negotiation_id = getattr(session, "negotiation_id", "UNKNOWN")
    prop_data = getattr(session, "property", {}) or {}
    prop_info = extract_property_fields(prop_data)
    
    scenario_name = getattr(session, "scenario_name", None)
    if not scenario_name:
        sc_num = getattr(session, "scenario", None)
        scenario_map = {1: "Land / Plot", 2: "Apartment / Flat", 3: "Villa / Independent House"}
        scenario_name = scenario_map.get(sc_num, "Real Estate Scenario")

    asking_price = getattr(session, "asking_price", None) or getattr(session, "reference_price", None)
    asking_price_str = format_inr(asking_price)
    
    raw_status = getattr(session, "status", "UNKNOWN")
    status_str = str(raw_status).upper()
    agreed_price = getattr(session, "agreed_price", None)
    final_price_str = format_inr(agreed_price) if agreed_price is not None else "Not available (No Agreement)"
    total_rounds = getattr(session, "round", 0)

    history = getattr(session, "history", []) or []
    fmt = format_type.strip().lower()

    if fmt == "json":
        payload = {
            "negotiation_id": negotiation_id,
            "scenario": scenario_name,
            "property": prop_info,
            "asking_price": asking_price,
            "asking_price_formatted": asking_price_str,
            "final_outcome": {
                "status": status_str,
                "agreed_price": agreed_price,
                "total_rounds": total_rounds
            },
            "history": history
        }
        return (
            json.dumps(payload, indent=2),
            "application/json",
            f"negotiation_{negotiation_id}_transcript.json"
        )

    elif fmt in ["md", "markdown"]:
        lines = []
        lines.append(f"# NEGOTIATION TRANSCRIPT")
        lines.append(f"==================================================")
        lines.append(f"**Negotiation ID:** `{negotiation_id}`  ")
        lines.append(f"**Scenario:** {scenario_name}  ")
        lines.append(f"**Property:** {prop_info['title']}  ")
        lines.append(f"**Location:** {prop_info['location']}  ")
        lines.append(f"**Asking Price:** {asking_price_str}  \n")

        # Group messages by round
        rounds_dict: Dict[int, list] = {}
        for item in history:
            r = item.get("round", 0)
            rounds_dict.setdefault(r, []).append(item)

        for r_num in sorted(rounds_dict.keys()):
            lines.append(f"## ROUND {r_num}")
            lines.append(f"--------------------------------------------------")
            for item in rounds_dict[r_num]:
                speaker = get_speaker_display_name(item.get("sender") or item.get("agent", ""), session)
                msg = item.get("message", "").strip()
                offer = item.get("offer")
                decision = item.get("decision")
                
                lines.append(f"**{speaker}:**")
                lines.append(f"> {msg}\n")
                if offer is not None:
                    lines.append(f"- **Offer / Position:** {format_inr(offer)}")
                if decision:
                    lines.append(f"- **Decision:** `{decision}`")
                lines.append("")

        lines.append(f"## FINAL OUTCOME")
        lines.append(f"==================================================")
        lines.append(f"**Status:** `{status_str}`  ")
        lines.append(f"**Final Price:** {final_price_str}  ")
        lines.append(f"**Total Rounds:** {total_rounds}  ")

        return (
            "\n".join(lines),
            "text/markdown; charset=utf-8",
            f"negotiation_{negotiation_id}_transcript.md"
        )

    else:
        # Standard Plain Text (.txt) format matching the example format
        sep = "=" * 50
        sub_sep = "-" * 50
        lines = []
        lines.append("NEGOTIATION TRANSCRIPT")
        lines.append(sep)
        lines.append(f"Negotiation ID: {negotiation_id}")
        lines.append(f"Scenario: {scenario_name}")
        lines.append(f"Property: {prop_info['title']}")
        lines.append(f"Asking Price: {asking_price_str}")
        lines.append("")

        rounds_dict: Dict[int, list] = {}
        for item in history:
            r = item.get("round", 0)
            rounds_dict.setdefault(r, []).append(item)

        for r_num in sorted(rounds_dict.keys()):
            lines.append(f"ROUND {r_num}")
            lines.append(sub_sep)
            for item in rounds_dict[r_num]:
                speaker = get_speaker_display_name(item.get("sender") or item.get("agent", ""), session)
                msg = item.get("message", "").strip()
                offer = item.get("offer")
                decision = item.get("decision")

                lines.append(f"{speaker}:")
                lines.append(f"{msg}")
                if offer is not None:
                    lines.append(f"Offer: {format_inr(offer)}")
                if decision:
                    lines.append(f"Decision: {decision}")
                lines.append("")

        lines.append("FINAL OUTCOME")
        lines.append(sep)
        lines.append(f"Status: {status_str}")
        lines.append(f"Final Price: {final_price_str}")
        lines.append(f"Total Rounds: {total_rounds}")

        return (
            "\n".join(lines),
            "text/plain; charset=utf-8",
            f"negotiation_{negotiation_id}_transcript.txt"
        )


# ==============================================================================
# 2. SUMMARY REPORT GENERATOR
# ==============================================================================

def generate_summary(session: Any, format_type: str = "html") -> Tuple[str, str, str]:
    """
    Generate downloadable negotiation summary report covering Sections A through F.
    Returns: (content_string, media_type, filename)
    """
    negotiation_id = getattr(session, "negotiation_id", "UNKNOWN")
    prop_data = getattr(session, "property", {}) or {}
    prop_info = extract_property_fields(prop_data)
    
    scenario_name = getattr(session, "scenario_name", None)
    if not scenario_name:
        sc_num = getattr(session, "scenario", None)
        scenario_map = {1: "Land / Plot", 2: "Apartment / Flat", 3: "Villa / Independent House"}
        scenario_name = scenario_map.get(sc_num, "Real Estate Scenario")

    created_at = getattr(session, "created_at", None)
    if created_at:
        try:
            timestamp_str = datetime.fromtimestamp(float(created_at)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Asking & Final Prices
    asking_price = getattr(session, "asking_price", None) or getattr(session, "reference_price", None)
    asking_price_str = format_inr(asking_price)
    agreed_price = getattr(session, "agreed_price", None)
    final_price_str = format_inr(agreed_price) if agreed_price is not None else "Not available (No Agreement)"
    raw_status = getattr(session, "status", "UNKNOWN")
    status_str = str(raw_status).upper()
    total_rounds = getattr(session, "round", 0)

    # Percentage difference calculation
    pct_diff_str = "Not available"
    pct_diff_val = None
    price_diff = None
    if agreed_price is not None and asking_price and asking_price > 0:
        price_diff = asking_price - agreed_price
        pct_diff_val = (price_diff / asking_price) * 100
        pct_diff_str = f"{pct_diff_val:.2f}% (Savings: {format_inr(price_diff)})"

    # Participants & Strategies
    mode = getattr(session, "mode", "human_vs_ai")
    human_role = getattr(session, "human_role", None)
    ai_role = getattr(session, "ai_role", None)
    ai_personality = getattr(session, "ai_personality", None)
    buyer_personality = getattr(session, "buyer_personality", None)
    seller_personality = getattr(session, "seller_personality", None)
    buyer_target = getattr(session, "target_price", None) if human_role == "buyer" or mode == "ai_vs_ai" else getattr(session, "minimum_price", None)
    seller_target = getattr(session, "target_price", None) if human_role == "seller" else getattr(session, "asking_price", None)

    # Financial analysis & timeline from actual history
    history = getattr(session, "history", []) or []
    buyer_initial_offer = None
    seller_initial_position = None
    buyer_concessions_by_round: Dict[int, float] = {}
    seller_concessions_by_round: Dict[int, float] = {}
    timeline_rows = []

    last_buyer_price = None
    last_seller_price = None

    for item in history:
        r = item.get("round", 0)
        sender_raw = str(item.get("sender") or item.get("agent") or "").lower()
        off = item.get("offer")
        msg = item.get("message", "")

        is_buyer = "buyer" in sender_raw or "human_buyer" in sender_raw
        is_seller = "seller" in sender_raw or "ai_seller" in sender_raw

        if off is not None:
            if is_buyer:
                if buyer_initial_offer is None:
                    buyer_initial_offer = off
                buyer_concessions_by_round[r] = off
                last_buyer_price = off
            elif is_seller:
                if seller_initial_position is None:
                    seller_initial_position = off
                seller_concessions_by_round[r] = off
                last_seller_price = off

        timeline_rows.append({
            "round": r,
            "speaker": get_speaker_display_name(item.get("sender") or item.get("agent", ""), session),
            "decision": item.get("decision", "OFFER"),
            "offer": off,
            "offer_formatted": format_inr_short(off) if off is not None else "—",
            "message": (msg[:70] + "...") if len(msg) > 70 else msg
        })

    # Deadlock / Behavioral info
    deadlock_reason = getattr(session, "deadlock_reason", None)
    repeated_offers = getattr(session, "repeated_offer_count", 0)
    stagnant_rounds = getattr(session, "stagnant_round_count", 0)
    is_deadlocked = status_str == "DEADLOCKED"

    # Training feedback / Key takeaways
    takeaways = []
    if status_str in ["ACCEPTED", "AGREEMENT_REACHED"]:
        takeaways.append(f"Negotiation successfully closed at {final_price_str} within {total_rounds} rounds.")
        if pct_diff_val is not None and pct_diff_val > 0:
            takeaways.append(f"Buyer negotiated a {pct_diff_val:.2f}% discount below the original asking price.")
    elif is_deadlocked:
        takeaways.append(f"Negotiation resulted in a deadlock: {deadlock_reason or 'Parties stopped making meaningful concessions.'}")
    elif status_str == "CANCELLED":
        takeaways.append("Session was cancelled prematurely by the participant.")
    else:
        takeaways.append(f"Negotiation concluded with status '{status_str}' after {total_rounds} rounds.")

    if buyer_initial_offer and asking_price:
        opening_spread = ((asking_price - buyer_initial_offer) / asking_price) * 100
        takeaways.append(f"Opening bid was set at {format_inr(buyer_initial_offer)} ({opening_spread:.1f}% gap from asking price).")

    fmt = format_type.strip().lower()

    # JSON export format
    if fmt == "json":
        payload = {
            "metadata": {
                "negotiation_id": negotiation_id,
                "timestamp": timestamp_str,
                "scenario": scenario_name,
                "property": prop_info,
                "asking_price": asking_price,
                "asking_price_formatted": asking_price_str
            },
            "executive_summary": {
                "final_status": status_str,
                "final_price": agreed_price,
                "final_price_formatted": final_price_str,
                "total_rounds": total_rounds,
                "price_difference": price_diff,
                "percentage_difference": round(pct_diff_val, 2) if pct_diff_val is not None else None,
                "percentage_difference_formatted": pct_diff_str
            },
            "participants": {
                "mode": mode,
                "human_role": human_role,
                "ai_role": ai_role,
                "ai_personality": ai_personality,
                "buyer_personality": buyer_personality,
                "seller_personality": seller_personality,
                "buyer_target_price": buyer_target,
                "seller_target_price": seller_target
            },
            "financial_analysis": {
                "asking_price": asking_price,
                "buyer_initial_offer": buyer_initial_offer,
                "seller_initial_position": seller_initial_position,
                "final_price": agreed_price,
                "difference_from_asking": price_diff,
                "buyer_concessions_by_round": buyer_concessions_by_round,
                "seller_concessions_by_round": seller_concessions_by_round
            },
            "deadlock_behavioral_info": {
                "deadlock_status": is_deadlocked,
                "deadlock_reason": deadlock_reason,
                "repeated_offers": repeated_offers,
                "stagnant_rounds": stagnant_rounds
            },
            "training_feedback": {
                "key_takeaways": takeaways
            }
        }
        return (
            json.dumps(payload, indent=2),
            "application/json",
            f"negotiation_{negotiation_id}_summary.json"
        )

    elif fmt in ["md", "markdown"]:
        lines = []
        lines.append(f"# REAL ESTATE NEGOTIATION SUMMARY REPORT")
        lines.append(f"==================================================")
        lines.append(f"\n## A. HEADER & METADATA")
        lines.append(f"- **Negotiation ID:** `{negotiation_id}`")
        lines.append(f"- **Timestamp:** {timestamp_str}")
        lines.append(f"- **Scenario Type:** {scenario_name}")
        lines.append(f"- **Property Name:** {prop_info['title']}")
        lines.append(f"- **Location:** {prop_info['location']}")
        lines.append(f"- **BHK:** {prop_info['bhk']}")
        lines.append(f"- **Square Feet (SQFT):** {prop_info['sqft']}")
        lines.append(f"- **Bathrooms:** {prop_info['baths']}")
        lines.append(f"- **Asking Price:** {asking_price_str}")

        lines.append(f"\n## B. EXECUTIVE SUMMARY & OUTCOME")
        lines.append(f"- **Final Status:** `{status_str}`")
        lines.append(f"- **Final / Agreed Price:** **{final_price_str}**")
        lines.append(f"- **Total Rounds:** {total_rounds}")
        lines.append(f"- **Price Difference / Concession:** {pct_diff_str}")

        lines.append(f"\n## C. PARTICIPANTS & STRATEGIES")
        if mode == "human_vs_ai":
            lines.append(f"- **Human Role:** {str(human_role).upper() if human_role else 'Not available'}")
            lines.append(f"- **AI Role:** {str(ai_role).upper() if ai_role else 'Not available'}")
            lines.append(f"- **AI Personality:** {str(ai_personality).title() if ai_personality else 'Not available'}")
        else:
            lines.append(f"- **Buyer Agent Personality:** {str(buyer_personality).title() if buyer_personality else 'Not available'}")
            lines.append(f"- **Seller Agent Personality:** {str(seller_personality).title() if seller_personality else 'Not available'}")
        if buyer_target:
            lines.append(f"- **Buyer Target Price:** {format_inr(buyer_target)}")
        if seller_target:
            lines.append(f"- **Seller Target Price:** {format_inr(seller_target)}")

        lines.append(f"\n## D. FINANCIAL ANALYSIS")
        lines.append(f"- **Original Asking Price:** {asking_price_str}")
        lines.append(f"- **Buyer Initial Offer:** {format_inr(buyer_initial_offer) if buyer_initial_offer else 'Not available'}")
        lines.append(f"- **Seller Initial Position:** {format_inr(seller_initial_position) if seller_initial_position else 'Not available'}")
        lines.append(f"- **Final Price:** {final_price_str}")
        if price_diff is not None:
            lines.append(f"- **Difference from Asking Price:** {format_inr(price_diff)}")

        lines.append(f"\n### Concession Timeline")
        if timeline_rows:
            lines.append("| Round | Speaker | Action / Decision | Offer | Summary |")
            lines.append("| :---: | :--- | :---: | :---: | :--- |")
            for t in timeline_rows:
                lines.append(f"| {t['round']} | {t['speaker']} | `{t['decision']}` | **{t['offer_formatted']}** | {t['message']} |")
        else:
            lines.append("*No timeline records available.*")

        lines.append(f"\n## E. DEADLOCK & BEHAVIORAL INFORMATION")
        lines.append(f"- **Deadlock Status:** {'DEADLOCKED' if is_deadlocked else 'NO DEADLOCK'}")
        if deadlock_reason:
            lines.append(f"- **Deadlock Reason:** {deadlock_reason}")
        lines.append(f"- **Repeated Offers Count:** {repeated_offers}")
        lines.append(f"- **Stagnant Rounds Count:** {stagnant_rounds}")

        lines.append(f"\n## F. TRAINING FEEDBACK & KEY TAKEAWAYS")
        for tw in takeaways:
            lines.append(f"- {tw}")

        return (
            "\n".join(lines),
            "text/markdown; charset=utf-8",
            f"negotiation_{negotiation_id}_summary.md"
        )

    elif fmt == "txt":
        sep = "=" * 60
        sub_sep = "-" * 60
        lines = []
        lines.append("REAL ESTATE NEGOTIATION SUMMARY REPORT")
        lines.append(sep)
        lines.append(f"Negotiation ID: {negotiation_id}")
        lines.append(f"Timestamp: {timestamp_str}")
        lines.append(f"Scenario: {scenario_name}")
        lines.append(f"Property: {prop_info['title']}")
        lines.append(f"Location: {prop_info['location']}")
        lines.append(f"BHK: {prop_info['bhk']} | SQFT: {prop_info['sqft']} | Baths: {prop_info['baths']}")
        lines.append(f"Asking Price: {asking_price_str}")
        lines.append("")
        lines.append("EXECUTIVE SUMMARY & OUTCOME")
        lines.append(sub_sep)
        lines.append(f"Status: {status_str}")
        lines.append(f"Final Price: {final_price_str}")
        lines.append(f"Total Rounds: {total_rounds}")
        lines.append(f"Percentage Difference: {pct_diff_str}")
        lines.append("")
        lines.append("FINANCIAL ANALYSIS")
        lines.append(sub_sep)
        lines.append(f"Asking Price: {asking_price_str}")
        lines.append(f"Buyer Initial Offer: {format_inr(buyer_initial_offer) if buyer_initial_offer else 'N/A'}")
        lines.append(f"Final Price: {final_price_str}")
        if price_diff is not None:
            lines.append(f"Difference from Asking Price: {format_inr(price_diff)}")
        lines.append("")
        lines.append("CONCESSION TIMELINE")
        lines.append(sub_sep)
        for t in timeline_rows:
            lines.append(f"Round {t['round']} | {t['speaker']} | Offer: {t['offer_formatted']}")
        lines.append("")
        lines.append("DEADLOCK / BEHAVIORAL INFO")
        lines.append(sub_sep)
        lines.append(f"Deadlock: {'YES' if is_deadlocked else 'NO'}")
        if deadlock_reason:
            lines.append(f"Reason: {deadlock_reason}")
        lines.append(f"Repeated Offers: {repeated_offers} | Stagnant Rounds: {stagnant_rounds}")
        lines.append("")
        lines.append("KEY TAKEAWAYS")
        lines.append(sub_sep)
        for tw in takeaways:
            lines.append(f"- {tw}")
        lines.append(sep)

        return (
            "\n".join(lines),
            "text/plain; charset=utf-8",
            f"negotiation_{negotiation_id}_summary.txt"
        )

    else:
        # Default: Professional Printable HTML Report
        status_color = "#10b981" if status_str in ["ACCEPTED", "AGREEMENT_REACHED"] else ("#ef4444" if is_deadlocked else "#6366f1")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Negotiation Summary Report - {negotiation_id}</title>
<style>
  :root {{
    --primary: #4f46e5;
    --primary-dark: #3730a3;
    --success: #10b981;
    --danger: #ef4444;
    --text-main: #1f2937;
    --text-muted: #6b7280;
    --bg-page: #f8fafc;
    --bg-card: #ffffff;
    --border: #e2e8f0;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg-page);
    color: var(--text-main);
    line-height: 1.6;
    padding: 30px 20px;
  }}
  .container {{
    max-width: 900px;
    margin: 0 auto;
    background: var(--bg-card);
    border-radius: 12px;
    border: 1px solid var(--border);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    padding: 36px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid var(--border);
    padding-bottom: 20px;
    margin-bottom: 28px;
  }}
  .header h1 {{ font-size: 24px; color: var(--text-main); font-weight: 800; }}
  .header .sub {{ color: var(--text-muted); font-size: 13px; margin-top: 4px; }}
  .status-badge {{
    display: inline-block;
    padding: 6px 14px;
    border-radius: 999px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.05em;
    background: {status_color}15;
    color: {status_color};
    border: 1px solid {status_color}40;
  }}
  .section {{ margin-bottom: 28px; }}
  .section-title {{
    font-size: 15px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--primary);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  .metric-card {{
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
  }}
  .metric-label {{ font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }}
  .metric-val {{ font-size: 16px; font-weight: 800; color: var(--text-main); margin-top: 4px; }}
  .highlight {{ color: var(--primary); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 10px;
  }}
  th, td {{
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{ background: #f1f5f9; font-weight: 700; color: var(--text-muted); font-size: 11px; text-transform: uppercase; }}
  .takeaways-list {{ list-style-type: none; }}
  .takeaways-list li {{
    position: relative;
    padding-left: 22px;
    margin-bottom: 8px;
    font-size: 13px;
  }}
  .takeaways-list li::before {{
    content: "•";
    color: var(--primary);
    font-weight: bold;
    font-size: 18px;
    position: absolute;
    left: 4px;
    top: -2px;
  }}
  .footer {{
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-muted);
    text-align: center;
  }}
  .print-btn {{
    display: inline-block;
    padding: 8px 16px;
    background: var(--primary);
    color: white;
    border-radius: 6px;
    font-weight: 700;
    font-size: 12px;
    text-decoration: none;
    cursor: pointer;
    border: none;
    margin-bottom: 20px;
  }}
  @media print {{
    body {{ background: white; padding: 0; }}
    .container {{ border: none; box-shadow: none; padding: 0; max-width: 100%; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>

<div class="container">
  <div class="no-print" style="text-align: right;">
    <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
  </div>

  <!-- HEADER -->
  <div class="header">
    <div>
      <h1>Real Estate Negotiation Summary</h1>
      <div class="sub">Session ID: <strong>{negotiation_id}</strong> | Generated: {timestamp_str}</div>
    </div>
    <div>
      <span class="status-badge">{status_str}</span>
    </div>
  </div>

  <!-- A. PROPERTY OVERVIEW -->
  <div class="section">
    <div class="section-title">🏡 Section A — Property & Scenario Profile</div>
    <div class="grid-2">
      <div class="metric-card">
        <div class="metric-label">Property Title</div>
        <div class="metric-val">{prop_info['title']}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Location & Scenario</div>
        <div class="metric-val">{prop_info['location']} ({scenario_name})</div>
      </div>
    </div>
    <div class="grid-3" style="margin-top: 12px;">
      <div class="metric-card">
        <div class="metric-label">Configuration</div>
        <div class="metric-val">{prop_info['bhk']} BHK | {prop_info['baths']} Baths</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Total Area</div>
        <div class="metric-val">{prop_info['sqft']} SQFT</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Asking Price</div>
        <div class="metric-val highlight">{asking_price_str}</div>
      </div>
    </div>
  </div>

  <!-- B. EXECUTIVE SUMMARY & OUTCOME -->
  <div class="section">
    <div class="section-title">🏆 Section B — Executive Summary & Outcome</div>
    <div class="grid-3">
      <div class="metric-card">
        <div class="metric-label">Final Outcome</div>
        <div class="metric-val">{status_str}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Agreed / Final Price</div>
        <div class="metric-val highlight">{final_price_str}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Price Concession / Delta</div>
        <div class="metric-val">{pct_diff_str}</div>
      </div>
    </div>
  </div>

  <!-- C. PARTICIPANTS & STRATEGIES -->
  <div class="section">
    <div class="section-title">👥 Section C — Participants & Strategies</div>
    <div class="grid-2">
      <div class="metric-card">
        <div class="metric-label">Buyer Participant</div>
        <div class="metric-val">{'Human' if human_role == 'buyer' else f'AI Agent ({str(buyer_personality or ai_personality).title()})'}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Seller Participant</div>
        <div class="metric-val">{'Human' if human_role == 'seller' else f'AI Agent ({str(seller_personality or ai_personality).title()})'}</div>
      </div>
    </div>
  </div>

  <!-- D. FINANCIAL ANALYSIS & TIMELINE -->
  <div class="section">
    <div class="section-title">📈 Section D — Financial Analysis & Concession Timeline</div>
    <table>
      <thead>
        <tr>
          <th>Round</th>
          <th>Speaker</th>
          <th>Action</th>
          <th>Offer</th>
          <th>Message Snippet</th>
        </tr>
      </thead>
      <tbody>
        {''.join(f"<tr><td><strong>{t['round']}</strong></td><td>{t['speaker']}</td><td><code>{t['decision']}</code></td><td><strong>{t['offer_formatted']}</strong></td><td>{t['message']}</td></tr>" for t in timeline_rows) if timeline_rows else "<tr><td colspan='5'>No concession records available.</td></tr>"}
      </tbody>
    </table>
  </div>

  <!-- E. DEADLOCK / BEHAVIORAL -->
  <div class="section">
    <div class="section-title">⚙️ Section E — Deadlock & Behavioral Metrics</div>
    <div class="grid-3">
      <div class="metric-card">
        <div class="metric-label">Deadlock Condition</div>
        <div class="metric-val">{'TRIGGERED' if is_deadlocked else 'NONE'}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Repeated Offers</div>
        <div class="metric-val">{repeated_offers}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Stagnant Rounds</div>
        <div class="metric-val">{stagnant_rounds}</div>
      </div>
    </div>
    {f'<div class="metric-card" style="margin-top:12px;"><div class="metric-label">Impasse Diagnosis</div><div class="metric-val" style="font-size:13px;font-weight:normal;">{deadlock_reason}</div></div>' if deadlock_reason else ''}
  </div>

  <!-- F. TRAINING FEEDBACK & TAKEAWAYS -->
  <div class="section">
    <div class="section-title">💡 Section F — Training Feedback & Key Takeaways</div>
    <ul class="takeaways-list">
      {''.join(f"<li>{tw}</li>" for tw in takeaways)}
    </ul>
  </div>

  <div class="footer">
    Real Estate Negotiation Training & Simulation Platform — Milestone 4 Report Generator
  </div>
</div>

</body>
</html>"""

        return (
            html_content,
            "text/html; charset=utf-8",
            f"negotiation_{negotiation_id}_summary.html"
        )
