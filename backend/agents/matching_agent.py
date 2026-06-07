"""
Matching Agent
--------------
Uses RAG (FAISS) to retrieve relevant products, then applies rule-based scoring
+ LLM reasoning to select the best-fit elevator.
"""

from config import PRODUCTS
from utils.llm_helper import generate_reasoning
from utils.rag_helper import retrieve_products


# ── Confidence Function ─────────────────────────────────────────
def calculate_confidence(product, req):
    score = 0
    max_score = 6  # 3 + 2 + 1

    if isinstance(req.get("capacity"), float) and product["capacity"] >= req["capacity"]:
        score += 3

    if isinstance(req.get("floors"), int) and product["max_floors"] >= req["floors"]:
        score += 2

    if isinstance(req.get("speed"), float) and product["speed"] >= req["speed"]:
        score += 1

    return round((score / max_score) * 100, 2)


# ── Scoring Function ────────────────────────────────────────────
def _score(product: dict, floors, capacity, speed) -> int:
    score = 0
    if isinstance(capacity, float) and product["capacity"]   >= capacity: score += 3
    if isinstance(floors,   int)   and product["max_floors"] >= floors:   score += 2
    if isinstance(speed,    float) and product["speed"]      >= speed:    score += 1
    return score


# ── Main Matching Agent ─────────────────────────────────────────
def matching_agent(req: dict) -> tuple[dict, str, float, list[str]]:
    logs = ["[Matching Agent] Starting product matching process..."]

    floors   = req.get("floors",   "Not specified")
    capacity = req.get("capacity", "Not specified")
    speed    = req.get("speed",    "Not specified")

    # ── Step 1: RAG Retrieval ───────────────────────────────────
    logs.append("[Matching Agent] Retrieving top products using RAG...")

    query = f"{floors} floors {capacity} kg {speed} m/s"

    try:
        candidates = retrieve_products(query)
        logs.append(f"[Matching Agent] Retrieved {len(candidates)} candidates via RAG.")
    except Exception as e:
        logs.append(f"[Matching Agent] RAG retrieval failed: {str(e)}")
        candidates = PRODUCTS  # fallback to all products

    # ── Step 2: No match case ────────────────────────────────────
    if not candidates:
        logs.append("[Matching Agent] No product found after retrieval.")
        return None, "No suitable product found.", 0.0, logs

    # ── Step 3: Select best product (rule-based on retrieved set)
    scored = sorted(
        candidates,
        key=lambda p: (-_score(p, floors, capacity, speed), p["base_price"])
    )

    best = scored[0]

    # ── Step 4: Confidence Score ────────────────────────────────
    confidence = calculate_confidence(best, req)
    logs.append(f"[Matching Agent] Confidence score: {confidence}%")

    # ── Step 5: Rule fallback reason ─────────────────────────────
    parts = []
    if isinstance(capacity, float): parts.append(f"capacity ≥ {capacity} kg")
    if isinstance(floors,   int):   parts.append(f"floors ≥ {floors}")
    if isinstance(speed,    float): parts.append(f"speed ≥ {speed} m/s")

    reason = (
        "Selected because it satisfies " + ", ".join(parts)
        if parts else "Selected as default model."
    )

    # ── Step 6: LLM reasoning ───────────────────────────────────
    logs.append("[Matching Agent] Generating selection reasoning using LLM...")

    try:
        llm_reason = generate_reasoning({
            "requirements": req,
            "product": best
        })

        if llm_reason and len(llm_reason.strip()) > 20:
            reason = llm_reason
            logs.append("[Matching Agent] LLM reasoning generated successfully.")
        else:
            logs.append("[Matching Agent] LLM returned weak response, using fallback.")

    except Exception as e:
        logs.append(f"[Matching Agent] LLM reasoning failed: {str(e)}")

    # ── Final return ────────────────────────────────────────────
    logs.append(f"[Matching Agent] Selected product: {best['name']}")

    retrieved_products = candidates[:3]

    return best, reason, confidence, logs, retrieved_products