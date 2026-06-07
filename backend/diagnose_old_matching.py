import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append("backend")

from agents.extraction_agent import extraction_agent
from agents.matching_agent import matching_agent

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

def run_diagnostics():
    for idx, sc in enumerate(scenarios, 1):
        print(f"\n==========================================")
        print(f"RUNNING SCENARIO {sc['id']}: {sc['description']}")
        print(f"==========================================")
        
        # 1. Run Extraction Agent
        reqs, ext_logs = extraction_agent(sc["text"])
        print("\n[Extracted Requirements]")
        for k, v in reqs.items():
            print(f"  {k}: {v} (type: {type(v).__name__})")
            
        # 2. Run Matching Agent
        best, reason, confidence, match_logs, retrieved_products = matching_agent(reqs)
        
        if best:
            print(f"\n[Selected Platform]")
            print(f"  ID: {best['id']}")
            print(f"  Model: {best['name']}")
            print(f"  Tier: {best.get('tier', 'Unknown')}")
            print(f"  Confidence: {confidence}%")
            
            print(f"\n[Retrieved Candidates]")
            for c in retrieved_products:
                print(f"  - ID: {c['id']} ({c['name']}), capacity={c['capacity']}, max_floors={c['max_floors']}, speed={c['speed']}")
                
            print(f"\n[Selection Rationale]")
            print(reason)
        else:
            print("\n[ERROR] No matches returned.")

if __name__ == "__main__":
    run_diagnostics()
