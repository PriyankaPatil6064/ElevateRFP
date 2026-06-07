from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, ProductMatchingTool, HistoricalDataTool
from config import PRODUCTS


class ProductMatchingAgent(BaseElevateAgent):
    """Platform-aware product matching agent.

    Selects the best elevator **platform** (not a fixed engineering
    configuration) for a given set of customer requirements using
    deterministic weighted scoring.

    Scoring dimensions (6, weighted):
        capacity_compatibility          25 %
        floor_compatibility             20 %
        speed_compatibility             15 %
        building_type_compatibility     15 %
        lift_type_compatibility         15 %
        special_requirements_coverage   10 %

    Unknown / unextracted requirements are **excluded from the
    denominator** so they neither reward nor penalise a platform.
    Coverage is computed only over requirements actually available.

    The LLM is never used for selection — it may only explain the
    result after deterministic scoring is complete.
    """

    # ── Dimension weights ────────────────────────────────────────────────
    WEIGHT_CAPACITY  = 0.25
    WEIGHT_FLOORS    = 0.20
    WEIGHT_SPEED     = 0.15
    WEIGHT_BUILDING  = 0.15
    WEIGHT_LIFT_TYPE = 0.15
    WEIGHT_SPECIAL   = 0.10

    def __init__(self):
        super().__init__(
            name="product_matcher",
            role="Senior Product Matching Specialist",
            goal="Find optimal product matches for RFP requirements using deterministic scoring",
            backstory="""You are an expert product specialist with deep knowledge of elevator 
            systems and 20+ years of experience matching customer requirements to optimal 
            product solutions. You excel at understanding both explicit and implicit needs."""
        )

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute product matching analysis."""
        start_time = datetime.now()

        try:
            requirements = context.get("requirements", {})
            if not requirements:
                raise ValueError("No requirements provided from requirement analysis")

            # ── Stage 1: Extract customer specifications ─────────────────
            specifications = self._extract_specifications(requirements)

            # ── Stage 2: Candidate retrieval (FAISS → full catalog) ──────
            candidates = await self._retrieve_candidates(specifications)

            # ── Stage 3: Deterministic scoring ───────────────────────────
            scored_matches = self._score_platforms(specifications, candidates)

            # ── Stage 4: Top 3 (never zero) ──────────────────────────────
            top_matches = scored_matches[:3]

            # ── Stage 5: Recommendations ─────────────────────────────────
            recommendations = self._generate_recommendations(
                top_matches, specifications,
            )

            # ── Overall coverage ─────────────────────────────────────────
            primary_coverage = (
                top_matches[0]["coverage_score"] if top_matches else 0.0
            )

            result = {
                "specifications": specifications,
                "product_matches": top_matches,
                "recommendations": recommendations,
                "matching_metadata": {
                    "total_products_evaluated": len(candidates),
                    "high_confidence_matches": len(
                        [m for m in top_matches if m.get("coverage_score", 0) > 0.80]
                    ),
                    "case_studies_found": 0,
                    "overall_confidence": primary_coverage,
                    "requirement_coverage_percentage": round(
                        primary_coverage * 100, 1,
                    ),
                },
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                "[ProductMatching] Completed in %.2fs — primary=%s coverage=%.1f%%",
                execution_time,
                top_matches[0]["product_id"] if top_matches else "none",
                primary_coverage * 100,
            )

            return AgentResult(
                agent_name=self.name,
                result=result,
                reasoning_traces=self.reasoning_traces,
                confidence_score=primary_coverage,
                execution_time=execution_time,
                retrieved_context=[],
                citations=[],
            )

        except Exception as e:
            self.logger.error(f"Product matching failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  STAGE 1 — SPECIFICATION EXTRACTION
    # ══════════════════════════════════════════════════════════════════════

    def _extract_specifications(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Extract customer-level specs from the upstream requirement result."""

        basic_req = requirements.get("basic_requirements", {})
        structured_summary = requirements.get("structured_summary", {})

        specifications = {
            "capacity_kg":    basic_req.get("capacity_kg"),
            "max_floors":     basic_req.get("max_floors"),
            "speed_ms":       basic_req.get("speed_ms"),
            "lift_type":      basic_req.get("lift_type"),
            "building_type":  basic_req.get("building_type"),
            "keywords":       basic_req.get("keywords", []),
            "special_requirements": basic_req.get("special_requirements",
                                    basic_req.get("optional_features", [])),
            "functional_requirements": (
                structured_summary.get("functional_requirements", {})
                .get("requirements", [])
            ),
            "critical_requirements": structured_summary.get(
                "critical_requirements", [],
            ),
        }

        # Parse additional feature flags (unchanged from original)
        additional = self._parse_functional_requirements(
            specifications["functional_requirements"],
        )
        specifications.update(additional)

        available_dims = [
            k for k in ("capacity_kg", "max_floors", "speed_ms",
                         "building_type", "lift_type")
            if specifications.get(k) is not None
        ]
        if specifications.get("special_requirements"):
            available_dims.append("special_requirements")

        self.logger.info(
            "[ProductMatching] Extracted specifications — "
            "available dimensions: %s (%d/6)",
            ", ".join(available_dims), len(available_dims),
        )

        self.add_reasoning_trace(
            step="specification_extraction",
            reasoning=(
                f"Extracted specifications from requirement analysis.  "
                f"{len(available_dims)}/6 scoring dimensions available: "
                f"{', '.join(available_dims)}"
            ),
            evidence=[specifications],
            confidence=0.9,
        )

        return specifications

    def _parse_functional_requirements(
        self, functional_requirements: List[str],
    ) -> Dict[str, Any]:
        """Parse additional feature flags from functional requirements."""

        additional_specs = {
            "accessibility_required":        False,
            "energy_efficiency_required":    False,
            "smart_features_required":       False,
            "maintenance_contract_required": False,
            "custom_finishes_required":      False,
        }

        for req in functional_requirements:
            req_lower = req.lower()

            if any(kw in req_lower for kw in ['ada', 'accessibility', 'disabled', 'wheelchair']):
                additional_specs["accessibility_required"] = True

            if any(kw in req_lower for kw in ['energy', 'efficient', 'green', 'sustainable']):
                additional_specs["energy_efficiency_required"] = True

            if any(kw in req_lower for kw in ['smart', 'iot', 'monitoring', 'predictive']):
                additional_specs["smart_features_required"] = True

            if any(kw in req_lower for kw in ['maintenance', 'service', 'support']):
                additional_specs["maintenance_contract_required"] = True

            if any(kw in req_lower for kw in ['custom', 'finish', 'design', 'aesthetic']):
                additional_specs["custom_finishes_required"] = True

        return additional_specs

    # ══════════════════════════════════════════════════════════════════════
    #  STAGE 2 — CANDIDATE RETRIEVAL
    # ══════════════════════════════════════════════════════════════════════

    async def _retrieve_candidates(
        self, specifications: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Retrieve candidate platforms.

        Attempts FAISS / RAG retrieval first.  If it returns nothing
        or fails, falls back to the full ``PRODUCTS`` catalog.
        Selection must never fail.
        """

        try:
            keyword_parts = []
            if specifications.get("building_type"):
                keyword_parts.append(specifications["building_type"])
            if specifications.get("lift_type"):
                keyword_parts.append(specifications["lift_type"])
            keyword_parts.extend(specifications.get("keywords", [])[:3])

            if keyword_parts:
                query = f"elevator platform {' '.join(keyword_parts)}"
                rag_results = await self.retrieve_knowledge(
                    query=query,
                    filters={"document_type": "product_catalog"},
                    top_k=10,
                )
                if rag_results:
                    self.logger.info(
                        "[ProductMatching] RAG returned %d candidates",
                        len(rag_results),
                    )
        except Exception as e:
            self.logger.warning(
                "[ProductMatching] RAG retrieval failed (%s), using full catalog",
                e,
            )

        # Always score the full catalog — RAG results are informational
        self.logger.info(
            "[ProductMatching] Using full catalog (%d platforms)", len(PRODUCTS),
        )
        return list(PRODUCTS)

    # ══════════════════════════════════════════════════════════════════════
    #  STAGE 3 — DETERMINISTIC SCORING
    # ══════════════════════════════════════════════════════════════════════

    def _score_platforms(
        self,
        specifications: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Score every candidate platform deterministically.

        Unknown requirements are excluded from the denominator so they
        neither inflate nor deflate coverage.
        """

        req_capacity = specifications.get("capacity_kg")
        req_floors   = specifications.get("max_floors")
        req_speed    = specifications.get("speed_ms")
        req_building = specifications.get("building_type")
        req_lift     = specifications.get("lift_type")
        req_special  = specifications.get("special_requirements", [])

        scored: List[Dict[str, Any]] = []

        for product in candidates:
            dimension_scores, coverage_details = self._score_single_platform(
                product,
                req_capacity, req_floors, req_speed,
                req_building, req_lift, req_special,
            )

            # ── Compute weighted coverage over available dimensions ──────
            active_weights: List[Tuple[str, float, float]] = []

            if req_capacity is not None:
                active_weights.append(("capacity", self.WEIGHT_CAPACITY, dimension_scores["capacity"]))
            if req_floors is not None:
                active_weights.append(("floors", self.WEIGHT_FLOORS, dimension_scores["floors"]))
            if req_speed is not None:
                active_weights.append(("speed", self.WEIGHT_SPEED, dimension_scores["speed"]))
            if req_building is not None:
                active_weights.append(("building_type", self.WEIGHT_BUILDING, dimension_scores["building_type"]))
            if req_lift is not None:
                active_weights.append(("lift_type", self.WEIGHT_LIFT_TYPE, dimension_scores["lift_type"]))
            if req_special:
                active_weights.append(("special_requirements", self.WEIGHT_SPECIAL, dimension_scores["special_requirements"]))

            if active_weights:
                total_weight = sum(w for _, w, _ in active_weights)
                coverage_score = round(
                    sum(w * s for _, w, s in active_weights) / total_weight, 4,
                )
            else:
                # No requirements at all — give neutral score
                coverage_score = 0.5

            scored.append({
                # ── Backward-compatible keys ─────────────────────────────
                "product_id":       product["id"],
                "confidence_score": coverage_score,  # mirrors coverage_score
                "specification_scores": dimension_scores,
                "metadata": {
                    "product_id":   product["id"],
                    "model":        product["name"],
                    "capacity_kg":  product["capacity"],
                    "max_floors":   product["max_floors"],
                    "speed_ms":     product["speed"],
                    "base_price":   product["base_price"],
                    # New additive keys
                    "tier":         product.get("tier", "Unknown"),
                    "description":  product.get("description", ""),
                },
                "match_explanation": self._build_match_explanation(
                    product, dimension_scores, coverage_score, active_weights,
                ),
                # ── New additive keys ────────────────────────────────────
                "coverage_score": coverage_score,
                "coverage_details": coverage_details,
                "selection_rationale": self._build_selection_rationale(
                    product, dimension_scores, coverage_details, coverage_score,
                ),
            })

        # Sort: coverage desc → base_price asc (tie-breaker)
        scored.sort(
            key=lambda m: (-m["coverage_score"], m["metadata"]["base_price"]),
        )

        self.logger.info(
            "[ProductMatching] Scored %d platforms — top: %s (%.1f%%)",
            len(scored),
            scored[0]["product_id"] if scored else "none",
            scored[0]["coverage_score"] * 100 if scored else 0,
        )

        self.add_reasoning_trace(
            step="deterministic_platform_scoring",
            reasoning=(
                f"Scored {len(scored)} platforms using {len(active_weights)}/6 "
                f"available dimensions.  "
                f"Weights: {', '.join(f'{n}={w:.0%}' for n, w, _ in active_weights)}."
            ),
            evidence=[{
                "top_product": scored[0]["product_id"] if scored else None,
                "top_coverage": scored[0]["coverage_score"] if scored else 0,
                "active_dimensions": len(active_weights),
                "top_3": [
                    {"id": m["product_id"], "coverage": m["coverage_score"]}
                    for m in scored[:3]
                ],
            }],
            confidence=0.95,
        )

        return scored

    # ── Score a single platform across all 6 dimensions ──────────────────

    def _score_single_platform(
        self,
        product: Dict[str, Any],
        req_capacity: Optional[int],
        req_floors: Optional[int],
        req_speed: Optional[float],
        req_building: Optional[str],
        req_lift: Optional[str],
        req_special: List[str],
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """Return ``(dimension_scores_dict, coverage_details_list)``."""

        coverage_details: List[Dict[str, Any]] = []

        # ── 1. Capacity ─────────────────────────────────────────────────
        cap_range = product.get("recommended_capacity_range", {})
        cap_score = self._range_score(
            req_capacity,
            cap_range.get("min", product["capacity"]),
            cap_range.get("max", product["capacity"]),
        )
        if req_capacity is not None:
            coverage_details.append({
                "requirement": f"Capacity {req_capacity} kg",
                "dimension": "capacity",
                "status": "satisfied" if cap_score >= 1.0 else "partial",
                "score": round(cap_score, 4),
                "platform_range": f"{cap_range.get('min', '?')}–{cap_range.get('max', '?')} kg",
            })

        # ── 2. Floors ───────────────────────────────────────────────────
        flr_range = product.get("recommended_floor_range", {})
        flr_score = self._range_score(
            req_floors,
            flr_range.get("min", 0),
            flr_range.get("max", product["max_floors"]),
        )
        if req_floors is not None:
            coverage_details.append({
                "requirement": f"{req_floors} floors",
                "dimension": "floors",
                "status": "satisfied" if flr_score >= 1.0 else "partial",
                "score": round(flr_score, 4),
                "platform_range": f"{flr_range.get('min', '?')}–{flr_range.get('max', '?')} floors",
            })

        # ── 3. Speed ────────────────────────────────────────────────────
        spd_range = product.get("recommended_speed_range", {})
        spd_score = self._range_score(
            req_speed,
            spd_range.get("min", 0),
            spd_range.get("max", product["speed"]),
        )
        if req_speed is not None:
            coverage_details.append({
                "requirement": f"Speed {req_speed} m/s",
                "dimension": "speed",
                "status": "satisfied" if spd_score >= 1.0 else "partial",
                "score": round(spd_score, 4),
                "platform_range": f"{spd_range.get('min', '?')}–{spd_range.get('max', '?')} m/s",
            })

        # ── 4. Building type ────────────────────────────────────────────
        supported_buildings = product.get("supported_building_types", [])
        bldg_score = self._set_membership_score(req_building, supported_buildings)
        if req_building is not None:
            coverage_details.append({
                "requirement": f"Building type: {req_building}",
                "dimension": "building_type",
                "status": "satisfied" if bldg_score >= 1.0 else "not_supported",
                "score": round(bldg_score, 4),
                "platform_supports": supported_buildings,
            })

        # ── 5. Lift type ────────────────────────────────────────────────
        supported_lifts = product.get("supported_lift_types", [])
        lift_score = self._set_membership_score(req_lift, supported_lifts)
        if req_lift is not None:
            coverage_details.append({
                "requirement": f"Lift type: {req_lift}",
                "dimension": "lift_type",
                "status": "satisfied" if lift_score >= 1.0 else "not_supported",
                "score": round(lift_score, 4),
                "platform_supports": supported_lifts,
            })

        # ── 6. Special requirements ─────────────────────────────────────
        premium_features = product.get("premium_features_available", [])
        special_score, special_details = self._special_requirements_score(
            req_special, premium_features,
        )
        coverage_details.extend(special_details)

        dimension_scores = {
            "capacity":              round(cap_score, 4),
            "floors":                round(flr_score, 4),
            "speed":                 round(spd_score, 4),
            "building_type":         round(bldg_score, 4),
            "lift_type":             round(lift_score, 4),
            "special_requirements":  round(special_score, 4),
        }

        return dimension_scores, coverage_details

    # ══════════════════════════════════════════════════════════════════════
    #  SCORING HELPERS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _range_score(
        value: Optional[float], range_min: float, range_max: float,
    ) -> float:
        """Score a numeric value against a recommended range.

        - Within range → 1.0
        - Below min    → value / min  (partial, 0.0 – 1.0)
        - Above max    → max / value  (partial, 0.0 – 1.0)
        - ``None``     → 1.0  (excluded from denominator upstream)
        """
        if value is None:
            return 1.0
        if range_min <= value <= range_max:
            return 1.0
        if value < range_min:
            return value / range_min if range_min > 0 else 0.0
        # value > range_max
        return range_max / value if value > 0 else 0.0

    @staticmethod
    def _set_membership_score(
        value: Optional[str], supported: List[str],
    ) -> float:
        """Score a categorical value against a supported set.

        - In set         → 1.0
        - Not in set     → 0.0
        - ``None``       → 1.0  (excluded from denominator upstream)
        """
        if value is None:
            return 1.0
        if not supported:
            return 0.0
        # Case-insensitive match
        value_lower = value.lower()
        for s in supported:
            if s.lower() == value_lower:
                return 1.0
        return 0.0

    @staticmethod
    def _special_requirements_score(
        requirements: List[str], premium_features: List[str],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Score special requirements against premium features.

        Uses substring matching to handle naming variations
        (e.g. "CCTV Monitoring" matches "CCTV Integration").

        Returns ``(score, details_list)``.
        """
        if not requirements:
            return 1.0, []

        features_lower = [f.lower() for f in premium_features]
        details: List[Dict[str, Any]] = []
        matched = 0

        for req in requirements:
            req_lower = req.lower()
            # Extract key terms (first meaningful word or acronym)
            req_tokens = set(req_lower.replace("(", " ").replace(")", " ").split())

            found = False
            for feat_lower in features_lower:
                feat_tokens = set(feat_lower.replace("(", " ").replace(")", " ").split())
                # Match if any significant token overlaps (>2 chars to skip "a", "in")
                overlap = {t for t in req_tokens & feat_tokens if len(t) > 2}
                if overlap:
                    found = True
                    break

            if found:
                matched += 1
                details.append({
                    "requirement": req,
                    "dimension": "special_requirements",
                    "status": "available",
                    "score": 1.0,
                })
            else:
                details.append({
                    "requirement": req,
                    "dimension": "special_requirements",
                    "status": "not_available",
                    "score": 0.0,
                })

        score = matched / len(requirements)
        return round(score, 4), details

    # ══════════════════════════════════════════════════════════════════════
    #  STAGE 4+5 — RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════════════════

    def _generate_recommendations(
        self,
        top_matches: List[Dict],
        specifications: Dict,
    ) -> Dict[str, Any]:
        """Build recommendation structure from scored matches.

        Guarantees at least one recommendation (fallback to cheapest).
        """

        if not top_matches:
            fallback = min(PRODUCTS, key=lambda p: p["base_price"])
            top_matches = [{
                "product_id":       fallback["id"],
                "confidence_score": 0.10,
                "coverage_score":   0.10,
                "specification_scores": {},
                "coverage_details": [],
                "metadata": {
                    "product_id":   fallback["id"],
                    "model":        fallback["name"],
                    "capacity_kg":  fallback["capacity"],
                    "max_floors":   fallback["max_floors"],
                    "speed_ms":     fallback["speed"],
                    "base_price":   fallback["base_price"],
                    "tier":         fallback.get("tier", "Unknown"),
                    "description":  fallback.get("description", ""),
                },
                "match_explanation": "Fallback — cheapest available platform",
                "selection_rationale": "No requirements matched; selected lowest-cost platform as fallback.",
            }]
            self.logger.warning(
                "[ProductMatching] No scored matches — using fallback %s",
                fallback["id"],
            )

        primary = top_matches[0]
        alternatives = top_matches[1:]

        recommendations = {
            "primary_recommendation": {
                "product": primary,
                "reasoning": self._build_primary_reasoning(primary, specifications),
                "key_strengths": self._identify_key_strengths(primary),
            },
            "alternative_options": [
                {
                    "product": alt,
                    "reasoning": (
                        f"Alternative option with {alt['coverage_score']:.0%} "
                        f"requirement coverage"
                    ),
                    "differentiation": self._identify_differentiation(alt, primary),
                }
                for alt in alternatives
            ],
            "case_study_support": [],
        }

        self.logger.info(
            "[ProductMatching] Primary: %s (%s, coverage=%.1f%%)  "
            "Alternatives: %s",
            primary["product_id"],
            primary["metadata"].get("tier", "?"),
            primary["coverage_score"] * 100,
            ", ".join(a["product_id"] for a in alternatives) or "none",
        )

        self.add_reasoning_trace(
            step="recommendation_generation",
            reasoning=(
                f"Primary recommendation: {primary['product_id']} "
                f"({primary['metadata'].get('model', '?')}) with "
                f"{primary['coverage_score']:.0%} requirement coverage.  "
                f"{len(alternatives)} alternative(s) provided."
            ),
            evidence=[{
                "primary": primary["product_id"],
                "primary_coverage": primary["coverage_score"],
                "primary_tier": primary["metadata"].get("tier"),
                "alternatives": [a["product_id"] for a in alternatives],
            }],
            confidence=0.90,
        )

        return recommendations

    # ══════════════════════════════════════════════════════════════════════
    #  EXPLANATION BUILDERS
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _build_match_explanation(
        product: Dict,
        scores: Dict[str, float],
        coverage: float,
        active_weights: List[Tuple[str, float, float]],
    ) -> str:
        """One-line explanation of the match for backward compatibility."""
        parts = []
        for dim_name, _, dim_score in active_weights:
            label = dim_name.replace("_", " ").title()
            parts.append(f"{label}: {dim_score:.0%}")
        parts.append(f"→ Coverage: {coverage:.0%}")
        return " | ".join(parts)

    @staticmethod
    def _build_selection_rationale(
        product: Dict,
        scores: Dict[str, float],
        coverage_details: List[Dict],
        coverage_score: float,
    ) -> str:
        """Multi-line human-readable selection rationale."""
        lines = [
            f"Platform: {product['name']} ({product.get('tier', 'Unknown')} tier)",
            f"Requirement coverage: {coverage_score:.0%}",
            "",
        ]
        satisfied = [d for d in coverage_details if d["status"] in ("satisfied", "available")]
        unsatisfied = [d for d in coverage_details if d["status"] in ("partial", "not_supported", "not_available")]

        if satisfied:
            for d in satisfied:
                lines.append(f"  ✓ {d['requirement']}")
        if unsatisfied:
            for d in unsatisfied:
                status_label = "partial match" if d["status"] == "partial" else "not available"
                lines.append(f"  ✗ {d['requirement']} ({status_label})")

        return "\n".join(lines)

    def _build_primary_reasoning(
        self, product: Dict, specs: Dict,
    ) -> str:
        """Explain why this platform was selected as primary."""
        meta = product["metadata"]
        parts = [
            f"Best platform match with {product['coverage_score']:.0%} "
            f"requirement coverage."
        ]

        tier = meta.get("tier", "")
        if tier:
            parts.append(f"{tier}-tier platform.")

        if specs.get("capacity_kg"):
            cap_range = f"{meta.get('capacity_kg', '?')} kg max"
            if product["specification_scores"].get("capacity", 0) >= 1.0:
                parts.append(f"Capacity requirement satisfied ({cap_range}).")
            else:
                parts.append(
                    f"Closest capacity match ({cap_range} vs "
                    f"{specs['capacity_kg']} kg required)."
                )

        if specs.get("max_floors"):
            if product["specification_scores"].get("floors", 0) >= 1.0:
                parts.append(
                    f"Floor range covers {specs['max_floors']} floors."
                )
            else:
                parts.append(
                    f"Closest floor match ({meta['max_floors']} max vs "
                    f"{specs['max_floors']} required)."
                )

        if specs.get("speed_ms"):
            if product["specification_scores"].get("speed", 0) >= 1.0:
                parts.append(
                    f"Speed requirement met ({specs['speed_ms']} m/s)."
                )

        return " ".join(parts)

    def _identify_key_strengths(self, product: Dict[str, Any]) -> List[str]:
        """Identify key strengths of the matched platform."""

        strengths = []
        spec_scores = product.get("specification_scores", {})

        if spec_scores.get("capacity", 0) >= 1.0:
            strengths.append("Fully meets capacity requirement")
        elif spec_scores.get("capacity", 0) >= 0.8:
            strengths.append(f"Strong capacity match ({spec_scores['capacity']:.0%})")

        if spec_scores.get("floors", 0) >= 1.0:
            strengths.append("Fully meets floor requirement")
        elif spec_scores.get("floors", 0) >= 0.8:
            strengths.append(f"Strong floor match ({spec_scores['floors']:.0%})")

        if spec_scores.get("speed", 0) >= 1.0:
            strengths.append("Fully meets speed requirement")

        if spec_scores.get("building_type", 0) >= 1.0:
            strengths.append("Building type supported")

        if spec_scores.get("lift_type", 0) >= 1.0:
            strengths.append("Lift type supported")

        tier = product.get("metadata", {}).get("tier", "")
        if tier:
            strengths.append(f"{tier}-tier platform")

        if product.get("coverage_score", 0) >= 0.9:
            strengths.append("Excellent overall requirement coverage")
        elif product.get("coverage_score", 0) >= 0.75:
            strengths.append("Good overall requirement coverage")

        if not strengths:
            strengths.append("Best available platform for given specifications")

        return strengths

    def _identify_differentiation(
        self, product: Dict[str, Any], primary: Dict[str, Any],
    ) -> str:
        """Identify how a platform differs from the primary recommendation."""

        meta = product.get("metadata", {})
        primary_meta = primary.get("metadata", {})

        differences = []

        if meta.get("base_price", 0) < primary_meta.get("base_price", 0):
            differences.append("Lower starting price")
        elif meta.get("base_price", 0) > primary_meta.get("base_price", 0):
            differences.append("Premium option")

        if meta.get("speed_ms", 0) > primary_meta.get("speed_ms", 0):
            differences.append("Higher speed capability")

        if meta.get("capacity_kg", 0) > primary_meta.get("capacity_kg", 0):
            differences.append("Higher capacity range")

        if meta.get("max_floors", 0) > primary_meta.get("max_floors", 0):
            differences.append("Greater floor coverage")

        p_tier = meta.get("tier", "")
        r_tier = primary_meta.get("tier", "")
        if p_tier and r_tier and p_tier != r_tier:
            differences.append(f"{p_tier}-tier vs {r_tier}-tier")

        return "; ".join(differences) if differences else "Similar specifications"

    # ══════════════════════════════════════════════════════════════════════
    #  TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def get_tools(self) -> List:
        """Get agent-specific tools."""
        return [
            KnowledgeSearchTool(),
            ProductMatchingTool(),
            HistoricalDataTool(),
        ]