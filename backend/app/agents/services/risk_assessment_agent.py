from typing import Dict, Any, List, Optional
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, HistoricalDataTool


class RiskAssessmentAgent(BaseElevateAgent):
    """Technical Configuration Agent.

    Despite the class and file name (retained for orchestrator and import
    compatibility), this agent functions as an **elevator design engineer**.

    It takes the customer requirements and the selected platform, then
    derives a technical configuration proposal — machine room type, drive
    system, door configuration, safety features, accessibility, etc.

    It does **not**:
    - Fabricate risk predictions (budget overrun, timeline delay, etc.)
    - Pretend certainty about civil parameters (shaft size, pit depth,
      overhead height) that require site survey and drawings.
    - Replace actual engineering review.

    Every recommendation carries:
        value                – the recommended value
        applicability        – mandatory / recommended / optional
        rationale            – human-readable justification
        configuration_source – standards_based / platform_based / requirement_based
    """

    def __init__(self):
        super().__init__(
            name="risk_assessor",          # unchanged for orchestrator compat
            role="Senior Elevator Design Engineer",
            goal="Derive technical configuration recommendations from customer requirements and selected platform",
            backstory="""You are a senior elevator design engineer with 25+ years 
            of experience in vertical transportation systems. You translate customer
            requirements into actionable technical specifications, referencing IS 14665,
            IS 15785, and National Building Code guidelines.""",
        )

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Derive technical configuration from requirements + platform."""
        start_time = datetime.now()

        try:
            requirements    = context.get("requirements", {})
            product_matches = context.get("product_matches", {})

            if not requirements:
                raise ValueError("No requirements provided for technical configuration")

            # ── Extract inputs ───────────────────────────────────────────
            basic    = requirements.get("basic_requirements", {})
            platform = self._extract_platform(product_matches)

            capacity_kg   = basic.get("capacity_kg")
            max_floors    = basic.get("max_floors")
            speed_ms      = basic.get("speed_ms")
            building_type = basic.get("building_type")
            lift_type     = basic.get("lift_type")
            special_reqs  = basic.get("special_requirements",
                            basic.get("optional_features", []))

            self.logger.info(
                "[TechConfig] Inputs — platform=%s  building=%s  lift=%s  "
                "capacity=%s  floors=%s  speed=%s",
                platform.get("id", "?"), building_type, lift_type,
                capacity_kg, max_floors, speed_ms,
            )

            # ── Derive configuration ─────────────────────────────────────
            technical_configuration = self._derive_configuration(
                platform, capacity_kg, max_floors, speed_ms,
                building_type, lift_type, special_reqs,
            )

            # ── Engineering notes ────────────────────────────────────────
            engineering_notes = self._generate_engineering_notes(
                platform, capacity_kg, max_floors, speed_ms,
                building_type, lift_type,
            )

            # ── Configuration details ────────────────────────────────────
            mandatory_count  = len([c for c in technical_configuration if c["applicability"] == "mandatory"])
            recommended_count = len([c for c in technical_configuration if c["applicability"] == "recommended"])
            optional_count   = len([c for c in technical_configuration if c["applicability"] == "optional"])

            configuration_details = {
                "platform_id":          platform.get("id", "unknown"),
                "platform_name":        platform.get("name", "Unknown"),
                "platform_tier":        platform.get("tier", "Unknown"),
                "building_type":        building_type,
                "lift_type":            lift_type,
                "floors":               max_floors,
                "capacity_kg":          capacity_kg,
                "speed_ms":             speed_ms,
                "total_configurations": len(technical_configuration),
                "mandatory_count":      mandatory_count,
                "recommended_count":    recommended_count,
                "optional_count":       optional_count,
            }

            configuration_confidence = self._calculate_confidence(
                capacity_kg, max_floors, speed_ms, building_type, lift_type,
            )

            configuration_metadata = {
                "total_configurations":     len(technical_configuration),
                "configuration_confidence": round(configuration_confidence, 4),
            }

            self.logger.info(
                "[TechConfig] Generated %d configurations "
                "(%d mandatory, %d recommended, %d optional) — confidence=%.0f%%",
                len(technical_configuration),
                mandatory_count, recommended_count, optional_count,
                configuration_confidence * 100,
            )

            self.add_reasoning_trace(
                step="technical_configuration",
                reasoning=(
                    f"Derived {len(technical_configuration)} technical configurations "
                    f"for platform {platform.get('id', '?')} "
                    f"({mandatory_count} mandatory, {recommended_count} recommended, "
                    f"{optional_count} optional)."
                ),
                evidence=[configuration_details],
                confidence=configuration_confidence,
            )

            # ── Build result ─────────────────────────────────────────────
            result = {
                # ── New: Technical configuration ─────────────────────────
                "technical_configuration": technical_configuration,
                "configuration_details":   configuration_details,
                "engineering_notes":       engineering_notes,
                "configuration_metadata":  configuration_metadata,

                # ── Backward compat: risk-shaped stubs ───────────────────
                "risk_analysis": {
                    "identified_risks":  [],
                    "overall_risk_score": 0.10,
                    "risk_level":        "low",
                    "top_risks":         [],
                    "risk_distribution": {
                        "critical": 0, "high": 0, "medium": 0, "low": 0,
                    },
                },
                "mitigation_strategies": {
                    "immediate_actions":       [],
                    "preventive_measures":     [],
                    "contingency_plans":       [],
                    "monitoring_requirements": [],
                },
                "risk_metadata": {
                    "total_risks_identified":     0,
                    "high_risk_count":            0,
                    "overall_risk_score":         0.10,
                    "risk_assessment_confidence": round(configuration_confidence, 4),
                },

                # Legacy list stubs
                "requirement_risks": [],
                "product_risks":     [],
                "compliance_risks":  [],
                "timeline_risks":    [],
                "budget_risks":      [],
                "historical_risks":  [],
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                agent_name=self.name,
                result=result,
                reasoning_traces=self.reasoning_traces,
                confidence_score=configuration_confidence,
                execution_time=execution_time,
                retrieved_context=[],
                citations=[],
            )

        except Exception as e:
            self.logger.error(f"Technical configuration failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  PLATFORM EXTRACTION
    # ══════════════════════════════════════════════════════════════════════

    def _extract_platform(self, product_matches: Dict[str, Any]) -> Dict[str, Any]:
        """Extract primary platform from product matching results."""

        if not product_matches:
            return {}

        # Try recommendations → primary_recommendation → product → metadata
        rec = product_matches.get("recommendations", {})
        primary = rec.get("primary_recommendation", {})
        product = primary.get("product", {})
        metadata = product.get("metadata", {})

        if metadata.get("product_id"):
            # Merge coverage data from product into metadata
            result = dict(metadata)
            result["coverage_score"] = product.get("coverage_score", 0)
            result["premium_features_available"] = []

            # Look up premium features from the catalog
            from config import PRODUCTS
            for p in PRODUCTS:
                if p["id"] == metadata.get("product_id"):
                    result["tier"] = p.get("tier", metadata.get("tier", "Unknown"))
                    result["premium_features_available"] = p.get("premium_features_available", [])
                    result["energy_efficiency_class"] = p.get("energy_efficiency_class", "B")
                    result["supported_lift_types"] = p.get("supported_lift_types", [])
                    break

            return result

        # Fallback: try direct product_matches list
        matches = product_matches.get("product_matches", [])
        if matches:
            meta = matches[0].get("metadata", {})
            result = dict(meta)
            result["coverage_score"] = matches[0].get("coverage_score", 0)
            result["premium_features_available"] = []
            result["energy_efficiency_class"] = "B"
            return result

        return {}

    # ══════════════════════════════════════════════════════════════════════
    #  CONFIGURATION DERIVATION
    # ══════════════════════════════════════════════════════════════════════

    def _derive_configuration(
        self,
        platform: Dict[str, Any],
        capacity_kg: Optional[int],
        max_floors: Optional[int],
        speed_ms: Optional[float],
        building_type: Optional[str],
        lift_type: Optional[str],
        special_reqs: List[str],
    ) -> List[Dict[str, Any]]:
        """Derive all technical configuration items deterministically."""

        configs: List[Dict[str, Any]] = []
        tier = platform.get("tier", "Unknown")
        premium_features = platform.get("premium_features_available", [])
        energy_class = platform.get("energy_efficiency_class", "B")
        floors = max_floors or 0
        speed = speed_ms or 0.0
        capacity = capacity_kg or 0
        btype = (building_type or "").lower()
        ltype = (lift_type or "").lower()
        special_lower = [s.lower() for s in special_reqs]

        # ── 1. Machine Room ──────────────────────────────────────────────
        configs.append(self._cfg_machine_room(tier, floors, speed, capacity, btype, ltype))

        # ── 2. Drive System ──────────────────────────────────────────────
        configs.append(self._cfg_drive_system(speed, floors, capacity, ltype))

        # ── 3. Power Supply ──────────────────────────────────────────────
        configs.append(self._cfg_power_supply(capacity))

        # ── 4. Door Configuration ────────────────────────────────────────
        configs.append(self._cfg_door(btype, ltype, capacity))

        # ── 5. Control System ────────────────────────────────────────────
        configs.append(self._cfg_control_system(floors, btype))

        # ── 6. ARD System ────────────────────────────────────────────────
        configs.append(self._cfg_ard(floors, btype, premium_features))

        # ── 7. Voice Announcement ────────────────────────────────────────
        configs.append(self._cfg_voice_announcement(btype, floors, premium_features))

        # ── 8. Braille Buttons ───────────────────────────────────────────
        configs.append(self._cfg_braille())

        # ── 9. Emergency Alarm ───────────────────────────────────────────
        configs.append(self._cfg_emergency_alarm(floors, btype))

        # ── 10. Overload Protection ──────────────────────────────────────
        configs.append(self._cfg_overload_protection())

        # ── 11. Fire Service Mode ────────────────────────────────────────
        configs.append(self._cfg_fire_service(floors, btype, special_lower))

        # ── 12. IoT Monitoring ───────────────────────────────────────────
        configs.append(self._cfg_iot_monitoring(tier, btype, premium_features))

        # ── 13. Accessibility Features ───────────────────────────────────
        configs.append(self._cfg_accessibility(btype, ltype))

        # ── 14. Energy Efficiency ────────────────────────────────────────
        configs.append(self._cfg_energy_efficiency(energy_class, tier, speed))

        # ── 15. CCTV / Surveillance ──────────────────────────────────────
        configs.append(self._cfg_cctv(btype, floors, premium_features, special_lower))

        self.add_reasoning_trace(
            step="configuration_derivation",
            reasoning=(
                f"Derived {len(configs)} technical configurations based on "
                f"platform {platform.get('id', '?')} ({tier} tier), "
                f"building type '{building_type or 'unknown'}', "
                f"lift type '{lift_type or 'unknown'}'."
            ),
            evidence=[{"config_count": len(configs), "tier": tier}],
            confidence=0.90,
        )

        return configs

    # ── Individual configuration derivers ────────────────────────────────

    def _cfg_machine_room(
        self, tier: str, floors: int, speed: float,
        capacity: int, btype: str, ltype: str,
    ) -> Dict[str, Any]:

        if ltype in ("hydraulic",):
            return self._config_item(
                "Machine Room", "Conventional (Hydraulic)", "mandatory",
                "Hydraulic systems require a dedicated machine room for the "
                "hydraulic power unit and control panel.",
                "standards_based", "drive_system",
            )

        if speed > 3.0 or capacity > 2500 or floors > 50:
            return self._config_item(
                "Machine Room", "Conventional or MRL (Engineering review required)", "recommended",
                "High speed, high capacity, or ultra-high-rise installations may "
                "require conventional machine room. MRL is possible with modern "
                "gearless traction but must be validated by the manufacturer.",
                "platform_based", "drive_system",
            )

        return self._config_item(
            "Machine Room", "MRL (Machine Room-Less)", "recommended",
            "MRL design is space-efficient and standard for modern "
            f"{tier.lower()}-tier platforms up to {floors or '?'} floors. "
            "Eliminates dedicated machine room, reducing civil construction costs.",
            "platform_based", "drive_system",
        )

    def _cfg_drive_system(
        self, speed: float, floors: int, capacity: int, ltype: str,
    ) -> Dict[str, Any]:

        if ltype in ("hydraulic",):
            return self._config_item(
                "Drive System", "Hydraulic Drive", "mandatory",
                "Hydraulic drive is required for hydraulic lift type. "
                "Suitable for low-rise applications up to 6 floors.",
                "requirement_based", "drive_system",
            )

        if speed > 1.75 or floors > 25:
            return self._config_item(
                "Drive System", "VVVF Gearless Traction", "mandatory",
                "Gearless traction is required for speeds above 1.75 m/s "
                "or buildings exceeding 25 floors. Provides smooth ride quality, "
                "energy efficiency, and reduced maintenance compared to geared systems.",
                "standards_based", "drive_system",
            )

        if speed > 0.0:
            return self._config_item(
                "Drive System", "VVVF AC Geared Traction", "recommended",
                "VVVF (Variable Voltage Variable Frequency) geared traction "
                "provides energy-efficient variable speed control. Suitable for "
                f"speeds up to 1.75 m/s and mid-rise installations.",
                "platform_based", "drive_system",
            )

        # Speed unknown
        return self._config_item(
            "Drive System", "VVVF Traction (Geared or Gearless per final speed)", "recommended",
            "VVVF traction drive recommended. Final selection between geared "
            "and gearless depends on confirmed speed requirement. Gearless is "
            "required above 1.75 m/s.",
            "platform_based", "drive_system",
        )

    def _cfg_power_supply(self, capacity: int) -> Dict[str, Any]:
        return self._config_item(
            "Power Supply", "Three Phase 415V 50Hz", "mandatory",
            "Three-phase 415V 50Hz power supply is mandatory for elevator "
            "traction motor operation as per IS 14665. Single-phase supply "
            "is insufficient for elevator motor starting current requirements.",
            "standards_based", "electrical",
        )

    def _cfg_door(
        self, btype: str, ltype: str, capacity: int,
    ) -> Dict[str, Any]:

        if ltype in ("freight", "goods"):
            return self._config_item(
                "Door Configuration",
                "Two-speed side opening (heavy-duty)",
                "recommended",
                "Heavy-duty two-speed side opening doors are standard for "
                "freight and goods lifts to accommodate wide loads and "
                "pallet entry. Door width should accommodate cargo dimensions.",
                "requirement_based", "doors",
            )

        if btype in ("hospital",):
            return self._config_item(
                "Door Configuration",
                "Two-speed centre opening (wide — minimum 1100mm clear opening)",
                "mandatory",
                "Hospital lifts require minimum 1100mm clear door opening to "
                "accommodate stretcher and bed entry as per IS 14665. "
                "Centre opening provides fastest operation for emergency use.",
                "standards_based", "doors",
            )

        if btype in ("commercial", "office", "mixed-use"):
            return self._config_item(
                "Door Configuration",
                "High-speed centre opening (2-panel or 4-panel)",
                "recommended",
                "High-speed centre opening doors improve passenger throughput "
                "in commercial buildings with high traffic volume. "
                "4-panel configuration recommended for wider openings.",
                "platform_based", "doors",
            )

        # Residential / default
        return self._config_item(
            "Door Configuration",
            "Two-speed centre opening",
            "recommended",
            "Centre opening doors provide balanced opening speed and "
            "aesthetic appearance for residential installations. "
            "Two-speed operation ensures smooth and quiet door movement.",
            "platform_based", "doors",
        )

    def _cfg_control_system(self, floors: int, btype: str) -> Dict[str, Any]:

        if btype in ("commercial", "office", "mixed-use", "hotel") and floors > 15:
            return self._config_item(
                "Control System",
                "Duplex or Group Collective Control",
                "recommended",
                "Multi-car group control is recommended for commercial buildings "
                f"with {floors or '?'} floors to optimise waiting time and "
                "passenger distribution. Duplex control coordinates two cars; "
                "group control handles three or more.",
                "requirement_based", "controls",
            )

        if floors > 20:
            return self._config_item(
                "Control System",
                "Duplex Collective Control",
                "recommended",
                f"Buildings with {floors} floors benefit from duplex collective "
                "control for improved traffic handling during peak hours. "
                "Single-car simplex may cause excessive wait times.",
                "requirement_based", "controls",
            )

        return self._config_item(
            "Control System",
            "Simplex Collective Control",
            "recommended",
            "Simplex collective control is efficient for single-car "
            "installations in residential and small commercial buildings. "
            "Responds to hall calls in direction of travel.",
            "platform_based", "controls",
        )

    def _cfg_ard(
        self, floors: int, btype: str, premium_features: List[str],
    ) -> Dict[str, Any]:

        # Buildings taller than 24m (~8 floors) or hospitals → mandatory
        if floors > 8 or btype in ("hospital", "commercial", "office", "hotel"):
            return self._config_item(
                "ARD System",
                "Battery-powered Automatic Rescue Device",
                "mandatory",
                "Automatic Rescue Device (ARD) is mandatory for buildings "
                "exceeding 24m travel height or commercial/hospital occupancies. "
                "Provides automatic floor levelling and door opening during "
                "power failure, ensuring passenger safety.",
                "standards_based", "safety",
            )

        return self._config_item(
            "ARD System",
            "Battery-powered Automatic Rescue Device",
            "recommended",
            "ARD is recommended for all passenger elevators to ensure "
            "automatic rescue during power failure. Provides battery-powered "
            "car levelling to nearest floor and automatic door opening.",
            "platform_based", "safety",
        )

    def _cfg_voice_announcement(
        self, btype: str, floors: int, premium_features: List[str],
    ) -> Dict[str, Any]:

        if btype in ("commercial", "office", "hospital", "hotel", "government"):
            return self._config_item(
                "Voice Announcement",
                "Floor and direction announcement",
                "recommended",
                "Voice announcement with floor number and travel direction "
                "is a standard expectation in commercial, hospital, and hotel "
                "buildings. Enhances accessibility for visually impaired passengers.",
                "requirement_based", "passenger_interface",
            )

        return self._config_item(
            "Voice Announcement",
            "Floor announcement",
            "optional",
            "Floor-level voice announcement improves passenger convenience "
            "in residential buildings. Optional but enhances perceived quality.",
            "platform_based", "passenger_interface",
        )

    def _cfg_braille(self) -> Dict[str, Any]:
        return self._config_item(
            "Braille Buttons",
            "Required on all COP and LOP buttons",
            "mandatory",
            "Braille markings on Car Operating Panel (COP) and Landing "
            "Operating Panel (LOP) buttons are mandatory for accessibility "
            "compliance as per IS 15785 and Rights of Persons with "
            "Disabilities Act, 2016.",
            "standards_based", "accessibility",
        )

    def _cfg_emergency_alarm(self, floors: int, btype: str) -> Dict[str, Any]:

        if floors > 15 or btype in ("commercial", "office", "hospital", "hotel"):
            return self._config_item(
                "Emergency Alarm",
                "In-car alarm bell + two-way intercom + emergency lighting",
                "mandatory",
                "Emergency alarm system with two-way intercom is mandatory "
                "as per IS 14665. High-rise and commercial buildings require "
                "intercom connected to building management or 24-hour "
                "monitoring station for trapped passenger communication.",
                "standards_based", "safety",
            )

        return self._config_item(
            "Emergency Alarm",
            "In-car alarm bell + emergency lighting",
            "mandatory",
            "Emergency alarm bell and battery-backed emergency lighting "
            "are mandatory in all passenger elevators as per IS 14665. "
            "Enables trapped passengers to alert building occupants.",
            "standards_based", "safety",
        )

    def _cfg_overload_protection(self) -> Dict[str, Any]:
        return self._config_item(
            "Overload Protection",
            "Electronic load weighing device",
            "mandatory",
            "Overload detection and prevention system is mandatory as per "
            "IS 14665. The elevator must not operate when loaded beyond "
            "110% of rated capacity. Electronic load weighing provides "
            "accurate measurement and audible/visual warning.",
            "standards_based", "safety",
        )

    def _cfg_fire_service(
        self, floors: int, btype: str, special_lower: List[str],
    ) -> Dict[str, Any]:

        # NBC India requires firefighter lift for buildings >24m height
        # ~8 floors at 3m floor height
        is_high_rise = floors > 8
        is_hospital = btype in ("hospital",)
        fire_requested = any(
            "fire" in s for s in special_lower
        )

        if is_high_rise or is_hospital or fire_requested:
            return self._config_item(
                "Fire Service Mode",
                "Firefighter's operation (Phase 1 and Phase 2)",
                "mandatory",
                "Firefighter's operation is mandatory for buildings exceeding "
                "24m height as per National Building Code of India. Phase 1 "
                "recalls all cars to designated floor on fire alarm activation. "
                "Phase 2 provides manual firefighter control. "
                "Hospital buildings require fire service regardless of height.",
                "standards_based", "safety",
            )

        return self._config_item(
            "Fire Service Mode",
            "Not required (building height below 24m)",
            "optional",
            "Fire service mode is not mandated for buildings below 24m "
            "height per National Building Code. Can be included as an "
            "optional safety enhancement if the client requests it.",
            "standards_based", "safety",
        )

    def _cfg_iot_monitoring(
        self, tier: str, btype: str, premium_features: List[str],
    ) -> Dict[str, Any]:

        if btype in ("commercial", "office", "hospital", "hotel", "government"):
            return self._config_item(
                "IoT Monitoring",
                "Full IoT with remote monitoring and predictive diagnostics",
                "recommended",
                "IoT-enabled remote monitoring is recommended for commercial "
                "and institutional buildings to ensure uptime SLA compliance, "
                "predictive maintenance scheduling, and real-time fault alerts. "
                "Reduces unplanned downtime and emergency callouts.",
                "platform_based", "monitoring",
            )

        if tier in ("Super", "Ultra", "Specialized"):
            return self._config_item(
                "IoT Monitoring",
                "Full IoT with remote monitoring and predictive diagnostics",
                "recommended",
                f"IoT monitoring is recommended for {tier}-tier platforms "
                "to enable proactive maintenance and real-time operational "
                "visibility for high-value installations.",
                "platform_based", "monitoring",
            )

        return self._config_item(
            "IoT Monitoring",
            "Basic remote monitoring",
            "optional",
            "Basic IoT monitoring provides remote fault alerts and "
            "usage statistics. Optional for residential installations "
            "but improves maintenance response time.",
            "platform_based", "monitoring",
        )

    def _cfg_accessibility(self, btype: str, ltype: str) -> Dict[str, Any]:

        if btype in ("hospital",):
            return self._config_item(
                "Accessibility Features",
                "Full accessibility: handrails, car mirror, tactile indicators, "
                "audible signals, wide door opening, stretcher-compatible car",
                "mandatory",
                "Hospital elevators require comprehensive accessibility "
                "features including rear car mirror for wheelchair users, "
                "stainless steel handrails, tactile floor indicators, and "
                "audible door signals as per IS 15785.",
                "standards_based", "accessibility",
            )

        if btype in ("commercial", "office", "government"):
            return self._config_item(
                "Accessibility Features",
                "Full accessibility: handrails, car mirror, tactile indicators, "
                "audible signals",
                "mandatory",
                "Commercial and public buildings must provide full accessibility "
                "features including rear car mirror for wheelchair visibility, "
                "handrails, tactile floor indicators on landings, and audible "
                "door closing signals as per IS 15785 and RPWD Act 2016.",
                "standards_based", "accessibility",
            )

        return self._config_item(
            "Accessibility Features",
            "Handrails and car mirror",
            "mandatory",
            "Minimum accessibility features (handrails and rear car mirror) "
            "are mandatory in all passenger elevators as per IS 15785. "
            "Additional features such as tactile indicators can be added.",
            "standards_based", "accessibility",
        )

    def _cfg_energy_efficiency(
        self, energy_class: str, tier: str, speed: float,
    ) -> Dict[str, Any]:

        if energy_class == "A+":
            return self._config_item(
                "Energy Efficiency",
                "Regenerative drive + LED lighting + standby mode + "
                "sleep mode during off-peak",
                "recommended",
                "A+ energy efficiency configuration includes regenerative "
                "drive that feeds braking energy back to the building "
                "electrical grid, full LED car and landing lighting, "
                "automatic standby mode, and sleep mode during off-peak hours. "
                "Reduces energy consumption by up to 40%.",
                "platform_based", "energy",
            )

        if energy_class == "A":
            return self._config_item(
                "Energy Efficiency",
                "LED lighting + standby mode + energy-efficient drive",
                "recommended",
                "Class A energy efficiency includes full LED lighting in car "
                "and landings, automatic standby mode when idle, and "
                "energy-efficient VVVF drive. Reduces energy consumption "
                "by approximately 25% compared to conventional systems.",
                "platform_based", "energy",
            )

        # Class B or unknown
        return self._config_item(
            "Energy Efficiency",
            "LED lighting + standby mode",
            "recommended",
            "Standard energy efficiency measures include LED car and "
            "landing lighting (replacing halogen/fluorescent) and automatic "
            "standby mode to reduce idle power consumption.",
            "platform_based", "energy",
        )

    def _cfg_cctv(
        self, btype: str, floors: int,
        premium_features: List[str], special_lower: List[str],
    ) -> Dict[str, Any]:

        cctv_requested = any("cctv" in s or "camera" in s or "surveillance" in s
                             for s in special_lower)

        if btype in ("commercial", "office", "hospital", "hotel", "government") or cctv_requested:
            return self._config_item(
                "CCTV / In-Car Surveillance",
                "In-car CCTV camera with building management integration",
                "recommended",
                "In-car CCTV is recommended for commercial, hospital, and "
                "hotel buildings for passenger safety, vandalism deterrence, "
                "and incident documentation. Feed should integrate with "
                "building security management system.",
                "requirement_based", "safety",
            )

        return self._config_item(
            "CCTV / In-Car Surveillance",
            "Optional in-car CCTV",
            "optional",
            "In-car CCTV can be added as an optional safety feature for "
            "residential buildings. Provides visual monitoring and "
            "recording for security purposes.",
            "platform_based", "safety",
        )

    # ══════════════════════════════════════════════════════════════════════
    #  ENGINEERING NOTES
    # ══════════════════════════════════════════════════════════════════════

    def _generate_engineering_notes(
        self,
        platform: Dict[str, Any],
        capacity_kg: Optional[int],
        max_floors: Optional[int],
        speed_ms: Optional[float],
        building_type: Optional[str],
        lift_type: Optional[str],
    ) -> List[str]:
        """Generate engineering notes and site survey reminders."""

        notes = [
            # ── Always present — civil parameter reminders ───────────────
            "Shaft size (width x depth) must be determined from manufacturer "
            "layout drawings after platform selection is confirmed. Shaft "
            "dimensions depend on car size, counterweight position, and "
            "door configuration.",

            "Pit depth must be verified through site survey and manufacturer "
            "specifications. Typical values range from 1200mm (low-speed MRL) "
            "to 2500mm+ (high-speed gearless), but actual requirement depends "
            "on buffer type and travel speed.",

            "Overhead clearance (headroom above top landing) must comply with "
            "IS 14665 minimum requirements and manufacturer specifications. "
            "Must be confirmed from architectural drawings.",

            "Electrical load calculation (kVA) must be performed by a licensed "
            "electrical consultant based on the selected motor rating, control "
            "system, and building electrical infrastructure.",

            "All civil dimensions (shaft, pit, overhead, machine room if "
            "applicable) require verification through site inspection and "
            "architectural/structural drawings before final order placement.",
        ]

        # ── Conditional notes ────────────────────────────────────────────

        floors = max_floors or 0
        speed = speed_ms or 0.0

        if floors > 30:
            notes.append(
                f"High-rise installation ({floors} floors) requires "
                "specialized rigging, staging, and potentially tower crane "
                "coordination during construction phase. Pre-installation "
                "site survey is essential."
            )

        if speed > 3.0:
            notes.append(
                f"High-speed installation ({speed} m/s) requires precise "
                "guide rail alignment, vibration analysis, and may require "
                "roller guides instead of sliding guides for ride quality."
            )

        if (capacity_kg or 0) > 2000:
            notes.append(
                f"Heavy-duty installation ({capacity_kg} kg) requires "
                "structural assessment of the pit slab and supporting "
                "structure to verify load-bearing capacity."
            )

        if (building_type or "").lower() == "hospital":
            notes.append(
                "Hospital elevator installations must coordinate with "
                "hospital infection control requirements and may require "
                "antimicrobial car finishes and easy-clean surfaces."
            )

        if (lift_type or "").lower() in ("freight", "goods"):
            notes.append(
                "Freight elevator installations require confirmation of "
                "maximum unit load dimensions, loading method (manual vs "
                "forklift), and floor protection requirements."
            )

        notes.append(
            "These technical recommendations are based on the customer "
            "requirements and selected platform. Final engineering "
            "specifications must be confirmed by the manufacturer's "
            "technical team after site survey and order confirmation."
        )

        self.add_reasoning_trace(
            step="engineering_notes",
            reasoning=f"Generated {len(notes)} engineering notes and reminders.",
            evidence=[{"note_count": len(notes)}],
            confidence=0.95,
        )

        return notes

    # ══════════════════════════════════════════════════════════════════════
    #  CONFIDENCE
    # ══════════════════════════════════════════════════════════════════════

    def _calculate_confidence(
        self,
        capacity_kg: Optional[int],
        max_floors: Optional[int],
        speed_ms: Optional[float],
        building_type: Optional[str],
        lift_type: Optional[str],
    ) -> float:
        """Configuration confidence = proportion of inputs available.

        More inputs → more specific recommendations → higher confidence.
        """
        available = sum(1 for v in [
            capacity_kg, max_floors, speed_ms, building_type, lift_type,
        ] if v is not None)

        # Base confidence 0.50 + up to 0.50 from available inputs
        return 0.50 + (available / 5) * 0.50

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITIES
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _config_item(
        parameter: str,
        value: str,
        applicability: str,
        rationale: str,
        configuration_source: str,
        category: str,
    ) -> Dict[str, Any]:
        """Create a single configuration recommendation."""
        return {
            "parameter":            parameter,
            "value":                value,
            "applicability":        applicability,
            "rationale":            rationale,
            "configuration_source": configuration_source,
            "category":             category,
        }

    def get_tools(self) -> List:
        """Get agent-specific tools."""
        return [KnowledgeSearchTool(), HistoricalDataTool()]