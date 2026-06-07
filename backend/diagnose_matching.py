import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append("backend")

from app.agents.services.requirement_analysis_agent import RequirementAnalysisAgent
from app.agents.services.product_matching_agent import ProductMatchingAgent

scenarios = [
    {
        "id": 1,
        "description": "Scenario 1: Residential, 800 kg, 10 floors, 1.0 m/s",
        "text": "This is a Residential building project. The elevator should have a capacity of 800 kg. There are 10 floors. The speed of the lift should be 1.0 m/s."
    },
    {
        "id": 2,
        "description": "Scenario 2: Commercial, 1600 kg, 30 floors, 2.5 m/s",
        "text": "This is a Commercial building. The lift type required is Passenger. The capacity of the lift is 1600 kg. The building has 30 floors. The elevator speed must be 2.5 m/s."
    },
    {
        "id": 3,
        "description": "Scenario 3: Hospital, 2000 kg, 40 floors, 3.5 m/s",
        "text": "We need an elevator for a Hospital. The lift type is Passenger (stretcher lift). The required capacity is 2000 kg. The building has 40 floors. The speed is 3.5 m/s."
    },
    {
        "id": 4,
        "description": "Scenario 4: Freight elevator, 5000 kg, 20 floors",
        "text": "This is a Warehouse project requiring a heavy-duty freight elevator. The elevator capacity must be 5000 kg. It needs to serve 20 floors."
    },
    {
        "id": 5,
        "description": "Scenario 5: Skyscraper, 3500 kg, 100 floors, 7.0 m/s",
        "text": "This is a luxury Skyscraper project. The lift type is Passenger. The capacity is 3500 kg. The building has 100 floors. The speed of the elevator must be 7.0 m/s."
    }
]

async def run_diagnostics():
    req_agent = RequirementAnalysisAgent()
    match_agent = ProductMatchingAgent()

    for idx, sc in enumerate(scenarios, 1):
        print(f"\n==========================================")
        print(f"RUNNING SCENARIO {sc['id']}: {sc['description']}")
        print(f"==========================================")
        
        # 1. Run Requirement Analysis
        req_res = await req_agent.execute({"rfp_content": sc["text"]})
        basic_reqs = req_res.result["basic_requirements"]
        
        # 2. Run Product Matching
        match_res = await match_agent.execute({"requirements": req_res.result})
        match_data = match_res.result
        
        # Extract requested outputs
        print("\n[Extracted Requirements]")
        for k, v in basic_reqs.items():
            if k in ["project_name", "building_type", "lift_type", "capacity_kg", "speed_ms", "max_floors", "stops", "number_of_openings", "door_type", "special_requirements"]:
                print(f"  {k}: {v}")
        
        product_matches = match_data.get("product_matches", [])
        if product_matches:
            print("\n--- Detailed Platform Scores (Top 3) ---")
            for m in product_matches[:3]:
                print(f"Platform: {m['product_id']} ({m['metadata']['model']})")
                print(f"  Coverage Score: {m['coverage_score']:.4f}")
                print(f"  Dimension Scores: {m['specification_scores']}")
                # Let's print details
                meta = m["metadata"]
                print(f"  Product details in metadata: capacity={meta.get('capacity_kg')}, max_floors={meta.get('max_floors')}, speed={meta.get('speed_ms')}")
            
            primary = product_matches[0]
            print(f"\n[Selected Platform]")
            print(f"  ID: {primary['product_id']}")
            print(f"  Model: {primary['metadata']['model']}")
            print(f"  Tier: {primary['metadata']['tier']}")
            print(f"  Coverage Score: {primary['coverage_score']:.4f}")
            
            print(f"\n[Dimension Scores]")
            for dim, score in primary["specification_scores"].items():
                print(f"  {dim}: {score}")
                
            print(f"\n[Coverage Score] (computed active/total_weight): {primary['coverage_score']}")
            
            print(f"\n[Alternative Platforms]")
            for alt in product_matches[1:]:
                print(f"  - ID: {alt['product_id']} ({alt['metadata']['model']}), Coverage Score: {alt['coverage_score']:.4f}")
                
            print(f"\n[Selection Rationale]")
            print(primary["selection_rationale"])
        else:
            print("\n[ERROR] No matches returned.")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
