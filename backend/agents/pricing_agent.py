"""
Pricing Agent
-------------
Responsibility: Calculate full cost breakdown for the selected product.
Formula: Total = (Base + Floors×InstallRate + Logistics) × (1 + Margin)
"""

from config import INSTALL_RATE_PER_FLOOR, LOGISTICS_COST, PROFIT_MARGIN


def pricing_agent(product: dict, floors, margin: float = PROFIT_MARGIN) -> tuple[dict, list[str]]:
    logs        = ["[Pricing Agent] Calculating cost breakdown..."]
    base        = product["base_price"]
    floor_count = floors if isinstance(floors, int) else 0
    install     = floor_count * INSTALL_RATE_PER_FLOOR
    logistics   = LOGISTICS_COST
    subtotal    = base + install + logistics
    margin_amt  = round(subtotal * margin, 2)
    total       = round(subtotal + margin_amt, 2)

    logs.append(f"[Pricing Agent] Base price          : ${base:>10,.2f}")
    logs.append(f"[Pricing Agent] Installation cost   : ${install:>10,.2f}  ({floor_count} floors × ${INSTALL_RATE_PER_FLOOR})")
    logs.append(f"[Pricing Agent] Logistics cost      : ${logistics:>10,.2f}  (flat rate)")
    logs.append(f"[Pricing Agent] Subtotal            : ${subtotal:>10,.2f}")
    logs.append(f"[Pricing Agent] Profit margin ({int(margin*100)}%) : ${margin_amt:>10,.2f}")
    logs.append(f"[Pricing Agent] TOTAL               : ${total:>10,.2f}")

    return {
        "base_price":        base,
        "installation_cost": install,
        "logistics_cost":    logistics,
        "profit_margin":     margin_amt,
        "margin_pct":        int(margin * 100),
        "total_price":       total,
    }, logs
