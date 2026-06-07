"""
Sales Agent
-----------
Responsibility: Parse uploaded PDF, extract raw text, clean it,
and validate that the document is a valid elevator RFP.
Raises HTTPException for invalid files or non-domain documents.
"""

import re
from PyPDF2 import PdfReader
from fastapi import HTTPException

# ── Keyword Sets ─────────────────────────────────────────────────────────────

ELEVATOR_KEYWORDS = [
    "elevator", "lift", "passenger lift", "freight lift",
    "shaft", "hoistway", "machine room"
]

TECH_KEYWORDS = [
    "floors", "capacity", "kg", "speed", "m/s"
]

RFP_KEYWORDS = [
    "request for proposal", "rfp", "tender",
    "quotation", "bid", "contract"
]


# ── Main Sales Agent Function ────────────────────────────────────────────────

def sales_agent(file) -> tuple[str, list[str]]:
    logs = ["[Sales Agent] Initializing PDF text extraction pipeline..."]

    # ── Step 1: Parse PDF ────────────────────────────────────────────────────
    try:
        reader = PdfReader(file)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Invalid or corrupted PDF file. Please upload a valid PDF document."
        )

    if not reader.pages:
        raise HTTPException(
            status_code=422,
            detail="The uploaded PDF has no readable pages."
        )

    # ── Step 2: Extract text page by page ────────────────────────────────────
    pages_text = []
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        pages_text.append(t)
        logs.append(f"[Sales Agent] Page {i + 1}: extracted {len(t)} characters.")

    raw_text = " ".join(pages_text)
    text = re.sub(r'\s+', ' ', raw_text).strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from PDF. The file may be scanned/image-based or password protected."
        )

    logs.append(f"[Sales Agent] Total text extracted: {len(text)} characters across {len(reader.pages)} page(s).")

    # ── Step 3: Advanced RFP Validation ──────────────────────────────────────
    lower = text.lower()

    domain_score = sum(1 for kw in ELEVATOR_KEYWORDS if kw in lower)
    tech_score   = sum(1 for kw in TECH_KEYWORDS if kw in lower)
    rfp_score    = sum(1 for kw in RFP_KEYWORDS if kw in lower)

    logs.append(f"[Sales Agent] Domain score: {domain_score}")
    logs.append(f"[Sales Agent] Technical score: {tech_score}")
    logs.append(f"[Sales Agent] RFP intent score: {rfp_score}")

    # 🎯 Acceptance Conditions
    if domain_score < 2:
        raise HTTPException(
            status_code=422,
            detail="Document is not related to elevator/lift systems."
        )

    if tech_score < 2:
        raise HTTPException(
            status_code=422,
            detail="Document lacks required technical specifications (floors, capacity, speed)."
        )

    if rfp_score < 1:
        raise HTTPException(
            status_code=422,
            detail="Document is not a Request for Proposal (RFP) or tender document."
        )

    # ── Optional: Combined Score (for logs/debugging) ─────────────────────────
    total_score = (domain_score * 2) + (tech_score * 2) + (rfp_score * 3)
    logs.append(f"[Sales Agent] Total validation score: {total_score}")

    logs.append("[Sales Agent] Advanced domain validation passed. Proceeding to next agent.")

    return text, logs