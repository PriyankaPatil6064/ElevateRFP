import google.generativeai as genai
import json
import re

# 🔑 Configure API
import os
genai.configure(api_key=os.getenv("AIzaSyC1jyq7eJIhPV2JEa5kYlb2e1ZT8A_RVAY"))
# 🤖 Model
model = genai.GenerativeModel("gemini-pro")


# ─────────────────────────────────────────────────────────────
# 🔍 Extraction Function (Hybrid Support)
# ─────────────────────────────────────────────────────────────
def extract_rfp_fields(text):
    prompt = f"""
    Extract the following information from the RFP text:

    - number of floors (integer)
    - load capacity in kg (number)
    - elevator speed in m/s (number)

    Return ONLY valid JSON like:
    {{
        "floors": number or null,
        "capacity": number or null,
        "speed": number or null
    }}

    Do NOT include explanation. Only JSON.

    Text:
    {text[:3000]}
    """

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Clean markdown if present
        raw = re.sub(r"```json|```", "", raw).strip()

        return json.loads(raw)

    except Exception:
        return {
            "floors": None,
            "capacity": None,
            "speed": None
        }


# ─────────────────────────────────────────────────────────────
# 📄 Proposal Generation Function
# ─────────────────────────────────────────────────────────────
def generate_proposal(data):
    prompt = f"""
    You are an expert in elevator RFP proposal writing.

    Generate a professional, well-structured proposal using the details below.

    Requirements:
    - Floors: {data['requirements']['floors']}
    - Capacity: {data['requirements']['capacity']} kg
    - Speed: {data['requirements']['speed']} m/s

    Selected Product:
    - Name: {data['product']['name']}
    - Capacity: {data['product']['capacity']} kg
    - Max Floors: {data['product']['max_floors']}
    - Speed: {data['product']['speed']} m/s

    Pricing:
    - Total Price: ${data['pricing']['total_price']}

    Structure the proposal into:
    1. Introduction
    2. Requirements Summary
    3. Proposed Solution
    4. Pricing Overview
    5. Conclusion

    Use professional tone, clear explanation, and persuasive language.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception:
        return "Error generating proposal using LLM."


# ─────────────────────────────────────────────────────────────
# 🧠 Reasoning Function (NEW)
# ─────────────────────────────────────────────────────────────
def generate_reasoning(data):
    prompt = f"""
    You are an expert elevator consultant.

    Explain why the selected product is the best choice based on:

    Requirements:
    - Floors: {data['requirements']['floors']}
    - Capacity: {data['requirements']['capacity']} kg
    - Speed: {data['requirements']['speed']} m/s

    Selected Product:
    - Name: {data['product']['name']}
    - Capacity: {data['product']['capacity']} kg
    - Max Floors: {data['product']['max_floors']}
    - Speed: {data['product']['speed']} m/s

    Write a short professional explanation (3-5 lines).
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception:
        return "The selected product best matches the given requirements based on capacity and specifications."