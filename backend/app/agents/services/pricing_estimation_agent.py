from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, HistoricalDataTool
from config import PRODUCTS


class PricingEstimationAgent(BaseElevateAgent):
    """Deterministic Indian elevator quotation estimator.

    Behaves like a sales engineer preparing a quotation for a domestic
    elevator company.  Pure mathematics — no LLM, no AI confidence,
    no hallucination.

    Formula
    -------
    Subtotal       = Platform Cost + Installation + Logistics + Features
    Margin         = Subtotal × 15 %
    Taxable Amount = Subtotal + Margin
    GST            = Taxable Amount × 18 %
    Final Price    = Taxable Amount + GST

    Three scenarios: Economy / Recommended / Premium
    (differ by platform cost interpolation and optional features).
    """

    # ── Constants ────────────────────────────────────────────────────────
    GST_RATE      = 0.18
    MARGIN_RATE   = 0.15
    VALIDITY_DAYS = 90

    # ── Installation rate per floor (INR) by tier ────────────────────────
    INSTALL_RATE_BY_TIER = {
        "Basic":       60_000,
        "Mid":         60_000,
        "High":        75_000,
        "Super":       90_000,
        "Ultra":      120_000,
        "Specialized":150_000,
    }
    DEFAULT_INSTALL_RATE = 60_000

    # ── Logistics (INR) by floor count ───────────────────────────────────
    # ≤25 floors  → ₹50,000
    # 26–50       → ₹1,00,000
    # >50         → ₹2,00,000

    # ── Delivery time by tier ────────────────────────────────────────────
    DELIVERY_WEEKS = {
        "Basic":       "8–10 weeks",
        "Mid":         "10–12 weeks",
        "High":        "14–16 weeks",
        "Super":       "18–20 weeks",
        "Ultra":       "20–24 weeks",
        "Specialized": "14–20 weeks",
    }

    # ── Warranty ─────────────────────────────────────────────────────────
    WARRANTY_STANDARD_MONTHS = 24
    WARRANTY_PREMIUM_MONTHS  = 36

    # ── Optional feature cost table (INR) ────────────────────────────────
    FEATURE_COSTS = {
        "ARD System":              80_000,
        "Voice Announcement":      40_000,
        "Braille Buttons":         20_000,
        "CCTV Monitoring":         60_000,
        "Emergency Alarm":         25_000,
        "Intercom":                30_000,
        "Fire Service Mode":      120_000,
        "IoT Monitoring":         200_000,
        "Destination Control":    350_000,
        "Touchless Controls":     100_000,
        "Regenerative Drive":     250_000,
        "Premium Interior Finish":300_000,
        "Access Control System":  150_000,
        "Overload Protection":     15_000,
    }

    # ── Mandatory safety features (always included, never optional) ──────
    MANDATORY_ALWAYS = ["Emergency Alarm", "Overload Protection"]

    # ── Feature sets for each scenario ───────────────────────────────────
    ECONOMY_FEATURES = [
        # Only mandatory items — added automatically
    ]
    RECOMMENDED_FEATURES = [
        "ARD System",
        "Voice Announcement",
        "Braille Buttons",
        "Intercom",
    ]
    PREMIUM_FEATURES = [
        "ARD System",
        "Voice Announcement",
        "Braille Buttons",
        "CCTV Monitoring",
        "Intercom",
        "IoT Monitoring",
        "Destination Control",
        "Touchless Controls",
        "Regenerative Drive",
        "Premium Interior Finish",
    ]

    # ── Engineering exclusions ───────────────────────────────────────────
    ENGINEERING_EXCLUSIONS = [
        "Civil work (shaft walls, plastering, waterproofing)",
        "Shaft construction and scaffolding",
        "Pit construction and waterproofing",
        "Machine room construction (if applicable)",
        "Electrical infrastructure upgrades (transformer, cabling, earthing)",
        "Government approvals, permits and inspections",
        "Building modifications and structural reinforcement",
        "Architectural finishes outside elevator car and landing",
        "Fire NOC and statutory approvals",
    ]

    def __init__(self):
        super().__init__(
            name="pricing_estimator",
            role="Senior Sales Engineer — Quotation Division",
            goal="Generate accurate, deterministic elevator quotations in INR",
            backstory="""You are a senior sales engineer preparing quotations 
            for a domestic Indian elevator company. You produce transparent, 
            explainable cost breakdowns with zero guesswork.""",
        )

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute deterministic pricing estimation."""
        start_time = datetime.now()

        try:
            requirements    = context.get("requirements", {})
            product_matches = context.get("product_matches", {})
            risk_assessment = context.get("risk_assessment", {})

            if not requirements or not product_matches:
                raise ValueError("Requirements and product matches required for pricing")

            basic_req = requirements.get("basic_requirements", {})
            floors    = basic_req.get("max_floors") or 10
            building_type = (basic_req.get("building_type") or "").lower()
            lift_type     = (basic_req.get("lift_type") or "").lower()

            # ── Extract platform details ─────────────────────────────────
            primary_product = self._get_primary_product(product_matches)
            platform        = self._lookup_platform(primary_product.get("product_id"))
            tier            = platform.get("tier", "Mid")

            # ── Mandatory features (context-dependent) ───────────────────
            mandatory_features = self._determine_mandatory_features(
                floors, building_type, lift_type,
            )

            # ── Build 3 scenarios ────────────────────────────────────────
            economy_result = self._calculate_scenario(
                "economy", platform, tier, floors,
                mandatory_features, self.ECONOMY_FEATURES,
                building_type,
            )
            recommended_result = self._calculate_scenario(
                "recommended", platform, tier, floors,
                mandatory_features, self.RECOMMENDED_FEATURES,
                building_type,
            )
            premium_result = self._calculate_scenario(
                "premium", platform, tier, floors,
                mandatory_features, self.PREMIUM_FEATURES,
                building_type,
            )

            # The "recommended" scenario is the primary quotation
            primary_breakdown = recommended_result

            # ── Alternative product pricing ──────────────────────────────
            alt_pricing = self._calculate_alternative_pricing(
                product_matches, tier, floors, mandatory_features, building_type,
            )

            # ── Build result ─────────────────────────────────────────────
            scenarios = {
                "economy": {
                    "description": "Essential configuration with mandatory safety features only",
                    "total_price": economy_result["final_price"],
                    "components_breakdown": economy_result["components"],
                    "rationale": "Minimum viable configuration meeting all safety standards",
                },
                "recommended": {
                    "description": "Balanced solution with recommended comfort and safety features",
                    "total_price": recommended_result["final_price"],
                    "components_breakdown": recommended_result["components"],
                    "rationale": "Industry-standard configuration for building type and platform tier",
                },
                "premium": {
                    "description": "Maximum comfort, technology and premium finishes",
                    "total_price": premium_result["final_price"],
                    "components_breakdown": premium_result["components"],
                    "rationale": "Full-featured premium configuration with all available upgrades",
                },
            }

            # Backward-compat pricing_breakdown uses "recommended" scenario
            pricing_breakdown = {
                "components": primary_breakdown["components"],
                "subtotal":   primary_breakdown["subtotal"],
                "margin_rate":   self.MARGIN_RATE,
                "margin_amount": primary_breakdown["margin_amount"],
                "tax_rate":      self.GST_RATE,
                "tax_amount":    primary_breakdown["gst_amount"],
                "total_price":   primary_breakdown["final_price"],
                "primary_product_details": primary_product,
                "add_on_details":   primary_breakdown["feature_details"],
                "cost_per_floor":   round(primary_breakdown["final_price"] / max(1, floors), 2),
                "alternative_pricing": alt_pricing,
            }

            result = {
                "pricing_specifications": {
                    "capacity_kg":  basic_req.get("capacity_kg"),
                    "max_floors":   floors,
                    "speed_ms":     basic_req.get("speed_ms"),
                    "building_type": basic_req.get("building_type"),
                    "lift_type":     basic_req.get("lift_type"),
                },
                "base_pricing": {
                    "primary_product": {
                        **primary_product,
                        "floor_cost":      primary_breakdown["installation_cost"],
                        "logistics_cost":  primary_breakdown["logistics_cost"],
                        "total_price":     primary_breakdown["final_price"],
                    },
                },
                "installation_costs": {
                    "base_installation":       primary_breakdown["installation_cost"],
                    "floor_rate":              self.INSTALL_RATE_BY_TIER.get(tier, self.DEFAULT_INSTALL_RATE),
                    "floors":                  floors,
                    "tier":                    tier,
                    "total_installation_cost": primary_breakdown["installation_cost"],
                },
                "customization_costs": {
                    "total_customization":   primary_breakdown["feature_total"],
                    "customization_details": primary_breakdown["feature_details"],
                    "mandatory_features":    primary_breakdown["mandatory_details"],
                    "optional_features":     primary_breakdown["optional_details"],
                },
                "compliance_costs": {"total_compliance_cost": 0},
                "risk_adjustments": {
                    "risk_level":      "low",
                    "risk_multiplier": 1.0,
                    "risk_adjustment": 0,
                },
                "historical_pricing": [],
                "pricing_breakdown": pricing_breakdown,
                "pricing_scenarios": scenarios,
                "pricing_metadata": {
                    "total_estimate":       primary_breakdown["final_price"],
                    "confidence_level":     1.0,
                    "pricing_confidence":   1.0,
                    "competitive_position": self._competitive_position(
                        primary_breakdown["final_price"], tier,
                    ),
                    "pricing_risks":        [],
                    "cost_basis":           "deterministic",
                    "platform_tier":        tier,
                    "gst_rate":             self.GST_RATE,
                    "margin_rate":          self.MARGIN_RATE,
                    "currency":             "INR",
                },
                "quotation_details": {
                    "validity_days":          self.VALIDITY_DAYS,
                    "delivery_time":          self.DELIVERY_WEEKS.get(tier, "12–16 weeks"),
                    "warranty_standard":      f"{self.WARRANTY_STANDARD_MONTHS} months",
                    "warranty_premium":       f"{self.WARRANTY_PREMIUM_MONTHS} months",
                    "amc_standard_per_year":  50_000,
                    "amc_premium_per_year":  120_000,
                    "engineering_exclusions": self.ENGINEERING_EXCLUSIONS,
                },
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                "[Pricing] %s tier, %d floors, %s — "
                "Economy=INR %s / Recommended=INR %s / Premium=INR %s",
                tier, floors, building_type or "?",
                f"{economy_result['final_price']:,.0f}",
                f"{recommended_result['final_price']:,.0f}",
                f"{premium_result['final_price']:,.0f}",
            )

            self.add_reasoning_trace(
                step="pricing_calculation",
                reasoning=(
                    f"Deterministic quotation: {tier} tier, {floors} floors. "
                    f"Recommended total: INR {recommended_result['final_price']:,.0f}"
                ),
                evidence=[{
                    "economy": economy_result["final_price"],
                    "recommended": recommended_result["final_price"],
                    "premium": premium_result["final_price"],
                }],
                confidence=1.0,
            )

            return AgentResult(
                agent_name=self.name,
                result=result,
                reasoning_traces=self.reasoning_traces,
                confidence_score=1.0,
                execution_time=execution_time,
                retrieved_context=[],
                citations=[],
            )

        except Exception as e:
            self.logger.error(f"Pricing estimation failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  SCENARIO CALCULATION
    # ══════════════════════════════════════════════════════════════════════

    def _calculate_scenario(
        self,
        scenario_name: str,
        platform: Dict[str, Any],
        tier: str,
        floors: int,
        mandatory_features: List[str],
        scenario_optional_features: List[str],
        building_type: str,
    ) -> Dict[str, Any]:
        """Calculate a complete pricing scenario."""

        # ── 1. Platform cost ─────────────────────────────────────────────
        starting  = platform.get("starting_price", platform.get("base_price", 2_000_000))
        maximum   = platform.get("maximum_price", starting)
        price_range = maximum - starting

        if scenario_name == "economy":
            platform_cost = starting
        elif scenario_name == "recommended":
            platform_cost = starting + int(price_range * 0.30)
        else:  # premium
            platform_cost = starting + int(price_range * 0.70)

        # ── 2. Installation cost ─────────────────────────────────────────
        rate = self.INSTALL_RATE_BY_TIER.get(tier, self.DEFAULT_INSTALL_RATE)
        installation_cost = floors * rate

        # ── 3. Logistics ─────────────────────────────────────────────────
        if floors > 50:
            logistics_cost = 200_000
        elif floors > 25:
            logistics_cost = 100_000
        else:
            logistics_cost = 50_000

        # ── 4. Features ──────────────────────────────────────────────────
        mandatory_details: List[Dict[str, Any]] = []
        optional_details:  List[Dict[str, Any]] = []

        # Mandatory features always included
        for feat in mandatory_features:
            cost = self.FEATURE_COSTS.get(feat, 0)
            mandatory_details.append({
                "type": feat, "cost": cost, "category": "mandatory",
            })

        # Scenario optional features (deduplicate against mandatory)
        mandatory_names = {f["type"] for f in mandatory_details}
        for feat in scenario_optional_features:
            if feat not in mandatory_names:
                cost = self.FEATURE_COSTS.get(feat, 0)
                if cost > 0:
                    optional_details.append({
                        "type": feat, "cost": cost, "category": "optional",
                    })

        all_features = mandatory_details + optional_details
        feature_total = sum(f["cost"] for f in all_features)

        # ── 5. Totals ───────────────────────────────────────────────────
        subtotal = platform_cost + installation_cost + logistics_cost + feature_total

        margin_amount  = round(subtotal * self.MARGIN_RATE)
        taxable_amount = subtotal + margin_amount
        gst_amount     = round(taxable_amount * self.GST_RATE)
        final_price    = taxable_amount + gst_amount

        components = {
            "platform_cost":      platform_cost,
            "installation_cost":  installation_cost,
            "logistics_cost":     logistics_cost,
            "feature_cost":       feature_total,
        }

        return {
            "scenario":          scenario_name,
            "platform_cost":     platform_cost,
            "installation_cost": installation_cost,
            "logistics_cost":    logistics_cost,
            "feature_total":     feature_total,
            "feature_details":   all_features,
            "mandatory_details": mandatory_details,
            "optional_details":  optional_details,
            "subtotal":          subtotal,
            "margin_amount":     margin_amount,
            "taxable_amount":    taxable_amount,
            "gst_amount":        gst_amount,
            "final_price":       final_price,
            "components":        components,
        }

    # ══════════════════════════════════════════════════════════════════════
    #  MANDATORY FEATURE DETERMINATION
    # ══════════════════════════════════════════════════════════════════════

    def _determine_mandatory_features(
        self, floors: int, building_type: str, lift_type: str,
    ) -> List[str]:
        """Determine which features are mandatory for this project."""

        mandatory = list(self.MANDATORY_ALWAYS)  # Emergency Alarm, Overload Protection

        # ARD mandatory for high-rise, commercial, hospital
        is_high_rise = floors > 8  # >24m at ~3m per floor
        if is_high_rise or building_type in ("commercial", "office", "hospital", "hotel"):
            if "ARD System" not in mandatory:
                mandatory.append("ARD System")

        # Fire Service Mode mandatory for buildings >24m height (NBC India)
        if is_high_rise or building_type == "hospital":
            if "Fire Service Mode" not in mandatory:
                mandatory.append("Fire Service Mode")

        return mandatory

    # ══════════════════════════════════════════════════════════════════════
    #  PRODUCT / PLATFORM HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _get_primary_product(self, product_matches: Dict) -> Dict[str, Any]:
        """Extract primary product metadata — backward compatible."""
        try:
            rec  = product_matches.get("recommendations", {}).get("primary_recommendation", {})
            prod = rec.get("product", {})
            meta = prod.get("metadata", prod)
            return {
                "product_id":       meta.get("product_id", "unknown"),
                "model":            meta.get("model", "Unknown Model"),
                "base_price":       meta.get("base_price", 0),
                "capacity_kg":      meta.get("capacity_kg", 0),
                "max_floors":       meta.get("max_floors", 0),
                "speed_ms":         meta.get("speed_ms", 0),
                "tier":             meta.get("tier", "Mid"),
                "confidence_score": prod.get("confidence_score",
                                    prod.get("coverage_score", 0.0)),
            }
        except Exception:
            return {
                "product_id": "fallback", "model": "Fallback",
                "base_price": 2_000_000, "capacity_kg": 0,
                "max_floors": 0, "speed_ms": 0, "tier": "Basic",
                "confidence_score": 0,
            }

    def _lookup_platform(self, product_id: str) -> Dict[str, Any]:
        """Look up full platform data from PRODUCTS catalog."""
        for p in PRODUCTS:
            if p["id"] == product_id:
                return p
        # Fallback — return a minimal dict
        return {
            "id": product_id,
            "starting_price": 2_000_000,
            "maximum_price":  3_200_000,
            "tier": "Basic",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  ALTERNATIVE PRICING
    # ══════════════════════════════════════════════════════════════════════

    def _calculate_alternative_pricing(
        self,
        product_matches: Dict,
        primary_tier: str,
        floors: int,
        mandatory_features: List[str],
        building_type: str,
    ) -> List[Dict]:
        """Calculate recommended-scenario pricing for alternative products."""

        alts = product_matches.get("recommendations", {}).get("alternative_options", [])
        alt_pricing = []

        for alt_opt in alts[:2]:
            prod = alt_opt.get("product", {})
            meta = prod.get("metadata", prod)
            pid  = meta.get("product_id", "unknown")

            platform = self._lookup_platform(pid)
            tier = platform.get("tier", primary_tier)

            result = self._calculate_scenario(
                "recommended", platform, tier, floors,
                mandatory_features, self.RECOMMENDED_FEATURES,
                building_type,
            )

            alt_pricing.append({
                "product":         pid,
                "model":           meta.get("model", ""),
                "tier":            tier,
                "base_price":      platform.get("starting_price", meta.get("base_price", 0)),
                "estimated_total": result["final_price"],
            })

        return alt_pricing

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITIES
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _competitive_position(total: float, tier: str) -> str:
        """Determine market position based on total and tier."""
        tier_thresholds = {
            "Basic":       (40_00_000, 60_00_000),
            "Mid":         (60_00_000, 100_00_000),
            "High":        (100_00_000, 160_00_000),
            "Super":       (140_00_000, 220_00_000),
            "Ultra":       (220_00_000, 400_00_000),
            "Specialized": (150_00_000, 500_00_000),
        }
        low, high = tier_thresholds.get(tier, (50_00_000, 150_00_000))
        if total <= low:
            return "competitive"
        if total <= high:
            return "market_rate"
        return "premium"

    def get_tools(self) -> List:
        """Get agent-specific tools."""
        return [KnowledgeSearchTool(), HistoricalDataTool()]