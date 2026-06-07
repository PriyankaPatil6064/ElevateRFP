from typing import Dict, Any, List
from datetime import datetime
from app.agents.core.base_agent import BaseElevateAgent, AgentResult
from app.agents.tools.rag_tools import KnowledgeSearchTool, HistoricalDataTool
from app.agents.prompts.proposal_templates import ProposalTemplates
from config import PRODUCTS


class ProposalWriterAgent(BaseElevateAgent):
    """Agent for generating professional elevator quotation documents.

    Produces a client-ready quotation in the style of Johnson Lifts,
    Schindler, KONE, and OTIS — not an AI report.

    Generates 13 structured sections:
        1.  Cover Page
        2.  Executive Summary
        3.  Recommended Platform
        4.  Technical Configuration
        5.  Included Features
        6.  Pricing Summary
        7.  Delivery Schedule
        8.  Warranty
        9.  Annual Maintenance Contract
        10. Payment Terms
        11. Engineering Exclusions
        12. Notes & Contact Information
        13. Compliance & Risk (minimal, for internal evaluation)
    """

    def __init__(self):
        super().__init__(
            name="proposal_writer",
            role="Senior Proposal Writer",
            goal="Generate professional, client-ready elevator quotation documents",
            backstory="""You are an expert proposal writer with 20+ years of experience 
            crafting winning elevator industry proposals. You excel at translating technical 
            specifications into persuasive business narratives backed by evidence."""
        )
        self.templates = ProposalTemplates()

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute proposal generation"""
        start_time = datetime.now()

        try:
            requirements    = context.get("requirements", {})
            product_matches = context.get("product_matches", {})
            compliance      = context.get("compliance_results", {})
            risk_assessment = context.get("risk_assessment", {})
            pricing         = context.get("pricing", {})

            if not all([requirements, product_matches, pricing]):
                raise ValueError("Requirements, product matches, and pricing are required")

            # Retrieve supporting knowledge (RAG — zero results is OK)
            supporting_docs = await self._retrieve_supporting_knowledge(requirements, product_matches)

            # ── Extract all data needed across sections ───────────────────
            basic_req      = requirements.get("basic_requirements", {})
            primary_rec    = product_matches.get("recommendations", {}).get("primary_recommendation", {})
            primary_prod   = primary_rec.get("product", {})
            primary_meta   = primary_prod.get("metadata", primary_prod)
            platform       = self._lookup_platform(primary_meta.get("product_id"))
            pricing_data   = pricing.get("pricing_breakdown", {})
            pricing_scenarios = pricing.get("pricing_scenarios", {})
            quotation      = pricing.get("quotation_details", {})
            recommended_sc = pricing_scenarios.get("recommended", {})
            recommended_components = recommended_sc.get("components_breakdown", pricing_data.get("components", {}))

            # ── Generate all 13 sections ──────────────────────────────────
            cover_page             = self._write_cover_page(basic_req)
            executive_summary      = self._write_executive_summary(
                basic_req, primary_meta, platform, pricing_data,
            )
            product_recommendation = self._write_product_recommendation(
                primary_meta, primary_prod, platform,
            )
            technical_solution     = self._write_technical_solution(
                basic_req, platform, pricing_data,
            )
            included_features      = self._write_included_features(
                pricing_data, platform,
            )
            pricing_section        = self._write_pricing_section(
                pricing_data, recommended_components, basic_req, quotation,
            )
            implementation_plan    = self._write_delivery_schedule(quotation, platform)
            warranty               = self._write_warranty(quotation)
            amc                    = self._write_amc(quotation)
            compliance_section     = self._write_compliance_section()
            risk_section           = self._write_risk_section(quotation, platform)
            engineering_exclusions = self._write_engineering_exclusions(quotation)
            conclusion             = self._write_conclusion(quotation)

            proposal = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "version": "3.0",
                    "status": "draft",
                    "sections_count": 13,
                },
                "sections": {
                    # ── Order matches professional quotation flow ──────────
                    "cover_page":             cover_page,
                    "executive_summary":      executive_summary,
                    "product_recommendation": product_recommendation,
                    "technical_solution":     technical_solution,
                    "included_features":      included_features,
                    "pricing":                pricing_section,
                    "implementation_plan":    implementation_plan,
                    "warranty":               warranty,
                    "amc":                    amc,
                    "compliance":             compliance_section,
                    "engineering_exclusions": engineering_exclusions,
                    "conclusion":             conclusion,
                    "risk_management":        risk_section,
                },
                "citations": [d.get("source", "") for d in supporting_docs],
                "retrieved_evidence_count": len(supporting_docs),
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                agent_name=self.name,
                result=proposal,
                reasoning_traces=self.reasoning_traces,
                confidence_score=self._calculate_writing_confidence(),
                execution_time=execution_time,
                retrieved_context=supporting_docs,
                citations=proposal["citations"]
            )

        except Exception as e:
            self.logger.error(f"Proposal writing failed: {e}")
            raise

    # ══════════════════════════════════════════════════════════════════════
    #  PLATFORM LOOKUP
    # ══════════════════════════════════════════════════════════════════════

    def _lookup_platform(self, product_id: str) -> Dict[str, Any]:
        """Look up full platform data from PRODUCTS catalog."""
        for p in PRODUCTS:
            if p["id"] == product_id:
                return p
        # Fallback
        return {
            "id": product_id or "unknown",
            "name": "Elevator Platform",
            "tier": "Mid",
            "description": "Elevator platform",
            "supported_lift_types": ["Passenger", "Traction"],
            "recommended_capacity_range": {"min": 0, "max": 0},
            "recommended_floor_range": {"min": 0, "max": 0},
            "recommended_speed_range": {"min": 0, "max": 0},
            "energy_efficiency_class": "A",
            "recommended_use_cases": [],
            "premium_features_available": [],
        }

    # ══════════════════════════════════════════════════════════════════════
    #  RAG RETRIEVAL
    # ══════════════════════════════════════════════════════════════════════

    async def _retrieve_supporting_knowledge(self, requirements: Dict, product_matches: Dict) -> List[Dict]:
        keywords = requirements.get("basic_requirements", {}).get("keywords", [])
        query = f"elevator proposal case study success {' '.join(keywords[:4])}"
        docs = await self.retrieve_knowledge(query=query, top_k=6)
        self.add_reasoning_trace(
            step="supporting_knowledge_retrieval",
            reasoning=f"Retrieved {len(docs)} supporting documents",
            evidence=[{"query": query, "docs_found": len(docs)}],
            confidence=0.85,
            sources=[d.get("source", "") for d in docs]
        )
        return docs

    # ══════════════════════════════════════════════════════════════════════
    #  SECTION WRITERS
    # ══════════════════════════════════════════════════════════════════════

    def _make_section(self, title: str, content: str, citations: List[str] = None) -> Dict[str, Any]:
        """Build a section dict in the standard format."""
        return {
            "title": title,
            "content": content,
            "word_count": len(content.split()),
            "citations": citations or [],
        }

    # ── 1. Cover Page ────────────────────────────────────────────────────

    def _write_cover_page(self, basic_req: Dict) -> Dict[str, Any]:
        # Extract client/project name from keywords if available
        building_type = basic_req.get("building_type", "")
        project_name = f"{building_type} Elevator Installation Project" if building_type else "Elevator Installation Project"

        now = datetime.now()
        date_str = now.strftime("%d %B %Y")
        ref_id = f"ELV-Q-{now.year}-{now.strftime('%m%d%H%M')}"

        content = self.templates.cover_page(
            client_name="Valued Client",
            project_name=project_name,
            date_str=date_str,
            reference_id=ref_id,
            validity_days=90,
        )

        self.add_reasoning_trace(
            step="cover_page_writing",
            reasoning="Generated cover page with project reference",
            evidence=[{"reference": ref_id}],
            confidence=0.95,
        )
        return self._make_section("Cover Page", content)

    # ── 2. Executive Summary ─────────────────────────────────────────────

    def _write_executive_summary(
        self, basic_req: Dict, primary_meta: Dict, platform: Dict, pricing_data: Dict,
    ) -> Dict[str, Any]:

        total_price = pricing_data.get("total_price", 0)

        content = self.templates.executive_summary(
            model_name=primary_meta.get("model", platform.get("name", "Recommended Model")),
            tier=primary_meta.get("tier", platform.get("tier", "Mid")),
            capacity_kg=basic_req.get("capacity_kg"),
            max_floors=basic_req.get("max_floors"),
            speed_ms=basic_req.get("speed_ms"),
            building_type=basic_req.get("building_type"),
            description=platform.get("description", ""),
            total_price=total_price,
        )

        self.add_reasoning_trace(
            step="executive_summary_writing",
            reasoning="Generated concise executive summary",
            evidence=[{"total_price": total_price}],
            confidence=0.92,
        )
        return self._make_section("Executive Summary", content)

    # ── 3. Recommended Platform ──────────────────────────────────────────

    def _write_product_recommendation(
        self, primary_meta: Dict, primary_prod: Dict, platform: Dict,
    ) -> Dict[str, Any]:

        coverage = primary_prod.get("coverage_score",
                                    primary_prod.get("confidence_score", 0))

        content = self.templates.recommended_platform(
            model_name=primary_meta.get("model", platform.get("name", "N/A")),
            tier=primary_meta.get("tier", platform.get("tier", "N/A")),
            capacity_range=platform.get("recommended_capacity_range", {}),
            floor_range=platform.get("recommended_floor_range", {}),
            speed_range=platform.get("recommended_speed_range", {}),
            coverage_pct=coverage * 100,
            description=platform.get("description", ""),
            use_cases=platform.get("recommended_use_cases", []),
        )

        self.add_reasoning_trace(
            step="product_recommendation_writing",
            reasoning=f"Generated platform recommendation for {primary_meta.get('model', 'N/A')}",
            evidence=[{"coverage": coverage}],
            confidence=0.92,
        )
        return self._make_section("Recommended Platform", content)

    # ── 4. Technical Configuration ───────────────────────────────────────

    def _write_technical_solution(
        self, basic_req: Dict, platform: Dict, pricing_data: Dict,
    ) -> Dict[str, Any]:

        # Get feature lists from pricing breakdown
        add_on_details = pricing_data.get("add_on_details", [])
        mandatory_features = [f for f in add_on_details if f.get("category") == "mandatory"]
        optional_features = [f for f in add_on_details if f.get("category") == "optional"]

        floors = basic_req.get("max_floors") or 10

        content = self.templates.technical_configuration(
            speed_ms=basic_req.get("speed_ms"),
            energy_class=platform.get("energy_efficiency_class", "A"),
            lift_types=platform.get("supported_lift_types", []),
            mandatory_features=mandatory_features,
            optional_features=optional_features,
            building_type=basic_req.get("building_type"),
            floors=floors,
        )

        self.add_reasoning_trace(
            step="technical_solution_writing",
            reasoning=f"Generated technical configuration with {len(mandatory_features)} mandatory + {len(optional_features)} optional features",
            evidence=[{"mandatory": len(mandatory_features), "optional": len(optional_features)}],
            confidence=0.90,
        )
        return self._make_section("Technical Configuration", content)

    # ── 5. Included Features ─────────────────────────────────────────────

    def _write_included_features(
        self, pricing_data: Dict, platform: Dict,
    ) -> Dict[str, Any]:

        # All features included in this scenario
        add_on_details = pricing_data.get("add_on_details", [])
        included_names = [f["type"] for f in add_on_details]

        # Features available on the platform but not included
        all_available = platform.get("premium_features_available", [])
        not_included = [f for f in all_available if f not in included_names]

        content = self.templates.included_features(
            included=included_names,
            available_not_included=not_included,
        )

        self.add_reasoning_trace(
            step="included_features_writing",
            reasoning=f"Listed {len(included_names)} included + {len(not_included)} available features",
            evidence=[{"included": len(included_names), "not_included": len(not_included)}],
            confidence=0.95,
        )
        return self._make_section("Included Features", content)

    # ── 6. Pricing Summary ───────────────────────────────────────────────

    def _write_pricing_section(
        self, pricing_data: Dict, components: Dict, basic_req: Dict, quotation: Dict,
    ) -> Dict[str, Any]:

        floors = basic_req.get("max_floors") or 10

        # Extract component costs
        platform_cost     = components.get("platform_cost", 0)
        installation_cost = components.get("installation_cost", 0)
        logistics_cost    = components.get("logistics_cost", 0)
        feature_cost      = components.get("feature_cost", 0)

        subtotal      = pricing_data.get("subtotal", platform_cost + installation_cost + logistics_cost + feature_cost)
        margin_rate   = pricing_data.get("margin_rate", 0.15)
        margin_amount = pricing_data.get("margin_amount", round(subtotal * margin_rate))
        gst_rate      = pricing_data.get("tax_rate", 0.18)
        gst_amount    = pricing_data.get("tax_amount", round((subtotal + margin_amount) * gst_rate))
        final_price   = pricing_data.get("total_price", subtotal + margin_amount + gst_amount)

        # Installation detail string
        install_rate = pricing_data.get("primary_product_details", {}).get("tier", "")
        installation_detail = f"({floors} floors)"

        content = self.templates.pricing_summary(
            platform_cost=platform_cost,
            installation_cost=installation_cost,
            installation_detail=installation_detail,
            logistics_cost=logistics_cost,
            feature_cost=feature_cost,
            subtotal=subtotal,
            margin_amount=margin_amount,
            margin_rate=margin_rate,
            gst_amount=gst_amount,
            gst_rate=gst_rate,
            final_price=final_price,
        )

        self.add_reasoning_trace(
            step="pricing_section_writing",
            reasoning=f"Generated pricing summary — Total: INR {final_price:,.0f}",
            evidence=[{"total": final_price}],
            confidence=0.95,
        )
        return self._make_section("Pricing Summary", content)

    # ── 7. Delivery Schedule ─────────────────────────────────────────────

    def _write_delivery_schedule(self, quotation: Dict, platform: Dict) -> Dict[str, Any]:

        delivery = quotation.get("delivery_time", "12–16 weeks")
        tier = platform.get("tier", "Mid")

        content = self.templates.delivery_schedule(
            delivery_weeks=delivery,
            tier=tier,
        )

        self.add_reasoning_trace(
            step="implementation_plan_writing",
            reasoning=f"Generated delivery schedule: {delivery}",
            evidence=[{"delivery": delivery, "tier": tier}],
            confidence=0.95,
        )
        return self._make_section("Delivery Schedule", content)

    # ── 8. Warranty ──────────────────────────────────────────────────────

    def _write_warranty(self, quotation: Dict) -> Dict[str, Any]:

        content = self.templates.warranty(
            standard_months=24,
            premium_months=36,
        )

        self.add_reasoning_trace(
            step="warranty_writing",
            reasoning="Generated warranty terms",
            evidence=[{"standard": 24, "premium": 36}],
            confidence=0.98,
        )
        return self._make_section("Warranty", content)

    # ── 9. Annual Maintenance Contract ───────────────────────────────────

    def _write_amc(self, quotation: Dict) -> Dict[str, Any]:

        standard_amc = quotation.get("amc_standard_per_year", 50_000)
        premium_amc  = quotation.get("amc_premium_per_year", 120_000)

        content = self.templates.amc(
            standard_per_year=standard_amc,
            premium_per_year=premium_amc,
        )

        self.add_reasoning_trace(
            step="amc_writing",
            reasoning="Generated AMC terms",
            evidence=[{"standard": standard_amc, "premium": premium_amc}],
            confidence=0.98,
        )
        return self._make_section("Annual Maintenance Contract", content)

    # ── 10. Compliance (minimal — for evaluation agent) ──────────────────

    def _write_compliance_section(self) -> Dict[str, Any]:

        # Payment terms + minimal compliance note
        payment = self.templates.payment_terms()
        compliance = self.templates.compliance_minimal()
        content = payment + "\n\n" + compliance

        self.add_reasoning_trace(
            step="compliance_section_writing",
            reasoning="Generated payment terms with compliance note",
            evidence=[],
            confidence=0.90,
        )
        return self._make_section("Payment Terms", content)

    # ── 11. Risk Management (minimal — for evaluation agent) ─────────────

    def _write_risk_section(self, quotation: Dict, platform: Dict) -> Dict[str, Any]:

        delivery = quotation.get("delivery_time", "12–16 weeks")
        content = self.templates.risk_minimal(delivery_weeks=delivery)

        self.add_reasoning_trace(
            step="risk_section_writing",
            reasoning="Generated minimal risk section for evaluation compatibility",
            evidence=[],
            confidence=0.85,
        )
        return self._make_section("Risk Management", content)

    # ── 12. Engineering Exclusions ───────────────────────────────────────

    def _write_engineering_exclusions(self, quotation: Dict) -> Dict[str, Any]:

        exclusions = quotation.get("engineering_exclusions", [
            "Civil work (shaft walls, plastering, waterproofing)",
            "Shaft construction and scaffolding",
            "Pit construction and waterproofing",
            "Machine room construction (if applicable)",
            "Electrical infrastructure upgrades (transformer, cabling, earthing)",
            "Government approvals, permits and inspections",
            "Building modifications and structural reinforcement",
            "Architectural finishes outside elevator car and landing",
            "Fire NOC and statutory approvals",
        ])

        content = self.templates.engineering_exclusions(exclusions)

        self.add_reasoning_trace(
            step="engineering_exclusions_writing",
            reasoning=f"Listed {len(exclusions)} engineering exclusions",
            evidence=[{"count": len(exclusions)}],
            confidence=0.98,
        )
        return self._make_section("Engineering Exclusions", content)

    # ── 13. Notes & Contact Information ──────────────────────────────────

    def _write_conclusion(self, quotation: Dict) -> Dict[str, Any]:

        validity = quotation.get("validity_days", 90)
        content = self.templates.notes_and_contact(validity_days=validity)

        self.add_reasoning_trace(
            step="conclusion_writing",
            reasoning="Generated notes and contact information",
            evidence=[{"validity_days": validity}],
            confidence=0.95,
        )
        return self._make_section("Notes & Contact Information", content)

    # ══════════════════════════════════════════════════════════════════════
    #  UTILITIES
    # ══════════════════════════════════════════════════════════════════════

    def _calculate_writing_confidence(self) -> float:
        if not self.reasoning_traces:
            return 0.5
        return sum(t.confidence for t in self.reasoning_traces) / len(self.reasoning_traces)

    def get_tools(self) -> List:
        return [KnowledgeSearchTool(), HistoricalDataTool()]
