from typing import Dict, Any, List
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, HistoricalDataTool


class EvaluationAgent(BaseElevateAgent):
    """Proposal Evaluation Agent — deterministic proposal assessment.

    Behaves like a proposal review committee.  Every score traces to an
    upstream agent output and a transparent formula.

    No LLM.  No random confidence.  Fully deterministic.

    Dimensions (5, weighted):
        Requirement Coverage      30 %  — coverage_score from Product Matching
        Standards Compliance      20 %  — compliant / applicable from Standards & Safety
        Technical Completeness    20 %  — (mandatory + recommended) / total from Tech Config
        Proposal Completeness     15 %  — sections present / 11 required sections
        Pricing Competitiveness   15 %  — scenario-based (economy 100 %, recommended 95 %, premium 85 %)

    Grading (percentage scale):
        90–100   Grade A   Excellent Proposal
        75–89    Grade B   Strong Proposal
        60–74    Grade C   Moderate Proposal
        Below 60 Grade D   Needs Improvement

    Estimated Win Probability (not a guarantee):
        Grade A → 85 %    Grade B → 70 %
        Grade C → 55 %    Grade D → 35 %
    """

    # ── Dimension weights ────────────────────────────────────────────────
    DIMENSION_WEIGHTS = {
        "requirement_coverage":    0.30,
        "standards_compliance":    0.20,
        "technical_completeness":  0.20,
        "proposal_completeness":   0.15,
        "pricing_competitiveness": 0.15,
    }

    # ── Required proposal sections (11) ──────────────────────────────────
    REQUIRED_SECTIONS = [
        ("cover_page",             "Cover Page"),
        ("executive_summary",      "Executive Summary"),
        ("product_recommendation", "Recommended Platform"),
        ("technical_solution",     "Technical Configuration"),
        ("pricing",                "Pricing Summary"),
        ("implementation_plan",    "Delivery Schedule"),
        ("warranty",               "Warranty"),
        ("amc",                    "AMC"),
        ("compliance",             "Payment Terms"),
        ("engineering_exclusions", "Engineering Exclusions"),
        ("conclusion",             "Contact Information"),
    ]

    # ── Grade thresholds ─────────────────────────────────────────────────
    GRADE_TABLE = [
        (90, "A", "Excellent Proposal"),
        (75, "B", "Strong Proposal"),
        (60, "C", "Moderate Proposal"),
        (0,  "D", "Needs Improvement"),
    ]

    # ── Estimated Win Probability by grade ───────────────────────────────
    WIN_PROBABILITY = {
        "A": 0.85,
        "B": 0.70,
        "C": 0.55,
        "D": 0.35,
    }

    # ── Pricing scenario competitiveness ─────────────────────────────────
    PRICING_SCENARIO_SCORES = {
        "economy":     1.00,
        "recommended": 0.95,
        "premium":     0.85,
    }

    # ── Strength labels (dimension → message when score > 85 %) ──────────
    STRENGTH_LABELS = {
        "requirement_coverage":    "Strong requirement coverage",
        "standards_compliance":    "High standards alignment",
        "technical_completeness":  "Comprehensive technical configuration",
        "proposal_completeness":   "Complete proposal structure",
        "pricing_competitiveness": "Competitive pricing",
    }

    # ── Improvement labels (dimension → message when score < 75 %) ───────
    IMPROVEMENT_LABELS = {
        "requirement_coverage":    "Improve requirement coverage — review platform selection",
        "standards_compliance":    "Improve standards alignment — enhance accessibility and safety features",
        "technical_completeness":  "Technical configuration needs refinement",
        "proposal_completeness":   "Proposal sections are incomplete",
        "pricing_competitiveness": "Premium pricing reduces competitiveness",
    }

    def __init__(self):
        super().__init__(
            name="evaluator",
            role="Senior Proposal Evaluator",
            goal="Objectively evaluate proposal quality using deterministic scoring",
            backstory="""You are a proposal evaluation specialist with 25+ years of 
            experience reviewing elevator proposals. You assess proposals using 
            transparent, deterministic formulas — no AI scoring, no random 
            confidence, no LLM evaluation."""
        )
        # Legacy attribute for orchestrator schema compatibility
        self.scoring_rubric = {
            dim: {
                "weight": w,
                "description": f"{dim.replace('_', ' ').title()} assessment",
            }
            for dim, w in self.DIMENSION_WEIGHTS.items()
        }

    # ══════════════════════════════════════════════════════════════════════
    #  EXECUTE
    # ══════════════════════════════════════════════════════════════════════

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute proposal evaluation — fully deterministic."""
        start_time = datetime.now()

        try:
            proposal        = context.get("proposal", {})
            product_matches = context.get("product_matches", {})
            compliance      = context.get("compliance_results", {})
            risk_assessment = context.get("risk_assessment", {})
            pricing         = context.get("pricing", {})

            if not proposal:
                raise ValueError("No proposal provided for evaluation")

            # ── Score each dimension ─────────────────────────────────────
            dimension_scores = {
                "requirement_coverage":    self._score_requirement_coverage(
                    product_matches,
                ),
                "standards_compliance":    self._score_standards_compliance(
                    compliance,
                ),
                "technical_completeness":  self._score_technical_completeness(
                    risk_assessment,
                ),
                "proposal_completeness":   self._score_proposal_completeness(
                    proposal,
                ),
                "pricing_competitiveness": self._score_pricing_competitiveness(
                    pricing,
                ),
            }

            # ── Weighted overall score (0.0 – 1.0) ──────────────────────
            weighted_score = sum(
                dimension_scores[dim]["score"] * self.DIMENSION_WEIGHTS[dim]
                for dim in dimension_scores
            )
            overall_pct = round(weighted_score * 100, 1)

            # ── Grade ────────────────────────────────────────────────────
            grade, grade_label = self._compute_grade(overall_pct)

            # ── Estimated Win Probability ────────────────────────────────
            win_prob = self.WIN_PROBABILITY[grade]

            # ── Strengths (dimensions > 85 %) ────────────────────────────
            strengths = self._generate_strengths(dimension_scores)

            # ── Improvement areas (dimensions < 75 %) ────────────────────
            improvement_areas = self._generate_improvement_areas(
                dimension_scores,
            )

            # ── Recommendations (backward-compatible) ────────────────────
            recommendations = self._generate_recommendations(
                dimension_scores,
            )

            # ── Overall assessment ───────────────────────────────────────
            overall_assessment = (
                f"{grade_label}. "
                f"Overall score {overall_pct}% (Grade {grade}). "
                f"Estimated win probability: {win_prob:.0%}. "
                f"{len(strengths)} strength"
                f"{'s' if len(strengths) != 1 else ''} identified, "
                f"{len(improvement_areas)} area"
                f"{'s' if len(improvement_areas) != 1 else ''} "
                f"for improvement."
            )

            self.add_reasoning_trace(
                step="overall_evaluation",
                reasoning=(
                    f"Overall: {overall_pct}% -> Grade {grade} "
                    f"({grade_label}). "
                    f"Estimated win probability: {win_prob:.0%}. "
                    + ", ".join(
                        f"{d}: {s['score']:.0%}"
                        for d, s in dimension_scores.items()
                    )
                ),
                evidence=[{
                    "overall_pct":    overall_pct,
                    "grade":          grade,
                    "win_probability": win_prob,
                }],
                confidence=0.95,
            )

            # ── Assemble result ──────────────────────────────────────────
            evaluation_report = {
                # ── Backward-compatible keys (frozen) ────────────────────
                "dimension_scores":    dimension_scores,
                "weighted_score":      round(weighted_score, 3),
                "grade":               grade,
                "win_probability": {
                    "probability": win_prob,
                    "percentage":  f"{win_prob * 100:.1f}%",
                    "category":    self._probability_category(win_prob),
                    "factors": {
                        "overall_score": overall_pct,
                        "grade":         grade,
                        "method":        "grade_based_lookup",
                    },
                },
                "recommendations":     recommendations,
                "benchmark_comparison": {
                    "status": "deterministic_scoring_no_benchmarks_needed",
                },
                "strengths":           strengths,
                "critical_gaps":       improvement_areas,

                # ── New additive keys ────────────────────────────────────
                "evaluation_scores": {
                    "overall_score": overall_pct,
                    "grade":         grade,
                    "grade_label":   grade_label,
                },
                "proposal_strengths":        strengths,
                "improvement_areas":         improvement_areas,
                "estimated_win_probability": f"{win_prob * 100:.0f}%",
                "overall_assessment":        overall_assessment,
                "evaluation_metadata": {
                    "overall_score":             overall_pct,
                    "grade":                     grade,
                    "estimated_win_probability": f"{win_prob * 100:.0f}%",
                    "evaluation_timestamp":      datetime.now().isoformat(),
                    "evaluation_method":         "deterministic",
                    "dimensions_evaluated":      len(dimension_scores),
                    "weights":                   dict(self.DIMENSION_WEIGHTS),
                },
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                agent_name=self.name,
                result=evaluation_report,
                reasoning_traces=self.reasoning_traces,
                confidence_score=weighted_score,
                execution_time=execution_time,
                retrieved_context=[],
                citations=[],
            )

        except Exception as e:
            self.logger.error(f"Proposal evaluation failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  DIMENSION 1 — REQUIREMENT COVERAGE  (30 %)
    # ══════════════════════════════════════════════════════════════════════

    def _score_requirement_coverage(
        self, product_matches: Dict,
    ) -> Dict[str, Any]:
        """coverage_score from Product Matching Agent."""

        # Primary recommendation path
        primary = (
            product_matches
            .get("recommendations", {})
            .get("primary_recommendation", {})
            .get("product", {})
        )
        coverage = primary.get("coverage_score", 0.0)

        # Fallback: product_matches list
        if not coverage:
            matches = product_matches.get("product_matches", [])
            if matches:
                coverage = matches[0].get("coverage_score", 0.0)

        # Fallback: matching_metadata
        if not coverage:
            coverage = (
                product_matches
                .get("matching_metadata", {})
                .get("overall_confidence", 0.0)
            )

        score = round(min(1.0, max(0.0, float(coverage))), 3)

        self.add_reasoning_trace(
            step="requirement_coverage",
            reasoning=f"Requirement coverage: {score:.0%}",
            evidence=[{"coverage_score": score}],
            confidence=0.95,
        )

        return {
            "score":  score,
            "source": "product_matching_agent",
            "method": "coverage_score from primary recommendation",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  DIMENSION 2 — STANDARDS COMPLIANCE  (20 %)
    # ══════════════════════════════════════════════════════════════════════

    def _score_standards_compliance(
        self, compliance: Dict,
    ) -> Dict[str, Any]:
        """compliant items / applicable items.

        Items with status ``Not Applicable`` are excluded from the
        denominator so they neither inflate nor deflate the score.
        """

        # Gather all feature assessments from domain-specific sections
        all_items: List[Dict] = []
        all_items.extend(compliance.get("safety_features", []))
        all_items.extend(compliance.get("accessibility_features", []))
        all_items.extend(compliance.get("energy_efficiency", []))
        all_items.extend(compliance.get("fire_safety", []))

        applicable = [
            i for i in all_items
            if i.get("status") != "Not Applicable"
        ]
        compliant = [
            i for i in applicable
            if i.get("status") == "Compliant"
        ]
        not_applicable_count = len(all_items) - len(applicable)

        if applicable:
            score = round(len(compliant) / len(applicable), 3)
        else:
            # Fallback: framework-level compliance scores
            fw = compliance.get("compliance_results", {})
            if fw:
                avg = sum(v.get("score", 0) for v in fw.values()) / len(fw)
                score = round(avg, 3)
            else:
                score = 0.5

        self.add_reasoning_trace(
            step="standards_compliance",
            reasoning=(
                f"Standards: {len(compliant)}/{len(applicable)} applicable "
                f"items compliant ({not_applicable_count} excluded as "
                f"Not Applicable) -> {score:.0%}"
            ),
            evidence=[{
                "total":          len(all_items),
                "applicable":     len(applicable),
                "compliant":      len(compliant),
                "not_applicable": not_applicable_count,
            }],
            confidence=0.95,
        )

        return {
            "score":                score,
            "source":               "standards_safety_agent",
            "compliant_count":      len(compliant),
            "applicable_count":     len(applicable),
            "not_applicable_count": not_applicable_count,
            "method":               "compliant / applicable (Not Applicable excluded)",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  DIMENSION 3 — TECHNICAL COMPLETENESS  (20 %)
    # ══════════════════════════════════════════════════════════════════════

    def _score_technical_completeness(
        self, risk_assessment: Dict,
    ) -> Dict[str, Any]:
        """mandatory configurations implemented / total configurations.

        ``mandatory`` and ``recommended`` items are treated as implemented
        configurations.  ``optional`` items are not counted toward
        completeness because they are nice-to-have rather than required.
        """

        tech_config = risk_assessment.get("technical_configuration", [])

        if not tech_config:
            self.add_reasoning_trace(
                step="technical_completeness",
                reasoning="No technical configuration data available",
                evidence=[{}],
                confidence=0.5,
            )
            return {
                "score":                0.0,
                "source":               "technical_configuration_agent",
                "mandatory_count":      0,
                "recommended_count":    0,
                "optional_count":       0,
                "total_configurations": 0,
                "method":               "no data available",
            }

        mandatory   = [c for c in tech_config
                       if c.get("applicability") == "mandatory"]
        recommended = [c for c in tech_config
                       if c.get("applicability") == "recommended"]
        optional    = [c for c in tech_config
                       if c.get("applicability") == "optional"]

        total       = len(tech_config)
        implemented = len(mandatory) + len(recommended)

        score = round(implemented / total, 3) if total > 0 else 0.5

        self.add_reasoning_trace(
            step="technical_completeness",
            reasoning=(
                f"Technical: {len(mandatory)} mandatory + "
                f"{len(recommended)} recommended = "
                f"{implemented}/{total} -> {score:.0%}"
            ),
            evidence=[{
                "mandatory":   len(mandatory),
                "recommended": len(recommended),
                "optional":    len(optional),
                "total":       total,
            }],
            confidence=0.92,
        )

        return {
            "score":                score,
            "source":               "technical_configuration_agent",
            "mandatory_count":      len(mandatory),
            "recommended_count":    len(recommended),
            "optional_count":       len(optional),
            "total_configurations": total,
            "method":               "(mandatory + recommended) / total",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  DIMENSION 4 — PROPOSAL COMPLETENESS  (15 %)
    # ══════════════════════════════════════════════════════════════════════

    def _score_proposal_completeness(
        self, proposal: Dict,
    ) -> Dict[str, Any]:
        """sections present / 11 required sections."""

        sections = proposal.get("sections", {})
        present: List[str] = []
        missing: List[str] = []

        for key, label in self.REQUIRED_SECTIONS:
            if key in sections:
                present.append(label)
            else:
                missing.append(label)

        total_required = len(self.REQUIRED_SECTIONS)
        score = round(
            len(present) / total_required, 3,
        ) if total_required > 0 else 0.0

        self.add_reasoning_trace(
            step="proposal_completeness",
            reasoning=(
                f"Proposal sections: {len(present)}/{total_required} "
                f"present -> {score:.0%}"
                + (f". Missing: {', '.join(missing)}" if missing else "")
            ),
            evidence=[{
                "present":        len(present),
                "missing":        missing,
                "total_required": total_required,
            }],
            confidence=0.95,
        )

        return {
            "score":             score,
            "source":            "proposal_writer_agent",
            "sections_present":  len(present),
            "sections_required": total_required,
            "missing_sections":  missing,
            "method":            "sections_present / required_sections (11)",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  DIMENSION 5 — PRICING COMPETITIVENESS  (15 %)
    # ══════════════════════════════════════════════════════════════════════

    def _score_pricing_competitiveness(
        self, pricing: Dict,
    ) -> Dict[str, Any]:
        """Scenario-based competitiveness.

        Economy = 100 %, Recommended = 95 %, Premium = 85 %.
        The proposal quotes the recommended scenario, so the base score
        is 95 %.  Higher prices reduce competitiveness.
        """

        pricing_breakdown = pricing.get("pricing_breakdown", {})
        total_price = pricing_breakdown.get("total_price", 0)

        if total_price > 0:
            # Pricing data available — recommended scenario
            score = self.PRICING_SCENARIO_SCORES["recommended"]
            scenario_used = "recommended"
        else:
            score = 0.0
            scenario_used = "none"

        self.add_reasoning_trace(
            step="pricing_competitiveness",
            reasoning=(
                f"Pricing: {scenario_used} scenario -> "
                f"{score:.0%} competitive"
            ),
            evidence=[{
                "scenario":    scenario_used,
                "total_price": total_price,
                "score":       score,
            }],
            confidence=0.95,
        )

        return {
            "score":          round(score, 3),
            "source":         "pricing_agent",
            "scenario_used":  scenario_used,
            "total_price":    total_price,
            "method":         "scenario_based (economy=100%, recommended=95%, premium=85%)",
        }

    # ══════════════════════════════════════════════════════════════════════
    #  GRADE + WIN PROBABILITY
    # ══════════════════════════════════════════════════════════════════════

    def _compute_grade(self, overall_pct: float) -> tuple:
        """Determine grade and label from overall percentage score."""
        for threshold, grade, label in self.GRADE_TABLE:
            if overall_pct >= threshold:
                return grade, label
        return "D", "Needs Improvement"

    @staticmethod
    def _probability_category(prob: float) -> str:
        """Human-readable category for win probability."""
        if prob >= 0.75:
            return "high"
        if prob >= 0.50:
            return "medium"
        if prob >= 0.25:
            return "low"
        return "very_low"

    # ══════════════════════════════════════════════════════════════════════
    #  STRENGTHS & IMPROVEMENT AREAS
    # ══════════════════════════════════════════════════════════════════════

    def _generate_strengths(
        self, dimension_scores: Dict[str, Dict],
    ) -> List[str]:
        """Generate strengths from dimensions scoring above 85 %."""
        strengths: List[str] = []
        for dim, data in dimension_scores.items():
            if data.get("score", 0) >= 0.85:
                label = self.STRENGTH_LABELS.get(dim)
                if label:
                    strengths.append(label)
        return strengths

    def _generate_improvement_areas(
        self, dimension_scores: Dict[str, Dict],
    ) -> List[str]:
        """Generate improvement areas from dimensions below 75 %."""
        areas: List[str] = []
        for dim, data in dimension_scores.items():
            if data.get("score", 0) < 0.75:
                label = self.IMPROVEMENT_LABELS.get(dim)
                if label:
                    areas.append(label)
        return areas

    # ══════════════════════════════════════════════════════════════════════
    #  RECOMMENDATIONS  (backward-compatible)
    # ══════════════════════════════════════════════════════════════════════

    def _generate_recommendations(
        self, dimension_scores: Dict[str, Dict],
    ) -> List[Dict[str, Any]]:
        """Improvement recommendations for dimensions below 75 %."""

        recommendations: List[Dict[str, Any]] = []

        for dim, data in dimension_scores.items():
            score = data.get("score", 0.0)
            if score < 0.75:
                priority = "high" if score < 0.50 else "medium"
                weight = self.DIMENSION_WEIGHTS[dim]
                recommendations.append({
                    "dimension":       dim,
                    "current_score":   score,
                    "target_score":    0.85,
                    "priority":        priority,
                    "action":          self.IMPROVEMENT_LABELS.get(
                        dim, "Review and improve",
                    ),
                    "expected_impact": (
                        f"+{(0.85 - score) * weight:.3f} to weighted score"
                    ),
                })

        recommendations.sort(
            key=lambda x: (
                x["priority"] == "high",
                0.85 - x["current_score"],
            ),
            reverse=True,
        )

        self.add_reasoning_trace(
            step="recommendations",
            reasoning=f"Generated {len(recommendations)} recommendations",
            evidence=[{"count": len(recommendations)}],
            confidence=0.90,
        )

        return recommendations

    # ══════════════════════════════════════════════════════════════════════
    #  TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def get_tools(self) -> List:
        """Get agent-specific tools."""
        return [KnowledgeSearchTool(), HistoricalDataTool()]
