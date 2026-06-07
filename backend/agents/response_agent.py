"""
Response Agent
--------------
Responsibility: Generate a structured, professional RFP proposal document.
Now supports:
1. LLM-based proposal generation (primary)
2. Template-based fallback (safety)
"""

from datetime import date
from config import INSTALL_RATE_PER_FLOOR, LOGISTICS_COST
from utils.llm_helper import generate_proposal


def response_agent(req: dict, product: dict, pricing: dict, reason: str) -> tuple[str, list[str]]:
    logs = ["[Response Agent] Preparing proposal generation..."]

    today  = date.today().strftime("%B %d, %Y")
    ref_no = f"RFP-{date.today().strftime('%Y%m%d')}-{product['id']}"

    # ── STEP 1: Try LLM Generation ────────────────────────────────────────────
    try:
        logs.append("[Response Agent] Attempting LLM-based proposal generation...")

        proposal = generate_proposal({
            "requirements": req,
            "product": product,
            "pricing": pricing
        })

        if proposal and len(proposal.strip()) > 50:
            logs.append("[Response Agent] LLM proposal generated successfully.")
            return proposal.strip(), logs

        else:
            logs.append("[Response Agent] LLM returned weak/empty response. Falling back...")

    except Exception as e:
        logs.append(f"[Response Agent] LLM generation failed: {str(e)}")

    # ── STEP 2: Fallback to Template (SAFE) ───────────────────────────────────
    logs.append("[Response Agent] Using template-based fallback proposal.")

    def fv(val, unit=""):
        return f"{val} {unit}".strip() if val != "Not specified" else "Not specified"

    proposal = f"""
================================================================================
                    ElevateRFP — OFFICIAL PROPOSAL RESPONSE
================================================================================
  Reference No : {ref_no}
  Date         : {today}
  Prepared by  : ElevateRFP Multi-Agent Automation System
================================================================================

SECTION 1 — INTRODUCTION
─────────────────────────────────────────────────────────────────────────────
  ElevateRFP is pleased to present this automated proposal in response to your
  Request for Proposal (RFP). Our system has analyzed your document and selected
  the most suitable elevator solution.

SECTION 2 — CUSTOMER REQUIREMENTS SUMMARY
─────────────────────────────────────────────────────────────────────────────
  Number of Floors : {fv(req.get('floors'), 'floors')}
  Load Capacity    : {fv(req.get('capacity'), 'kg')}
  Elevator Speed   : {fv(req.get('speed'), 'm/s')}

SECTION 3 — RECOMMENDED SOLUTION
─────────────────────────────────────────────────────────────────────────────
  Model Name       : {product['name']}
  Product ID       : {product['id']}
  Capacity         : {product['capacity']} kg
  Max Floors       : {product['max_floors']}
  Speed            : {product['speed']} m/s

  Selection Reason : {reason}

SECTION 4 — PRICING DETAILS
─────────────────────────────────────────────────────────────────────────────
  Base Price       : RS {pricing['base_price']:,.2f}
  Installation     : RS {pricing['installation_cost']:,.2f}
  Logistics        : RS {pricing['logistics_cost']:,.2f}
  Margin ({pricing['margin_pct']}%) : RS {pricing['profit_margin']:,.2f}

  TOTAL PRICE      : RS {pricing['total_price']:,.2f}

SECTION 5 — CONCLUSION
─────────────────────────────────────────────────────────────────────────────
  The selected solution provides optimal performance and cost efficiency
  for your requirements.

  Thank you for considering ElevateRFP.

================================================================================
""".strip()

    logs.append(f"[Response Agent] Template proposal generated. Reference: {ref_no}")

    return proposal, logs