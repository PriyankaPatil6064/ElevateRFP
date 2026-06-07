"""
Orchestrator Agent
------------------
Responsibility: Control the full agent pipeline execution sequence.
Flow: Sales → Extraction → Matching → Pricing → Response
Collects logs from every agent and returns a unified result dict.
"""

from .sales_agent      import sales_agent
from .extraction_agent import extraction_agent
from .matching_agent   import matching_agent
from .pricing_agent    import pricing_agent
from .response_agent   import response_agent


def orchestrator(file) -> dict:
    all_logs = ["[Orchestrator] Pipeline started. Invoking agents in sequence..."]

    # Step 1 — Sales Agent: parse & validate PDF
    text, logs = sales_agent(file)
    all_logs  += logs

    # Step 2 — Extraction Agent: mine requirements
    requirements, logs = extraction_agent(text)
    all_logs           += logs

    # Step 3 — Matching Agent: select best product
    product, reason, confidence, logs, retrieved_products = matching_agent(requirements)
    all_logs              += logs

    if not product:
        all_logs.append("[Orchestrator] Pipeline halted — no matching product found.")
        return {
            "error":        reason,
            "requirements": requirements,
            "agent_logs":   all_logs,
        }

    # Step 4 — Pricing Agent: calculate costs
    pricing, logs = pricing_agent(product, requirements.get("floors"))
    all_logs      += logs

    # Step 5 — Response Agent: generate proposal
    proposal, logs = response_agent(requirements, product, pricing, reason)
    all_logs       += logs

    all_logs.append("[Orchestrator] Pipeline completed successfully.")

    return {
        "requirements": requirements,
        "product":      product,
        "match_reason": reason,
        "pricing":      pricing,
        "response":     proposal,
        "preview":      text[:400],
        "agent_logs":   all_logs,
        "confidence": confidence,
        "retrieved_products": retrieved_products
    }
