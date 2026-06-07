"""
Extraction Agent
----------------
Responsibility: Apply regex rules to extract structured requirements
(floors, capacity, speed) from cleaned document text.
Returns 'Not specified' for any parameter not found.
"""

import re
from utils.llm_helper import extract_rfp_fields

def extraction_agent(text: str) -> tuple[dict, list[str]]:
    logs = ["[Extraction Agent] Scanning document for elevator requirements..."]
    t    = text.lower()
    req  = {}

    # ── Floors ────────────────────────────────────────────────────────────────
    # Matches: "15 floors", "15 levels", "15 stories", "15-storey", "15 floor building"
    m = re.search(r'(\d+)\s*[-]?\s*(?:floors?|levels?|stor(?:ey|ies|y))', t)
    if m:
        req["floors"] = int(m.group(1))
        logs.append(f"[Extraction Agent] Floors detected: {req['floors']}")
    else:
        req["floors"] = "Not specified"
        logs.append("[Extraction Agent] Floors: not found in document.")

    # ── Capacity ──────────────────────────────────────────────────────────────
    # Matches: "1000 kg", "1,000 kg", "1000 kilograms", "load of 800kg"
    m = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*(?:kg|kilograms?)', t)
    if m:
        req["capacity"] = float(m.group(1).replace(",", ""))
        logs.append(f"[Extraction Agent] Capacity detected: {req['capacity']} kg")
    else:
        req["capacity"] = "Not specified"
        logs.append("[Extraction Agent] Capacity: not found in document.")

    # ── Speed ─────────────────────────────────────────────────────────────────
    # Matches: "1.5 m/s", "2 mps", "1.5 meters per second", "speed: 2.5m/s"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:m/s|mps|meters?\s*per\s*second)', t)
    if m:
        req["speed"] = float(m.group(1))
        logs.append(f"[Extraction Agent] Speed detected: {req['speed']} m/s")
    else:
        req["speed"] = "Not specified"
        logs.append("[Extraction Agent] Speed: not found in document.")

    # ── Completeness check ────────────────────────────────────────────────────
    found = [k for k, v in req.items() if v != "Not specified"]
    logs.append(
        f"[Extraction Agent] Extraction complete. "
        f"Found {len(found)}/3 parameters: {found if found else 'none'}."
    )

    return req, logs
