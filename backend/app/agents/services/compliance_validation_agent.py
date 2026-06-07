from typing import Dict, Any, List
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, ComplianceCheckTool
from config import PRODUCTS


class ComplianceValidationAgent(BaseElevateAgent):
    """Standards & Safety Agent — validates elevator solutions against
    industry standards and safety requirements.

    Primary standards evaluated:
        EN 81-20/50   — European Elevator Safety Standard       (weight 25%)
        ASME A17.1    — Safety Code for Elevators                (weight 25%)
        IS 14665      — Indian Standard for Lifts & Escalators   (weight 20%)
        IS 15785      — Indian Accessibility Standard            (weight 10%)
        ISO 25745     — Energy Performance of Lifts              (weight 20%)

    Domain categories:
        Safety Features        — Emergency Alarm, ARD, Overload, Intercom,
                                 Fire Service Mode, Emergency Lighting
        Accessibility Features — Braille, Voice, Handrails, Mirror, Wheelchair
        Energy Efficiency      — LED, Standby, VVVF, Regenerative, Class
        Fire Safety            — Fire Service Mode, Emergency Lighting,
                                 Fire-Rated Doors

    Language rules:
        Use "Designed in accordance with" or "Recommended under".
        Never use "Certified" or "Approved" — certification requires
        statutory inspection.
    """

    # ── Constants ─────────────────────────────────────────────────────────
    FIRE_SERVICE_HEIGHT_M = 24   # NBC India threshold
    FLOOR_HEIGHT_M        = 3.0  # assumed average floor-to-floor

    # ── Framework definitions (deterministic, rule-based) ─────────────────
    FRAMEWORKS = {
        "ASME_A17_1": {
            "name": "ASME A17.1 — Safety Code for Elevators",
            "weight": 0.25,
            "checks": [
                ("capacity_adequate",   "Product capacity meets or exceeds requirement"),
                ("speed_compliant",     "Operating speed within published limits for building height"),
                ("safety_features",     "Safety features (emergency, intercom, alarm) present"),
                ("machine_room",        "Machine room or MRL configuration addressed"),
            ],
        },
        "EN_81": {
            "name": "EN 81-20/50 — European Elevator Safety Standard",
            "weight": 0.25,
            "checks": [
                ("load_rating",         "Passenger elevator capacity >= 630 kg (EN 81-20 minimum)"),
                ("door_protection",     "Door type clearly specified"),
                ("overload_protection", "Overload detection / sensor mentioned"),
                ("emergency_operation", "Emergency / battery operation mentioned"),
            ],
        },
        "IS_14665": {
            "name": "IS 14665 — Indian Standard for Lifts & Escalators",
            "weight": 0.20,
            "checks": [
                ("safety_features_is",  "Emergency alarm and overload protection present"),
                ("fire_service_mode",   "Fire service mode addressed for applicable buildings"),
                ("ard_system",          "Automatic Rescue Device present for applicable buildings"),
            ],
        },
        "IS_15785": {
            "name": "IS 15785 — Accessibility Requirements for Lifts",
            "weight": 0.10,
            "checks": [
                ("braille_buttons",     "Braille buttons available on platform"),
                ("wheelchair_access",   "Car capacity sufficient for wheelchair accessibility (>= 680 kg)"),
                ("voice_announcement",  "Voice announcement available or recommended"),
            ],
        },
        "ISO_25745": {
            "name": "ISO 25745 — Energy Performance of Lifts",
            "weight": 0.20,
            "checks": [
                ("energy_class",        "Energy-efficient drive system mentioned or available"),
                ("standby_power",       "Standby / sleep mode mentioned or recommended"),
                ("usage_category",      "Building type allows usage-category determination"),
            ],
        },
    }

    def __init__(self):
        super().__init__(
            name="compliance_validator",
            role="Standards & Safety Specialist",
            goal="Validate elevator solutions against industry standards and safety requirements",
            backstory="""You are a standards and safety specialist with 20+ years of 
            experience in elevator industry compliance. You validate solutions against 
            EN 81, ASME A17.1, IS 14665, IS 15785, and ISO 25745. You focus on 
            practical, elevator-domain standards — not generic software frameworks."""
        )

    # ══════════════════════════════════════════════════════════════════════
    #  EXECUTE
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute standards and safety validation — pure rule-based."""
        start_time = datetime.now()

        try:
            requirements    = context.get("requirements", {})
            product_matches = context.get("product_matches", {})

            if not requirements:
                raise ValueError("No requirements provided for standards validation")

            basic_req   = requirements.get("basic_requirements", {})
            rfp_content = context.get("rfp_content", "")
            text_lower  = rfp_content.lower() if rfp_content else ""
            all_req_text = self._gather_all_requirement_text(requirements)

            # Primary product and platform lookup
            primary_product = self._get_primary_product(product_matches)
            platform = self._lookup_platform(primary_product.get("product_id", ""))

            floors        = basic_req.get("max_floors") or 10
            building_type = basic_req.get("building_type", "")
            capacity      = primary_product.get("capacity_kg",
                                                basic_req.get("capacity_kg", 0))

            # ── Evaluate each framework (backward-compatible) ─────────
            framework_results: Dict[str, Dict[str, Any]] = {}

            for fw_key, fw_def in self.FRAMEWORKS.items():
                checks_passed, checks_total, details, gaps = self._evaluate_framework(
                    fw_key, fw_def, basic_req, primary_product, platform,
                    text_lower, all_req_text
                )

                score = checks_passed / checks_total if checks_total else 0.0

                if score >= 0.75:
                    status = "compliant"
                elif score >= 0.50:
                    status = "partially_compliant"
                else:
                    status = "non_compliant"

                framework_results[fw_key] = {
                    "name":          fw_def["name"],
                    "score":         round(score, 3),
                    "status":        status,
                    "checks_passed": checks_passed,
                    "checks_total":  checks_total,
                    "details":       details,
                    "gaps":          gaps,
                }

                self.add_reasoning_trace(
                    step=f"framework_{fw_key}",
                    reasoning=f"{fw_key}: {checks_passed}/{checks_total} checks passed -> {status}",
                    evidence=[{"score": score, "gaps": gaps}],
                    confidence=0.92,
                )

            # ── Compliance gaps (backward-compatible) ─────────────────
            compliance_gaps = self._collect_gaps(framework_results)

            # ── Compliance matrix (backward-compatible) ───────────────
            overall_score = sum(
                framework_results[k]["score"] * self.FRAMEWORKS[k]["weight"]
                for k in framework_results
            )

            if overall_score >= 0.75 and not any(
                g["severity"] == "critical" for g in compliance_gaps
            ):
                compliance_status = "compliant"
            elif overall_score >= 0.50:
                compliance_status = "partially_compliant"
            else:
                compliance_status = "non_compliant"

            compliance_matrix = {
                "framework_summary": {
                    k: {
                        "status":             v["status"],
                        "score":              v["score"],
                        "requirements_count": v["checks_total"],
                        "gaps_count":         len(v["gaps"]),
                    }
                    for k, v in framework_results.items()
                },
                "gap_summary": {
                    "total_gaps":    len(compliance_gaps),
                    "critical_gaps": len([g for g in compliance_gaps if g["severity"] == "critical"]),
                    "medium_gaps":   len([g for g in compliance_gaps if g["severity"] == "medium"]),
                    "low_gaps":      len([g for g in compliance_gaps if g["severity"] == "low"]),
                },
                "compliance_status": compliance_status,
                "overall_score":     round(overall_score, 3),
            }

            # ── Remediation plan (backward-compatible) ────────────────
            remediation_plan = self._build_remediation_plan(compliance_gaps)

            # ── NEW domain-specific sections ──────────────────────────
            standards_compliance   = self._build_standards_compliance(
                basic_req, primary_product, platform, framework_results
            )
            safety_features        = self._build_safety_features(
                floors, building_type, platform
            )
            accessibility_features = self._build_accessibility_features(
                capacity, building_type, platform
            )
            energy_efficiency      = self._build_energy_efficiency(
                floors, platform
            )
            fire_safety            = self._build_fire_safety(
                floors, building_type
            )
            compliance_notes       = self._build_compliance_notes()

            # ── Assemble result ───────────────────────────────────────
            result = {
                # Backward-compatible keys (frozen)
                "compliance_requirements": {
                    k: v["gaps"] for k, v in framework_results.items()
                },
                "compliance_results":  framework_results,
                "product_compliance":  {},
                "compliance_gaps":     compliance_gaps,
                "compliance_matrix":   compliance_matrix,
                "remediation_plan":    remediation_plan,

                # New domain-specific keys
                "standards_compliance":   standards_compliance,
                "safety_features":        safety_features,
                "accessibility_features": accessibility_features,
                "energy_efficiency":      energy_efficiency,
                "fire_safety":            fire_safety,
                "compliance_notes":       compliance_notes,

                # Metadata (backward-compatible + expanded)
                "compliance_metadata": {
                    # Existing keys
                    "frameworks_evaluated":   len(framework_results),
                    "total_requirements":     sum(
                        v["checks_total"] for v in framework_results.values()
                    ),
                    "compliance_score":       round(overall_score, 3),
                    "critical_gaps":          compliance_matrix["gap_summary"]["critical_gaps"],
                    "validation_confidence":  self._calculate_validation_confidence(),
                    # New keys
                    "standards_checked": [
                        "EN 81-20/50", "ASME A17.1",
                        "IS 14665", "IS 15785", "ISO 25745",
                    ],
                    "safety_features_count":        len(safety_features),
                    "accessibility_features_count": len(accessibility_features),
                    "energy_features_count":        len(energy_efficiency),
                    "fire_safety_count":            len(fire_safety),
                },
            }

            self.add_reasoning_trace(
                step="compliance_summary",
                reasoning=f"Overall compliance: {compliance_status} ({overall_score:.0%})",
                evidence=[compliance_matrix],
                confidence=0.90,
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                agent_name=self.name,
                result=result,
                reasoning_traces=self.reasoning_traces,
                confidence_score=result["compliance_metadata"]["validation_confidence"],
                execution_time=execution_time,
                retrieved_context=[],
                citations=[],
            )

        except Exception as e:
            self.logger.error(f"Standards validation failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  PLATFORM LOOKUP
    # ══════════════════════════════════════════════════════════════════════

    def _lookup_platform(self, product_id: str) -> Dict[str, Any]:
        """Look up full platform data from PRODUCTS catalog."""
        for p in PRODUCTS:
            if p["id"] == product_id:
                return p
        return {
            "id": product_id or "unknown",
            "name": "Elevator Platform",
            "tier": "Mid",
            "description": "Elevator platform",
            "supported_lift_types": ["Passenger", "Traction"],
            "recommended_capacity_range": {"min": 0, "max": 0},
            "recommended_floor_range":    {"min": 0, "max": 0},
            "recommended_speed_range":    {"min": 0, "max": 0},
            "energy_efficiency_class": "A",
            "recommended_use_cases": [],
            "premium_features_available": [],
        }

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITY HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _is_high_rise(self, floors: int) -> bool:
        """Building exceeds 24 m height (NBC India fire safety threshold)."""
        return floors * self.FLOOR_HEIGHT_M > self.FIRE_SERVICE_HEIGHT_M

    def _is_commercial_or_institutional(self, building_type: str) -> bool:
        """Building type is commercial, hospital, hotel, or institutional."""
        bt = building_type.lower() if building_type else ""
        return any(t in bt for t in [
            "commercial", "office", "hospital", "hotel", "mixed",
            "government", "airport", "transit", "industrial", "warehouse",
        ])

    def _has_gearless_traction(self, platform: Dict) -> bool:
        """Platform supports gearless traction drive."""
        return "Gearless Traction" in platform.get("supported_lift_types", [])

    def _feature_available(self, feature_name: str, platform: Dict) -> bool:
        """Check if a feature is listed on the platform."""
        return feature_name in platform.get("premium_features_available", [])

    # ══════════════════════════════════════════════════════════════════════
    #  FRAMEWORK EVALUATION (backward-compatible)
    # ══════════════════════════════════════════════════════════════════════

    def _evaluate_framework(
        self,
        fw_key: str,
        fw_def: Dict,
        basic_req: Dict,
        product: Dict,
        platform: Dict,
        text_lower: str,
        all_req_text: str,
    ):
        """Run all checks for one framework. Returns (passed, total, details, gaps)."""
        combined_text = (text_lower + " " + all_req_text).lower()
        checks = fw_def["checks"]
        passed = 0
        details: List[Dict[str, Any]] = []
        gaps: List[str] = []

        for check_id, description in checks:
            ok = self._run_check(
                check_id, fw_key, basic_req, product, platform, combined_text
            )
            if ok:
                passed += 1
            else:
                gaps.append(description)
            details.append({
                "check": check_id, "description": description, "passed": ok
            })

        return passed, len(checks), details, gaps

    def _run_check(
        self,
        check_id: str,
        fw_key: str,
        basic_req: Dict,
        product: Dict,
        platform: Dict,
        text: str,
    ) -> bool:
        """Evaluate a single deterministic check."""

        req_capacity  = basic_req.get("capacity_kg")
        req_floors    = basic_req.get("max_floors") or 10
        prod_capacity = product.get("capacity_kg", 0) if product else 0
        prod_speed    = product.get("speed_ms", 0) if product else 0
        building_type = basic_req.get("building_type", "")

        # ── ASME A17.1 ───────────────────────────────────────────────────
        if check_id == "capacity_adequate":
            if not req_capacity:
                return True
            return prod_capacity >= req_capacity

        if check_id == "speed_compliant":
            if not req_floors:
                return True
            if req_floors <= 20:
                return prod_speed <= 3.5
            if req_floors <= 50:
                return prod_speed <= 6.0
            return prod_speed <= 12.0

        if check_id == "safety_features":
            safety_words = ["emergency", "safety", "intercom", "alarm", "fire"]
            return any(w in text for w in safety_words)

        if check_id == "machine_room":
            return any(w in text for w in [
                "machine room", "mrl", "machine-room-less", "roomless"
            ])

        # ── EN 81-20/50 ──────────────────────────────────────────────────
        if check_id == "load_rating":
            if not req_capacity:
                return prod_capacity >= 630
            return prod_capacity >= 630

        if check_id == "door_protection":
            return any(w in text for w in [
                "door", "opening", "telescopic", "sliding", "automatic door"
            ])

        if check_id == "overload_protection":
            return any(w in text for w in [
                "overload", "sensor", "load weighing", "load sensor"
            ])

        if check_id == "emergency_operation":
            return any(w in text for w in [
                "emergency", "battery", "ard", "rescue", "backup"
            ])

        # ── IS 14665 ─────────────────────────────────────────────────────
        if check_id == "safety_features_is":
            return any(w in text for w in [
                "emergency", "alarm", "overload", "safety"
            ])

        if check_id == "fire_service_mode":
            # Below 24 m: not applicable → pass (no gap)
            if not self._is_high_rise(req_floors):
                return True
            # Above 24 m: check if fire service is addressed
            return (
                any(w in text for w in ["fire", "firefighter", "fire service"])
                or self._is_commercial_or_institutional(building_type)
            )

        if check_id == "ard_system":
            # Not required for low-rise residential
            if req_floors <= 8 and not self._is_commercial_or_institutional(building_type):
                return True
            return (
                any(w in text for w in ["ard", "rescue", "automatic rescue"])
                or self._feature_available("ARD (Automatic Rescue Device)", platform)
            )

        # ── IS 15785 ─────────────────────────────────────────────────────
        if check_id == "braille_buttons":
            return (
                any(w in text for w in ["braille", "tactile"])
                or self._feature_available("Braille Buttons", platform)
            )

        if check_id == "wheelchair_access":
            return prod_capacity >= 680

        if check_id == "voice_announcement":
            return (
                any(w in text for w in ["voice", "announcement", "audio"])
                or self._feature_available("Voice Announcement", platform)
            )

        # ── ISO 25745 ────────────────────────────────────────────────────
        if check_id == "energy_class":
            energy_class = platform.get("energy_efficiency_class", "")
            return (
                any(w in text for w in [
                    "energy", "vfd", "regenerative", "efficient",
                    "class a", "class b", "vvvf",
                ])
                or bool(energy_class)
            )

        if check_id == "standby_power":
            return any(w in text for w in [
                "standby", "sleep", "idle", "power save"
            ])

        if check_id == "usage_category":
            return bool(building_type)

        return False

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — STANDARDS COMPLIANCE
    # ══════════════════════════════════════════════════════════════════════

    def _build_standards_compliance(
        self,
        basic_req: Dict,
        product: Dict,
        platform: Dict,
        framework_results: Dict,
    ) -> List[Dict[str, Any]]:
        """Build the standards_compliance list — one entry per standard."""

        entries = []
        req_capacity = basic_req.get("capacity_kg") or 0
        prod_capacity = product.get("capacity_kg", 0)
        req_floors = basic_req.get("max_floors") or 10
        prod_speed = product.get("speed_ms", 0)
        building_type = basic_req.get("building_type", "")
        energy_class = platform.get("energy_efficiency_class", "")

        # ── EN 81-20/50 ──────────────────────────────────────────────
        en_result = framework_results.get("EN_81", {})
        en_status = "Compliant" if en_result.get("score", 0) >= 0.75 else "Recommended"
        entries.append({
            "standard_name": "EN 81-20/50",
            "status": en_status,
            "rationale": (
                f"Designed in accordance with EN 81-20/50. "
                f"Passenger elevator capacity {prod_capacity:,} kg "
                f"{'meets' if prod_capacity >= 630 else 'below'} "
                f"EN 81-20 minimum of 630 kg. "
                f"Door protection and overload detection included in configuration."
            ),
            "configuration_source": "standards_based",
        })

        # ── ASME A17.1 ──────────────────────────────────────────────
        asme_result = framework_results.get("ASME_A17_1", {})
        asme_status = "Compliant" if asme_result.get("score", 0) >= 0.75 else "Recommended"

        # Speed limit description
        if req_floors <= 20:
            speed_limit = "3.5 m/s"
        elif req_floors <= 50:
            speed_limit = "6.0 m/s"
        else:
            speed_limit = "12.0 m/s"

        entries.append({
            "standard_name": "ASME A17.1",
            "status": asme_status,
            "rationale": (
                f"Designed in accordance with ASME A17.1. "
                f"Capacity adequate for requirement. "
                f"Operating speed {prod_speed} m/s within limit "
                f"for {req_floors}-floor building (max {speed_limit}). "
                f"Safety features present in configuration."
            ),
            "configuration_source": "standards_based",
        })

        # ── IS 14665 ────────────────────────────────────────────────
        is14665_result = framework_results.get("IS_14665", {})
        is14665_status = "Compliant" if is14665_result.get("score", 0) >= 0.75 else "Recommended"

        fire_note = ""
        if self._is_high_rise(req_floors):
            fire_note = " Fire service mode included for high-rise building."
        else:
            fire_note = ""

        entries.append({
            "standard_name": "IS 14665",
            "status": is14665_status,
            "rationale": (
                f"Designed in accordance with IS 14665. "
                f"Emergency alarm and overload protection present. "
                f"ARD system {'included' if self._feature_available('ARD (Automatic Rescue Device)', platform) else 'available'}."
                f"{fire_note}"
            ),
            "configuration_source": "standards_based",
        })

        # ── IS 15785 ────────────────────────────────────────────────
        is15785_result = framework_results.get("IS_15785", {})
        is15785_status = "Compliant" if is15785_result.get("score", 0) >= 0.75 else "Recommended"

        wheelchair_note = (
            f"Car capacity {prod_capacity:,} kg "
            f"{'sufficient' if prod_capacity >= 680 else 'may need review'} "
            f"for wheelchair accessibility."
        )

        entries.append({
            "standard_name": "IS 15785",
            "status": is15785_status,
            "rationale": (
                f"Designed in accordance with IS 15785. "
                f"Braille buttons {'included' if self._feature_available('Braille Buttons', platform) else 'available'} on platform. "
                f"{wheelchair_note}"
            ),
            "configuration_source": "standards_based",
        })

        # ── ISO 25745 ───────────────────────────────────────────────
        iso_result = framework_results.get("ISO_25745", {})
        if iso_result.get("score", 0) >= 0.75:
            iso_status = "Compliant"
            iso_lang = "Designed in accordance with"
        else:
            iso_status = "Recommended"
            iso_lang = "Recommended under"

        regen_note = ""
        if self._has_gearless_traction(platform) and req_floors >= 15:
            regen_note = " Regenerative drive included."
        elif req_floors >= 15:
            regen_note = " Regenerative drive recommended."

        entries.append({
            "standard_name": "ISO 25745",
            "status": iso_status,
            "rationale": (
                f"{iso_lang} ISO 25745. "
                f"Energy efficiency Class {energy_class}. "
                f"Building type allows usage-category determination."
                f"{regen_note}"
            ),
            "configuration_source": "standards_based",
        })

        self.add_reasoning_trace(
            step="standards_compliance_build",
            reasoning=f"Built {len(entries)} standards compliance entries",
            evidence=[{"standards": [e["standard_name"] for e in entries]}],
            confidence=0.92,
        )

        return entries

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — SAFETY FEATURES
    # ══════════════════════════════════════════════════════════════════════

    def _build_safety_features(
        self,
        floors: int,
        building_type: str,
        platform: Dict,
    ) -> List[Dict[str, Any]]:
        """Build the safety_features list — 6 features."""

        features = []
        is_high_rise = self._is_high_rise(floors)
        is_commercial = self._is_commercial_or_institutional(building_type)

        # 1. Emergency Alarm — always Compliant
        features.append({
            "feature": "Emergency Alarm",
            "status": "Compliant",
            "standard": "IS 14665",
            "rationale": (
                "Designed in accordance with IS 14665. "
                "Required for all passenger elevators."
            ),
            "configuration_source": "standards_based",
        })

        # 2. ARD System
        if floors > 8 or is_commercial:
            features.append({
                "feature": "ARD System",
                "status": "Compliant",
                "standard": "IS 14665",
                "rationale": (
                    "Designed in accordance with IS 14665. "
                    f"Required for {'commercial' if is_commercial else 'high-rise'} "
                    f"buildings exceeding 8 floors."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "ARD System",
                "status": "Recommended",
                "standard": "IS 14665",
                "rationale": (
                    "Recommended under IS 14665. "
                    "Not mandatory for low-rise residential but recommended "
                    "for passenger safety."
                ),
                "configuration_source": "standards_based",
            })

        # 3. Overload Protection — always Compliant
        features.append({
            "feature": "Overload Protection",
            "status": "Compliant",
            "standard": "EN 81-20",
            "rationale": (
                "Designed in accordance with EN 81-20. "
                "Required for all passenger elevators."
            ),
            "configuration_source": "standards_based",
        })

        # 4. Intercom — always Compliant
        features.append({
            "feature": "Intercom",
            "status": "Compliant",
            "standard": "ASME A17.1",
            "rationale": (
                "Designed in accordance with ASME A17.1. "
                "Two-way communication required in all passenger lifts."
            ),
            "configuration_source": "standards_based",
        })

        # 5. Fire Service Mode
        if is_high_rise:
            features.append({
                "feature": "Fire Service Mode",
                "status": "Compliant",
                "standard": "IS 14665 / NBC India",
                "rationale": (
                    "Designed in accordance with IS 14665. "
                    "Recommended for firefighter operation. "
                    f"Building height ({floors} floors x {self.FLOOR_HEIGHT_M:.0f}m "
                    f"= {floors * self.FLOOR_HEIGHT_M:.0f}m) exceeds "
                    f"{self.FIRE_SERVICE_HEIGHT_M}m threshold."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Fire Service Mode",
                "status": "Not Applicable",
                "standard": "IS 14665 / NBC India",
                "rationale": (
                    f"Building height ({floors} floors x {self.FLOOR_HEIGHT_M:.0f}m "
                    f"= {floors * self.FLOOR_HEIGHT_M:.0f}m) below "
                    f"{self.FIRE_SERVICE_HEIGHT_M}m threshold. Not mandatory."
                ),
                "configuration_source": "standards_based",
            })

        # 6. Emergency Lighting
        if is_commercial or is_high_rise:
            features.append({
                "feature": "Emergency Lighting",
                "status": "Compliant",
                "standard": "IS 14665",
                "rationale": (
                    "Designed in accordance with IS 14665. "
                    f"Required for {'commercial' if is_commercial else 'high-rise'} buildings."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Emergency Lighting",
                "status": "Recommended",
                "standard": "IS 14665",
                "rationale": (
                    "Recommended under IS 14665. "
                    "Recommended for all passenger elevators for safe evacuation."
                ),
                "configuration_source": "standards_based",
            })

        self.add_reasoning_trace(
            step="safety_features_build",
            reasoning=f"Built {len(features)} safety feature assessments",
            evidence=[{
                "high_rise": is_high_rise,
                "commercial": is_commercial,
            }],
            confidence=0.95,
        )

        return features

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — ACCESSIBILITY FEATURES
    # ══════════════════════════════════════════════════════════════════════

    def _build_accessibility_features(
        self,
        capacity: int,
        building_type: str,
        platform: Dict,
    ) -> List[Dict[str, Any]]:
        """Build the accessibility_features list — 5 features."""

        features = []
        is_commercial = self._is_commercial_or_institutional(building_type)

        # 1. Braille Buttons
        if self._feature_available("Braille Buttons", platform):
            features.append({
                "feature": "Braille Buttons",
                "status": "Compliant",
                "standard": "IS 15785",
                "rationale": (
                    "Designed in accordance with IS 15785. "
                    "Required for accessibility compliance. "
                    "Available on selected platform."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Braille Buttons",
                "status": "Recommended",
                "standard": "IS 15785",
                "rationale": (
                    "Recommended under IS 15785. "
                    "Required for accessibility compliance."
                ),
                "configuration_source": "standards_based",
            })

        # 2. Voice Announcement
        if self._feature_available("Voice Announcement", platform) and is_commercial:
            features.append({
                "feature": "Voice Announcement",
                "status": "Compliant",
                "standard": "IS 15785",
                "rationale": (
                    "Designed in accordance with IS 15785. "
                    "Required for commercial and public buildings."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Voice Announcement",
                "status": "Recommended",
                "standard": "IS 15785",
                "rationale": (
                    "Recommended under IS 15785 for visually impaired users."
                ),
                "configuration_source": "standards_based",
            })

        # 3. Handrails — always Recommended
        features.append({
            "feature": "Handrails",
            "status": "Recommended",
            "standard": "IS 15785",
            "rationale": (
                "Recommended under IS 15785. "
                "Recommended for passenger safety and accessibility."
            ),
            "configuration_source": "standards_based",
        })

        # 4. Mirror — always Recommended
        features.append({
            "feature": "Mirror",
            "status": "Recommended",
            "standard": "IS 15785",
            "rationale": (
                "Recommended under IS 15785. "
                "Recommended for wheelchair users to view door from rear of car."
            ),
            "configuration_source": "standards_based",
        })

        # 5. Wheelchair Accessibility
        if capacity >= 680:
            features.append({
                "feature": "Wheelchair Accessibility",
                "status": "Compliant",
                "standard": "IS 15785",
                "rationale": (
                    f"Designed in accordance with IS 15785. "
                    f"Car capacity {capacity:,} kg sufficient for wheelchair access "
                    f"(minimum 680 kg)."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Wheelchair Accessibility",
                "status": "Recommended",
                "standard": "IS 15785",
                "rationale": (
                    f"Recommended under IS 15785. "
                    f"Car capacity {capacity:,} kg below recommended 680 kg minimum "
                    f"for wheelchair access."
                ),
                "configuration_source": "standards_based",
            })

        self.add_reasoning_trace(
            step="accessibility_features_build",
            reasoning=f"Built {len(features)} accessibility feature assessments",
            evidence=[{"capacity": capacity, "commercial": is_commercial}],
            confidence=0.93,
        )

        return features

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — ENERGY EFFICIENCY
    # ══════════════════════════════════════════════════════════════════════

    def _build_energy_efficiency(
        self,
        floors: int,
        platform: Dict,
    ) -> List[Dict[str, Any]]:
        """Build the energy_efficiency list — 5 features."""

        features = []
        energy_class = platform.get("energy_efficiency_class", "A")
        is_gearless = self._has_gearless_traction(platform)

        # 1. LED Lighting
        if self._feature_available("LED Lighting", platform):
            features.append({
                "feature": "LED Lighting",
                "status": "Compliant",
                "standard": "ISO 25745",
                "rationale": (
                    "Designed in accordance with ISO 25745. "
                    "Available on platform. "
                    "Reduces car lighting energy consumption by 50-60%."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "LED Lighting",
                "status": "Recommended",
                "standard": "ISO 25745",
                "rationale": (
                    "Recommended under ISO 25745. "
                    "Reduces car lighting energy consumption by 50-60%."
                ),
                "configuration_source": "standards_based",
            })

        # 2. Standby Mode — always Recommended
        features.append({
            "feature": "Standby Mode",
            "status": "Recommended",
            "standard": "ISO 25745",
            "rationale": (
                "Recommended under ISO 25745. "
                "Reduces idle energy consumption when elevator is not in use."
            ),
            "configuration_source": "standards_based",
        })

        # 3. VVVF Drive
        if is_gearless:
            features.append({
                "feature": "VVVF Drive",
                "status": "Compliant",
                "standard": "ISO 25745",
                "rationale": (
                    "Designed in accordance with ISO 25745. "
                    "Standard on gearless traction platforms."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "VVVF Drive",
                "status": "Recommended",
                "standard": "ISO 25745",
                "rationale": (
                    "Recommended under ISO 25745. "
                    "Improves energy efficiency by 20-30% over conventional drives."
                ),
                "configuration_source": "standards_based",
            })

        # 4. Regenerative Drive
        if floors < 15:
            features.append({
                "feature": "Regenerative Drive",
                "status": "Not Applicable",
                "standard": "ISO 25745",
                "rationale": (
                    f"Cost-benefit marginal for buildings under 15 floors "
                    f"({floors} floors)."
                ),
                "configuration_source": "standards_based",
            })
        elif is_gearless and floors >= 25:
            # High-rise gearless → Compliant
            features.append({
                "feature": "Regenerative Drive",
                "status": "Compliant",
                "standard": "ISO 25745",
                "rationale": (
                    "Designed in accordance with ISO 25745. "
                    "Included on high-rise gearless traction platform. "
                    f"Significant energy savings for {floors}-floor travel."
                ),
                "configuration_source": "standards_based",
            })
        else:
            # 15+ floors but not high-rise gearless → Recommended
            features.append({
                "feature": "Regenerative Drive",
                "status": "Recommended",
                "standard": "ISO 25745",
                "rationale": (
                    "Recommended under ISO 25745. "
                    f"Energy savings beneficial for {floors}-floor travel distance."
                ),
                "configuration_source": "standards_based",
            })

        # 5. Efficiency Class — always Compliant (from platform data)
        features.append({
            "feature": "Efficiency Class",
            "status": "Compliant",
            "standard": "ISO 25745",
            "rationale": (
                f"Designed in accordance with ISO 25745. "
                f"Platform rated Energy Efficiency Class {energy_class}."
            ),
            "configuration_source": "standards_based",
        })

        self.add_reasoning_trace(
            step="energy_efficiency_build",
            reasoning=f"Built {len(features)} energy efficiency assessments "
                      f"(gearless={is_gearless}, floors={floors}, class={energy_class})",
            evidence=[{
                "gearless": is_gearless,
                "floors": floors,
                "energy_class": energy_class,
            }],
            confidence=0.93,
        )

        return features

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — FIRE SAFETY
    # ══════════════════════════════════════════════════════════════════════

    def _build_fire_safety(
        self,
        floors: int,
        building_type: str,
    ) -> List[Dict[str, Any]]:
        """Build the fire_safety list — 3 features."""

        features = []
        is_high_rise = self._is_high_rise(floors)
        is_commercial = self._is_commercial_or_institutional(building_type)
        height_m = floors * self.FLOOR_HEIGHT_M

        # 1. Fire Service Mode
        if is_high_rise:
            features.append({
                "feature": "Fire Service Mode",
                "status": "Compliant",
                "standard": "IS 14665 / NBC India",
                "rationale": (
                    "Designed in accordance with IS 14665. "
                    "Recommended for firefighter operation. "
                    f"Building height {height_m:.0f}m exceeds "
                    f"{self.FIRE_SERVICE_HEIGHT_M}m threshold."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Fire Service Mode",
                "status": "Not Applicable",
                "standard": "IS 14665 / NBC India",
                "rationale": (
                    f"Building height {height_m:.0f}m below "
                    f"{self.FIRE_SERVICE_HEIGHT_M}m threshold. Not mandatory."
                ),
                "configuration_source": "standards_based",
            })

        # 2. Emergency Lighting
        if is_commercial or is_high_rise:
            features.append({
                "feature": "Emergency Lighting",
                "status": "Compliant",
                "standard": "IS 14665",
                "rationale": (
                    "Designed in accordance with IS 14665. "
                    f"Required for {'commercial' if is_commercial else 'high-rise'} "
                    f"buildings."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Emergency Lighting",
                "status": "Recommended",
                "standard": "IS 14665",
                "rationale": (
                    "Recommended under IS 14665. "
                    "Recommended for all passenger elevators for safe evacuation."
                ),
                "configuration_source": "standards_based",
            })

        # 3. Fire-Rated Doors
        if is_commercial or is_high_rise:
            features.append({
                "feature": "Fire-Rated Doors",
                "status": "Recommended",
                "standard": "NBC India",
                "rationale": (
                    "Recommended under NBC India. "
                    "Recommended for all shaft landing doors in "
                    f"{'commercial high-rise' if is_commercial else 'high-rise'} buildings."
                ),
                "configuration_source": "standards_based",
            })
        else:
            features.append({
                "feature": "Fire-Rated Doors",
                "status": "Recommended",
                "standard": "NBC India",
                "rationale": (
                    "Recommended under NBC India. "
                    "Recommended for shaft landing doors."
                ),
                "configuration_source": "standards_based",
            })

        self.add_reasoning_trace(
            step="fire_safety_build",
            reasoning=f"Built {len(features)} fire safety assessments "
                      f"(high_rise={is_high_rise}, height={height_m:.0f}m)",
            evidence=[{
                "high_rise": is_high_rise,
                "height_m": height_m,
                "commercial": is_commercial,
            }],
            confidence=0.95,
        )

        return features

    # ══════════════════════════════════════════════════════════════════════
    #  NEW — COMPLIANCE NOTES
    # ══════════════════════════════════════════════════════════════════════

    def _build_compliance_notes(self) -> List[str]:
        """Engineering notes — always included."""

        return [
            "Final statutory approval depends on site inspection.",
            "Civil drawings must be approved by local authority.",
            "Local authority approvals required before installation.",
            "Installation inspection required before commissioning.",
            "All features designed in accordance with applicable standards. "
            "Statutory certification subject to third-party inspection.",
        ]

    # ══════════════════════════════════════════════════════════════════════
    #  BACKWARD-COMPATIBLE HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _get_primary_product(self, product_matches: Dict) -> Dict:
        """Extract primary product metadata from product_matches context."""
        try:
            primary = (
                product_matches
                .get("recommendations", {})
                .get("primary_recommendation", {})
            )
            product = primary.get("product", {})
            meta = product.get("metadata", product)
            return {
                "product_id":  meta.get("product_id", ""),
                "capacity_kg": meta.get("capacity_kg", 0),
                "max_floors":  meta.get("max_floors", 0),
                "speed_ms":    meta.get("speed_ms", 0),
                "base_price":  meta.get("base_price", 0),
                "model":       meta.get("model", "Unknown"),
            }
        except Exception:
            return {}

    def _gather_all_requirement_text(self, requirements: Dict) -> str:
        """Concatenate all requirement strings for keyword scanning."""
        parts = []
        ss = requirements.get("structured_summary", {})
        parts.extend(
            ss.get("functional_requirements", {}).get("requirements", [])
        )
        parts.extend(
            ss.get("non_functional_requirements", {}).get("requirements", [])
        )
        for cr in ss.get("critical_requirements", []):
            if isinstance(cr, dict):
                parts.append(cr.get("requirement", ""))
            else:
                parts.append(str(cr))
        parts.extend(
            requirements.get("basic_requirements", {}).get("keywords", [])
        )
        return " ".join(parts)

    def _collect_gaps(self, framework_results: Dict) -> List[Dict[str, Any]]:
        """Flatten framework gaps into a compliance_gaps list."""
        gaps = []
        for fw_key, fw_data in framework_results.items():
            severity = (
                "critical" if fw_data["score"] < 0.50
                else "medium" if fw_data["score"] < 0.75
                else "low"
            )
            for gap_desc in fw_data["gaps"]:
                gaps.append({
                    "type":        "framework_gap",
                    "framework":   fw_key,
                    "description": gap_desc,
                    "severity":    severity,
                })
        return gaps

    def _build_remediation_plan(
        self, compliance_gaps: List[Dict]
    ) -> Dict[str, Any]:
        """Create remediation plan for compliance gaps."""
        if not compliance_gaps:
            return {
                "status": "no_remediation_needed",
                "message": "All compliance requirements are met",
                "estimated_timeline": "No remediation needed",
            }

        critical = [g for g in compliance_gaps if g["severity"] == "critical"]
        medium   = [g for g in compliance_gaps if g["severity"] == "medium"]

        immediate_actions = [
            {
                "gap": g,
                "action": f"Address {g['framework']} gap: {g['description']}",
                "timeline": "Immediate (0-30 days)",
                "priority": "Critical",
            }
            for g in critical
        ]

        short_term_actions = [
            {
                "gap": g,
                "action": f"Implement {g['framework']} measure: {g['description']}",
                "timeline": "Short-term (1-3 months)",
                "priority": "Medium",
            }
            for g in medium
        ]

        if critical:
            timeline = "3-6 months (due to critical gaps)"
        elif medium:
            timeline = "1-3 months"
        else:
            timeline = "Within 30 days"

        self.add_reasoning_trace(
            step="remediation_planning",
            reasoning=f"Created remediation plan for {len(compliance_gaps)} gaps",
            evidence=[{"timeline": timeline}],
            confidence=0.85,
        )

        return {
            "immediate_actions":  immediate_actions,
            "short_term_actions": short_term_actions,
            "long_term_actions":  [],
            "estimated_timeline": timeline,
            "priority_order":     immediate_actions + short_term_actions,
        }

    def _calculate_validation_confidence(self) -> float:
        if not self.reasoning_traces:
            return 0.5
        return sum(t.confidence for t in self.reasoning_traces) / len(
            self.reasoning_traces
        )

    def get_tools(self) -> List:
        """Get agent-specific tools"""
        return [KnowledgeSearchTool(), ComplianceCheckTool()]