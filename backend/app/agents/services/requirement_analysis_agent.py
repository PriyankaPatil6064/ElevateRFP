from typing import Dict, Any, List, Optional, Tuple
import re
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, HistoricalDataTool


class RequirementAnalysisAgent(BaseElevateAgent):
    """Customer-facing elevator requirement extraction agent.

    Extracts only **customer-visible** requirements from RFP documents.
    Engineering specifications (pit depth, shaft size, machine room type,
    drive system, guide rails, etc.) are intentionally NOT extracted here —
    they are derived downstream after product selection, matching the real
    elevator quotation workflow:

        Customer requirements  →  Product recommendation
        →  Engineering specification  →  Pricing  →  Proposal

    Supported customer-level parameters (10)
    ─────────────────────────────────────────
        project_name, building_type, lift_type, capacity_kg, speed_ms,
        max_floors, stops, number_of_openings, door_type,
        special_requirements

    Domain validation
    ─────────────────
        Documents must contain ≥ 3 elevator-industry keywords to proceed.
        Invalid documents receive a normal response with
        ``is_valid_domain = False`` (no HTTP 500).

    Confidence
    ──────────
        ``confidence = extracted_count / 10``  (purely explainable)

    Missing values are always ``None``, never fabricated.
    """

    # ══════════════════════════════════════════════════════════════════════
    #  CONSTANTS
    # ══════════════════════════════════════════════════════════════════════

    DOMAIN_KEYWORDS: List[str] = [
        "elevator", "lift", "capacity", "floor", "shaft", "passenger",
        "hydraulic", "traction", "machine room", "v3f", "ard",
        "car operating panel", "guide rail", "landing door", "hoistway",
        "escalator", "dumbwaiter", "pit depth", "overhead", "car size",
        "door operator", "gearless", "mrl", "cop", "lop", "intercom",
        "overload", "fire service", "firefighter", "rope", "sheave",
        "counterweight", "governor", "buffer", "safety gear",
    ]
    DOMAIN_THRESHOLD: int = 3

    # The 10 customer-level parameters.
    TOTAL_SUPPORTED_PARAMETERS: int = 10

    # Names of the 10 customer-level fields (used in logging / stats).
    _CUSTOMER_FIELDS: List[str] = [
        "project_name", "building_type", "lift_type", "capacity_kg",
        "speed_ms", "max_floors", "stops", "number_of_openings",
        "door_type", "special_requirements",
    ]

    # ── Keyword → canonical-label maps ────────────────────────────────────

    _LIFT_TYPE_MAP: Dict[str, str] = {
        # Labels must exactly match supported_lift_types in config.py PRODUCTS.
        # Catalog values: Freight, Gearless Traction, Goods, Hydraulic, MRL, Passenger, Traction
        "passenger":         "Passenger",
        "freight":           "Freight",
        "goods":             "Goods",          # catalog has 'Goods' (ELV-FRT1)
        "cargo":             "Freight",
        # Hospital / bed / stretcher lifts are Passenger type in the catalog.
        # There is no 'Hospital' lift type in supported_lift_types.
        "hospital lift":     "Passenger",
        "bed lift":          "Passenger",
        "stretcher lift":    "Passenger",
        "panoramic":         "Passenger",      # panoramic cars are Passenger type
        "observation":       "Passenger",
        "hydraulic":         "Hydraulic",
        "traction":          "Traction",
        "mrl":               "MRL",
        "machine room less": "MRL",
        "machine-room-less": "MRL",
        "gearless":          "Gearless Traction",
        "geared":            "Traction",       # geared traction → Traction in catalog
    }

    _BUILDING_TYPE_MAP: Dict[str, str] = {
        # Labels must exactly match supported_building_types in config.py PRODUCTS.
        # Catalog values: Airport, Commercial, Government, Hospital, Hotel,
        #                 Industrial, Mixed-Use, Office, Residential, Retail,
        #                 Transit, Warehouse
        # Order: more-specific keywords first to prevent premature matches.
        "residential":  "Residential",
        "apartment":    "Residential",
        "housing":      "Residential",
        "mixed-use":    "Mixed-Use",      # before 'commercial' to avoid swallowing
        "mixed use":    "Mixed-Use",
        "hospital":     "Hospital",
        "medical":      "Hospital",
        "healthcare":   "Hospital",
        "office":       "Office",         # FIX: was 'Commercial' — catalog has 'Office'
        "corporate":    "Office",         # FIX: was 'Commercial'
        "commercial":   "Commercial",
        "warehouse":    "Warehouse",      # FIX: was 'Industrial' — catalog has 'Warehouse'
        "industrial":   "Industrial",
        "factory":      "Industrial",
        "hotel":        "Hotel",          # FIX: was 'Hospitality' — catalog has 'Hotel'
        "hospitality":  "Hotel",          # FIX: same
        "retail":       "Retail",
        "mall":         "Retail",
        "shopping":     "Retail",
        "government":   "Government",
        "airport":      "Airport",
        "metro":        "Transit",
        "station":      "Transit",
        # Removed: 'educational', 'school', 'university' — not in catalog
        # (they will map to None and be excluded from scoring)
    }

    _DOOR_TYPE_MAP: Dict[str, str] = {
        "center opening":  "Center Opening Automatic",
        "centre opening":  "Center Opening Automatic",
        "center open":     "Center Opening Automatic",
        "centre open":     "Center Opening Automatic",
        "co door":         "Center Opening Automatic",
        "side opening":    "Side Opening Automatic",
        "2-panel side":    "Side Opening Automatic",
        "telescopic":      "Telescopic",
        "manual":          "Manual Swing",
        "swing door":      "Manual Swing",
        "automatic door":  "Center Opening Automatic",
        "imperforated":    "Imperforated",
    }

    # Special requirements: customer-stated preferences and needs that
    # go beyond the core 9 numeric/categorical specs.
    _SPECIAL_REQUIREMENT_KEYWORDS: Dict[str, str] = {
        "fire service":        "Fire Service Mode",
        "firefighter":         "Fire Service Mode",
        "fire recall":         "Fire Service Mode",
        "intercom":            "Intercom System",
        "cctv":                "CCTV Monitoring",
        "camera":              "CCTV Monitoring",
        "emergency battery":   "Emergency Battery Backup",
        "battery backup":      "Emergency Battery Backup",
        "ups":                 "Emergency Battery Backup",
        "ard":                 "Automatic Rescue Device (ARD)",
        "automatic rescue":    "Automatic Rescue Device (ARD)",
        "overload":            "Overload Sensor",
        "regenerative":        "Regenerative Drive",
        "destination dispatch": "Destination Dispatch",
        "destination control":  "Destination Dispatch",
        "access control":      "Access Control System",
        "card reader":         "Access Control System",
        "biometric":           "Biometric Access",
        "voice announcement":  "Voice Announcement",
        "voice annunciation":  "Voice Announcement",
        "floor announcement":  "Voice Announcement",
        "emergency alarm":     "Emergency Alarm",
        "alarm bell":          "Emergency Alarm",
        "wheelchair":          "Wheelchair Accessible",
        "disabled":            "Disabled Access",
        "stretcher":           "Stretcher Size",
        "glass":               "Glass / Panoramic Car",
        "stainless steel":     "Stainless Steel Finish",
        "hairline":            "Hairline Finish",
        "marble":              "Marble Floor Finish",
        "granite":             "Granite Floor Finish",
        "false ceiling":       "False Ceiling",
        "handrail":            "Handrail",
        "mirror":              "Mirror in Car",
        "led lighting":        "LED Lighting",
        "car fan":             "Car Fan",
        "anti-vandal":         "Anti-Vandal Features",
        "earthquake":          "Seismic Operation Mode",
        "seismic":             "Seismic Operation Mode",
    }

    # ══════════════════════════════════════════════════════════════════════
    #  INIT
    # ══════════════════════════════════════════════════════════════════════

    def __init__(self):
        super().__init__(
            name="requirement_analyst",
            role="Senior Requirements Analyst",
            goal="Extract, categorize, and structure RFP requirements with high accuracy",
            backstory="""You are an expert requirements analyst with 15+ years of experience 
            in enterprise RFP analysis. You excel at identifying functional and non-functional 
            requirements, understanding implicit needs, and structuring complex requirements 
            into actionable specifications."""
        )

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute requirement analysis on the RFP content in *context*."""
        start_time = datetime.now()

        try:
            rfp_content = context.get("rfp_content", "")
            if not rfp_content:
                raise ValueError("No RFP content provided")

            text_lower = rfp_content.lower()

            # ── Step 0: Domain validation ────────────────────────────────
            is_valid, domain_hits, domain_matched = self._validate_elevator_domain(text_lower)

            self.logger.info(
                "[RequirementAnalysis] Domain validation: valid=%s, hits=%d/%d, matched=%s",
                is_valid, domain_hits, self.DOMAIN_THRESHOLD, domain_matched,
            )
            self.add_reasoning_trace(
                step="domain_validation",
                reasoning=(
                    f"Domain validation {'PASSED' if is_valid else 'FAILED'} — "
                    f"{domain_hits} elevator keyword(s) found "
                    f"(threshold={self.DOMAIN_THRESHOLD})"
                ),
                evidence=[{
                    "is_valid": is_valid,
                    "keyword_hits": domain_hits,
                    "threshold": self.DOMAIN_THRESHOLD,
                    "matched_keywords": domain_matched,
                }],
                confidence=1.0 if is_valid else 0.0,
            )

            # ── Invalid domain → normal response with nulls ─────────────
            if not is_valid:
                return self._build_invalid_domain_result(
                    start_time, domain_hits, domain_matched,
                )

            # ── Step 1: Extract 10 customer-level requirements ───────────
            basic_requirements, extraction_log = self._extract_customer_requirements(
                rfp_content, text_lower,
            )
            basic_requirements["is_valid_domain"] = True

            # ── Step 2: RAG retrieval (unchanged) ────────────────────────
            similar_rfps = await self.retrieve_knowledge(
                query=f"RFP requirements {' '.join(basic_requirements.get('keywords', [])[:4])}",
                filters={"document_type": "rfp"},
                top_k=5,
            )

            # ── Step 3: Categorize requirements (unchanged) ──────────────
            categorized_requirements = await self._categorize_requirements(
                rfp_content, similar_rfps,
            )

            # ── Step 4: Priority analysis (unchanged) ────────────────────
            requirement_priority = await self._analyze_requirement_priority(rfp_content)

            # ── Step 5: Structured summary ───────────────────────────────
            structured_summary = await self._generate_structured_summary(
                basic_requirements, categorized_requirements, requirement_priority,
            )

            # ── Confidence = extracted / 10 ──────────────────────────────
            extracted_count = extraction_log["extracted_count"]
            confidence_score = round(
                extracted_count / self.TOTAL_SUPPORTED_PARAMETERS, 4,
            )

            self.logger.info(
                "[RequirementAnalysis] Confidence: %.3f (%d/%d customer parameters)",
                confidence_score, extracted_count, self.TOTAL_SUPPORTED_PARAMETERS,
            )

            result = {
                "is_valid_domain": True,
                "basic_requirements": basic_requirements,
                "categorized_requirements": categorized_requirements,
                "requirement_priority": requirement_priority,
                "structured_summary": structured_summary,
                "analysis_metadata": {
                    "total_requirements": (
                        len(categorized_requirements.get("functional", []))
                        + len(categorized_requirements.get("non_functional", []))
                    ),
                    "mandatory_count": len(
                        [r for r in requirement_priority if r.get("priority") == "mandatory"]
                    ),
                    "optional_count": len(
                        [r for r in requirement_priority if r.get("priority") == "optional"]
                    ),
                    "confidence_score": confidence_score,
                    "extraction_stats": {
                        "total_parameters": self.TOTAL_SUPPORTED_PARAMETERS,
                        "extracted_count": extracted_count,
                        "missing_count": extraction_log["missing_count"],
                        "extracted_fields": extraction_log["extracted_fields"],
                        "missing_fields": extraction_log["missing_fields"],
                    },
                    "domain_validation": {
                        "is_valid": True,
                        "keyword_hits": domain_hits,
                        "matched_keywords": domain_matched,
                    },
                },
            }

            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                "[RequirementAnalysis] Completed in %.2fs — confidence=%.3f",
                execution_time, confidence_score,
            )

            return AgentResult(
                agent_name=self.name,
                result=result,
                reasoning_traces=self.reasoning_traces,
                confidence_score=confidence_score,
                execution_time=execution_time,
                retrieved_context=similar_rfps,
                citations=[r.get("source", "") for r in similar_rfps],
            )

        except Exception as e:
            self.logger.error(f"Requirement analysis failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  DOMAIN VALIDATION
    # ══════════════════════════════════════════════════════════════════════

    def _validate_elevator_domain(
        self, text_lower: str,
    ) -> Tuple[bool, int, List[str]]:
        """Return ``(is_valid, hit_count, matched_keywords)``."""
        matched = [kw for kw in self.DOMAIN_KEYWORDS if kw in text_lower]
        return len(matched) >= self.DOMAIN_THRESHOLD, len(matched), matched

    # ══════════════════════════════════════════════════════════════════════
    #  INVALID-DOMAIN RESPONSE BUILDER
    # ══════════════════════════════════════════════════════════════════════

    def _build_invalid_domain_result(
        self, start_time: datetime, domain_hits: int, domain_matched: List[str],
    ) -> AgentResult:
        """Return a **normal** AgentResult for non-elevator documents.

        All fields are ``None``, confidence is ``0.0``, and the pipeline
        can continue without producing an HTTP 500.
        """
        self.logger.warning(
            "[RequirementAnalysis] Document rejected — only %d elevator keyword(s) "
            "found (minimum %d required).  Returning empty extraction.",
            domain_hits, self.DOMAIN_THRESHOLD,
        )

        empty_basic = {
            # Backward-compatible keys
            "capacity_kg":         None,
            "max_floors":          None,
            "speed_ms":            None,
            "lift_type":           None,
            "building_type":       None,
            "power_supply":        None,
            "door_type":           None,
            "optional_features":   [],
            "keywords":            [],
            "raw_extractions":     {"capacities": [], "floors": [], "speeds": []},
            # Customer-level keys
            "project_name":        None,
            "stops":               None,
            "number_of_openings":  None,
            "special_requirements": [],
            "is_valid_domain":     False,
        }

        empty_summary = {
            "executive_summary": {
                "total_requirements": 0,
                "mandatory_requirements": 0,
                "optional_requirements": 0,
                "key_specifications": {f: None for f in self._CUSTOMER_FIELDS},
            },
            "functional_requirements":     {"count": 0, "requirements": []},
            "non_functional_requirements": {"count": 0, "requirements": []},
            "critical_requirements":       [],
            "optional_features":           [],
        }

        result = {
            "is_valid_domain": False,
            "message": (
                "Uploaded document does not appear to be an elevator-related RFP. "
                f"Only {domain_hits} elevator keyword(s) found "
                f"(minimum {self.DOMAIN_THRESHOLD} required)."
            ),
            "domain_validation": {
                "is_valid": False,
                "keyword_hits": domain_hits,
                "threshold": self.DOMAIN_THRESHOLD,
                "matched_keywords": domain_matched,
            },
            "basic_requirements":       empty_basic,
            "categorized_requirements": {"functional": [], "non_functional": []},
            "requirement_priority":     [],
            "structured_summary":       empty_summary,
            "analysis_metadata": {
                "total_requirements": 0,
                "mandatory_count":    0,
                "optional_count":     0,
                "confidence_score":   0.0,
                "extraction_stats": {
                    "total_parameters": self.TOTAL_SUPPORTED_PARAMETERS,
                    "extracted_count":  0,
                    "missing_count":    self.TOTAL_SUPPORTED_PARAMETERS,
                    "extracted_fields": [],
                    "missing_fields":   list(self._CUSTOMER_FIELDS),
                },
                "domain_validation": {
                    "is_valid": False,
                    "keyword_hits": domain_hits,
                    "matched_keywords": domain_matched,
                },
            },
        }

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResult(
            agent_name=self.name,
            result=result,
            reasoning_traces=self.reasoning_traces,
            confidence_score=0.0,
            execution_time=execution_time,
            retrieved_context=[],
            citations=[],
        )

    # ══════════════════════════════════════════════════════════════════════
    #  CUSTOMER-LEVEL REQUIREMENT EXTRACTION  (10 parameters)
    # ══════════════════════════════════════════════════════════════════════

    def _extract_customer_requirements(
        self, rfp_content: str, text_lower: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract the 10 customer-visible requirements.

        Engineering specifications (pit depth, shaft size, drive type,
        machine room, guide rails, etc.) are **intentionally omitted**.
        Those are design decisions made later after product selection.

        Returns ``(basic_requirements_dict, extraction_log_dict)``.
        """

        # 1. Project name
        project_name = self._extract_project_name(rfp_content)

        # 2. Building type
        building_type = self._detect_field(text_lower, self._BUILDING_TYPE_MAP)

        # 3. Lift type
        lift_type = self._detect_field(text_lower, self._LIFT_TYPE_MAP)

        # 4. Capacity (kg)
        capacity_kg = self._extract_capacity(rfp_content)

        # 5. Speed (m/s)
        speed_ms = self._extract_speed(rfp_content)

        # 6. Number of floors
        max_floors = self._extract_numeric(rfp_content, [
            r'(\d+)\s*(?:floor|storey|story|stories|level)s?',
            r'(?:floor|storey|story|level)s?\s*[:\-\u2013]\s*(\d+)',
            r'(\d+)\s*(?:fl|flr)s?\b',
            r'(?:number of floors|total floors|no\.?\s*of floors)\s*[:\-\u2013]?\s*(\d+)',
        ], 1, 200, "max_floors")

        # 7. Stops
        stops = self._extract_numeric(rfp_content, [
            r'(\d+)\s*stops?\b',
            r'(?:number of stops|no\.?\s*of stops|total stops)\s*[:\-\u2013]?\s*(\d+)',
            r'stops?\s*[:\-\u2013]\s*(\d+)',
        ], 2, 200, "stops")

        # 8. Number of openings
        number_of_openings = self._extract_numeric(rfp_content, [
            r'(\d+)\s*openings?\b',
            r'(?:number of openings|no\.?\s*of openings)\s*[:\-\u2013]?\s*(\d+)',
            r'openings?\s*[:\-\u2013]\s*(\d+)',
            r'(\d+)\s*(?:front\s*(?:and|&)\s*rear|opposite)\s*openings?',
        ], 1, 200, "number_of_openings")

        # 9. Door type
        door_type = self._detect_field(text_lower, self._DOOR_TYPE_MAP)

        # 10. Special requirements (customer-stated preferences)
        special_requirements = self._detect_feature_list(
            text_lower, self._SPECIAL_REQUIREMENT_KEYWORDS,
        )

        # ── Also extract backward-compatible auxiliary fields ────────────
        keywords = self._extract_keywords(text_lower)

        # optional_features is preserved for backward compatibility.
        # It is the same list as special_requirements — downstream agents
        # that read optional_features continue to work unchanged.
        optional_features = list(special_requirements)

        # ── Build per-field log ──────────────────────────────────────────
        field_values = {
            "project_name":        project_name,
            "building_type":       building_type,
            "lift_type":           lift_type,
            "capacity_kg":         capacity_kg,
            "speed_ms":            speed_ms,
            "max_floors":          max_floors,
            "stops":               stops,
            "number_of_openings":  number_of_openings,
            "door_type":           door_type,
            # list → counted as extracted if non-empty
            "special_requirements": special_requirements if special_requirements else None,
        }

        extracted_fields: List[str] = []
        missing_fields: List[str] = []

        for name, value in field_values.items():
            if value is not None:
                extracted_fields.append(name)
                self.logger.info("[RequirementAnalysis] \u2713 %s = %s", name, value)
            else:
                missing_fields.append(name)
                self.logger.info("[RequirementAnalysis] \u2717 %s = None (not found in document)", name)

        extracted_count = len(extracted_fields)
        missing_count = len(missing_fields)

        self.logger.info(
            "[RequirementAnalysis] Extraction complete: %d/%d customer fields",
            extracted_count, self.TOTAL_SUPPORTED_PARAMETERS,
        )
        if missing_fields:
            self.logger.info(
                "[RequirementAnalysis] Missing: %s", ", ".join(missing_fields),
            )

        self.add_reasoning_trace(
            step="customer_extraction",
            reasoning=(
                f"Extracted {extracted_count}/{self.TOTAL_SUPPORTED_PARAMETERS} "
                f"customer-level parameters. "
                f"Missing: {', '.join(missing_fields) if missing_fields else 'none'}. "
                f"Engineering specs (pit depth, shaft size, drive type, etc.) are "
                f"intentionally deferred to downstream agents after product selection."
            ),
            evidence=[{
                "extracted_count": extracted_count,
                "total_parameters": self.TOTAL_SUPPORTED_PARAMETERS,
                "extracted_fields": extracted_fields,
                "missing_fields": missing_fields,
                "special_requirements_count": len(special_requirements),
                "keywords_count": len(keywords),
            }],
            confidence=round(extracted_count / self.TOTAL_SUPPORTED_PARAMETERS, 4),
        )

        extraction_log = {
            "extracted_count": extracted_count,
            "missing_count": missing_count,
            "extracted_fields": extracted_fields,
            "missing_fields": missing_fields,
        }

        # ── Assemble basic_requirements ──────────────────────────────────
        # All backward-compatible keys are present.  Engineering specs
        # that were never customer-level are simply absent from this dict.
        basic_requirements = {
            # ── Backward-compatible keys ─────────────────────────────────
            "capacity_kg":         capacity_kg,
            "max_floors":          max_floors,
            "speed_ms":            speed_ms,
            "lift_type":           lift_type,
            "building_type":       building_type,
            "power_supply":        None,  # engineering decision — derived later
            "door_type":           door_type,
            "optional_features":   optional_features,
            "keywords":            keywords,
            "raw_extractions": {
                "capacities": [capacity_kg] if capacity_kg else [],
                "floors":     [max_floors] if max_floors else [],
                "speeds":     [speed_ms] if speed_ms else [],
            },
            # ── New customer-level keys ──────────────────────────────────
            "project_name":        project_name,
            "stops":               stops,
            "number_of_openings":  number_of_openings,
            "special_requirements": special_requirements,
        }

        return basic_requirements, extraction_log

    # ══════════════════════════════════════════════════════════════════════
    #  INDIVIDUAL EXTRACTORS
    # ══════════════════════════════════════════════════════════════════════

    def _extract_project_name(self, text: str) -> Optional[str]:
        """Extract project name / RFP title from text."""
        patterns = [
            r'(?:project\s*(?:name|title))\s*[:\-\u2013]\s*(.+)',
            r'(?:rfp|request\s*for\s*proposal)\s*[:\-\u2013]\s*(.+)',
            r'(?:tender|bid)\s*(?:for|:)\s*(.+)',
            r'(?:subject|re)\s*[:\-\u2013]\s*(.+?(?:elevator|lift|escalator).+)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                name = re.split(r'[.\n]', m.group(1).strip())[0].strip()
                if 5 <= len(name) <= 200:
                    return name
        return None

    def _extract_capacity(self, text: str) -> Optional[int]:
        """Extract load capacity in kg."""
        patterns_and_multipliers = [
            (r'(\d+)\s*kg\b', 1),
            (r'(\d+)\s*kilogram', 1),
            (r'capacity\s*[:\-\u2013]?\s*(\d+)\s*kg', 1),
            (r'(?:load|rated)\s*(?:capacity)?\s*[:\-\u2013]?\s*(\d+)\s*kg', 1),
            (r'(\d+)\s*(?:person|passenger|pax)s?\b', 75),
            (r'capacity\s*[:\-\u2013]?\s*(\d+)\s*(?:lb|pound)s?', 0.4536),
        ]
        values: List[int] = []
        for pat, mult in patterns_and_multipliers:
            for m in re.finditer(pat, text, re.IGNORECASE):
                val = int(float(m.group(1)) * mult)
                if 100 <= val <= 50000:
                    values.append(val)
        return max(values) if values else None

    def _extract_speed(self, text: str) -> Optional[float]:
        """Extract speed in m/s.

        Only patterns with explicit speed units are used.
        The bare ``speed: NUMBER`` pattern (no unit) has been removed — it
        incorrectly matched RPM, VFD frequency, or other numeric fields.
        """
        patterns_and_multipliers = [
            # Explicit m/s — highest confidence
            (r'(\d+(?:\.\d+)?)\s*m\s*/\s*s', 1.0),
            (r'(\d+(?:\.\d+)?)\s*mps\b', 1.0),
            (r'speed\s*[:\-\u2013]?\s*(\d+(?:\.\d+)?)\s*m\s*/\s*s', 1.0),
            # ft/min conversion
            (r'(\d+(?:\.\d+)?)\s*(?:fpm|ft\s*/\s*min)', 0.00508),
        ]
        values: List[float] = []
        for pat, mult in patterns_and_multipliers:
            for m in re.finditer(pat, text, re.IGNORECASE):
                val = round(float(m.group(1)) * mult, 2)
                if 0.1 <= val <= 20.0:
                    values.append(val)
        return max(values) if values else None

    def _extract_numeric(
        self, text: str, patterns: List[str],
        min_val: int, max_val: int, label: str,
    ) -> Optional[int]:
        """Extract the largest in-range integer matching any pattern."""
        values: List[int] = []
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                raw = m.group(m.lastindex) if m.lastindex else m.group(1)
                try:
                    val = int(raw)
                except (ValueError, TypeError):
                    continue
                if min_val <= val <= max_val:
                    values.append(val)
        return max(values) if values else None

    # ── Keyword detectors ────────────────────────────────────────────────

    @staticmethod
    def _detect_field(
        text_lower: str, keyword_map: Dict[str, str],
    ) -> Optional[str]:
        """Return canonical label for first matched keyword, or ``None``."""
        for keyword, label in keyword_map.items():
            if keyword in text_lower:
                return label
        return None

    @staticmethod
    def _detect_feature_list(
        text_lower: str, keyword_map: Dict[str, str],
    ) -> List[str]:
        """Return deduplicated list of matched features."""
        found: List[str] = []
        seen: set = set()
        for keyword, feature_name in keyword_map.items():
            if keyword in text_lower and feature_name not in seen:
                found.append(feature_name)
                seen.add(feature_name)
        return found

    @staticmethod
    def _extract_keywords(text_lower: str) -> List[str]:
        """Extract domain keywords present in text."""
        keyword_list = [
            'elevator', 'lift', 'escalator', 'accessibility', 'ada',
            'compliance', 'safety', 'maintenance', 'installation',
            'modernization', 'upgrade', 'energy', 'efficiency', 'green',
            'sustainable', 'smart', 'iot', 'monitoring', 'remote',
            'predictive', 'analytics', 'traction', 'hydraulic', 'mrl',
            'machine room', 'gearless', 'fire service', 'intercom',
            'cctv', 'vfd', 'regenerative', 'v3f', 'guide rail',
            'car operating panel', 'landing door', 'pit depth',
            'overhead', 'shaft', 'hoistway', 'ard', 'governor',
            'buffer', 'safety gear',
        ]
        return [kw for kw in keyword_list if kw in text_lower]

    # ══════════════════════════════════════════════════════════════════════
    #  CATEGORIZATION & PRIORITY  (unchanged from original)
    # ══════════════════════════════════════════════════════════════════════

    async def _categorize_requirements(
        self, rfp_content: str, similar_rfps: List[Dict],
    ) -> Dict[str, List[str]]:
        """Categorize requirements into functional and non-functional."""

        context_patterns = []
        for rfp in similar_rfps:
            if rfp.get("metadata", {}).get("requirement_categories"):
                context_patterns.extend(rfp["metadata"]["requirement_categories"])

        functional_indicators = [
            'capacity', 'speed', 'floors', 'doors', 'controls', 'operation',
            'functionality', 'features', 'interface', 'system', 'mechanism',
            'elevator', 'lift', 'car size', 'hoistway', 'shaft',
        ]
        non_functional_indicators = [
            'performance', 'reliability', 'availability', 'security',
            'compliance', 'safety', 'efficiency', 'maintenance', 'support',
            'warranty', 'response time', 'uptime', 'scalability', 'noise',
            'vibration',
        ]

        sentences = re.split(r'[.!?\n]+', rfp_content)
        functional_requirements: List[str] = []
        non_functional_requirements: List[str] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            s_lower = sentence.lower()
            f_score = sum(1 for i in functional_indicators if i in s_lower)
            nf_score = sum(1 for i in non_functional_indicators if i in s_lower)
            if f_score > nf_score:
                functional_requirements.append(sentence)
            elif nf_score > 0:
                non_functional_requirements.append(sentence)

        self.add_reasoning_trace(
            step="requirement_categorization",
            reasoning=(
                f"Categorized {len(functional_requirements)} functional and "
                f"{len(non_functional_requirements)} non-functional requirements"
            ),
            evidence=[{
                "functional_count": len(functional_requirements),
                "non_functional_count": len(non_functional_requirements),
                "context_rfps": len(similar_rfps),
            }],
            confidence=0.85,
        )

        return {
            "functional": functional_requirements,
            "non_functional": non_functional_requirements,
        }

    async def _analyze_requirement_priority(
        self, rfp_content: str,
    ) -> List[Dict[str, Any]]:
        """Analyze requirement priority (mandatory vs optional)."""

        mandatory_indicators = [
            'must', 'shall', 'required', 'mandatory', 'essential',
            'critical', 'necessary', 'compulsory', 'obligatory',
        ]
        optional_indicators = [
            'should', 'could', 'may', 'optional', 'preferred',
            'desirable', 'nice to have', 'if possible', 'ideally',
        ]

        sentences = re.split(r'[.!?\n]+', rfp_content)
        requirements: List[Dict[str, Any]] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            s_lower = sentence.lower()
            m_score = sum(1 for i in mandatory_indicators if i in s_lower)
            o_score = sum(1 for i in optional_indicators if i in s_lower)
            if m_score > 0 or o_score > 0:
                priority = "mandatory" if m_score >= o_score else "optional"
                confidence = max(m_score, o_score) / (m_score + o_score + 1)
                requirements.append({
                    "requirement": sentence,
                    "priority": priority,
                    "confidence": confidence,
                    "indicators": {
                        "mandatory_score": m_score,
                        "optional_score": o_score,
                    },
                })

        self.add_reasoning_trace(
            step="priority_analysis",
            reasoning=f"Analyzed priority for {len(requirements)} requirements",
            evidence=[{"requirements_analyzed": len(requirements)}],
            confidence=0.8,
        )
        return requirements

    # ── Structured summary ───────────────────────────────────────────────

    async def _generate_structured_summary(
        self, basic_req: Dict, categorized_req: Dict, priority_req: List,
    ) -> Dict[str, Any]:
        """Generate structured requirement summary."""

        summary = {
            "executive_summary": {
                "total_requirements": (
                    len(categorized_req.get("functional", []))
                    + len(categorized_req.get("non_functional", []))
                ),
                "mandatory_requirements": len(
                    [r for r in priority_req if r.get("priority") == "mandatory"]
                ),
                "optional_requirements": len(
                    [r for r in priority_req if r.get("priority") == "optional"]
                ),
                "key_specifications": {
                    "project_name":        basic_req.get("project_name"),
                    "building_type":       basic_req.get("building_type"),
                    "lift_type":           basic_req.get("lift_type"),
                    "capacity_kg":         basic_req.get("capacity_kg"),
                    "speed_ms":            basic_req.get("speed_ms"),
                    "max_floors":          basic_req.get("max_floors"),
                    "stops":               basic_req.get("stops"),
                    "number_of_openings":  basic_req.get("number_of_openings"),
                    "door_type":           basic_req.get("door_type"),
                },
            },
            "functional_requirements": {
                "count": len(categorized_req.get("functional", [])),
                "requirements": categorized_req.get("functional", [])[:10],
            },
            "non_functional_requirements": {
                "count": len(categorized_req.get("non_functional", [])),
                "requirements": categorized_req.get("non_functional", [])[:10],
            },
            "critical_requirements": [
                r for r in priority_req
                if r.get("priority") == "mandatory" and r.get("confidence", 0) > 0.7
            ][:5],
            "optional_features": basic_req.get("optional_features", []),
            "special_requirements": basic_req.get("special_requirements", []),
        }

        self.add_reasoning_trace(
            step="summary_generation",
            reasoning=(
                "Generated structured summary with 10 customer-level fields.  "
                "Engineering specs deferred to downstream agents."
            ),
            evidence=[summary],
            confidence=0.9,
        )
        return summary

    # ══════════════════════════════════════════════════════════════════════
    #  TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def get_tools(self) -> List:
        """Get agent-specific tools."""
        return [KnowledgeSearchTool(), HistoricalDataTool()]