from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


# ── Request schemas ──────────────────────────────────────────────────────────

class AgentWorkflowRequest(BaseModel):
    rfp_content: str = Field(..., min_length=50, description="Raw RFP text content")
    rfp_id: Optional[str] = Field(None, description="Optional RFP identifier")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ── Reasoning trace ──────────────────────────────────────────────────────────

class ReasoningTraceSchema(BaseModel):
    agent_name: str
    step: str
    reasoning: str
    confidence: float
    timestamp: str
    sources: List[str] = []


# ── Per-agent result ─────────────────────────────────────────────────────────

class AgentResultSchema(BaseModel):
    agent_name: str
    confidence_score: float
    execution_time: float
    citations: List[str] = []
    reasoning_traces: List[ReasoningTraceSchema] = []


# ── Requirement analysis ─────────────────────────────────────────────────────

class BasicRequirementsSchema(BaseModel):
    capacity_kg: Optional[int] = None
    max_floors: Optional[int] = None
    speed_ms: Optional[float] = None
    keywords: List[str] = []


class RequirementAnalysisSchema(BaseModel):
    basic_requirements: BasicRequirementsSchema
    analysis_metadata: Dict[str, Any] = {}


# ── Product matching ─────────────────────────────────────────────────────────

class ProductMatchSchema(BaseModel):
    product_id: Optional[str] = None
    confidence_score: float = 0.0
    match_explanation: Optional[str] = None
    specification_scores: Dict[str, float] = {}


class ProductMatchingSchema(BaseModel):
    product_matches: List[ProductMatchSchema] = []
    matching_metadata: Dict[str, Any] = {}


# ── Compliance ───────────────────────────────────────────────────────────────

class ComplianceGapSchema(BaseModel):
    framework: str
    severity: str
    description: str


class ComplianceMatrixSchema(BaseModel):
    compliance_status: str
    overall_score: float
    framework_summary: Dict[str, Any] = {}
    gap_summary: Dict[str, int] = {}


class ComplianceResultSchema(BaseModel):
    compliance_matrix: ComplianceMatrixSchema
    compliance_gaps: List[ComplianceGapSchema] = []


# ── Risk assessment ──────────────────────────────────────────────────────────

class RiskItemSchema(BaseModel):
    type: str
    category: str
    description: str
    severity: str
    probability: float
    impact: float


class RiskAnalysisSchema(BaseModel):
    overall_risk_score: float
    risk_level: str
    risk_distribution: Dict[str, int] = {}
    top_risks: List[RiskItemSchema] = []


class RiskAssessmentSchema(BaseModel):
    risk_analysis: RiskAnalysisSchema
    risk_metadata: Dict[str, Any] = {}


# ── Pricing ──────────────────────────────────────────────────────────────────

class PricingComponentsSchema(BaseModel):
    base_product_cost: float = 0.0
    installation_cost: float = 0.0
    customization_cost: float = 0.0
    compliance_cost: float = 0.0
    risk_adjustment: float = 0.0


class PricingBreakdownSchema(BaseModel):
    components: PricingComponentsSchema
    subtotal: float
    tax_amount: float
    total_price: float


class PricingScenarioSchema(BaseModel):
    description: str
    total_price: float
    rationale: str


class PricingResultSchema(BaseModel):
    pricing_breakdown: PricingBreakdownSchema
    pricing_scenarios: Dict[str, PricingScenarioSchema] = {}
    pricing_metadata: Dict[str, Any] = {}


# ── Proposal ─────────────────────────────────────────────────────────────────

class ProposalSectionSchema(BaseModel):
    title: str
    content: str
    word_count: int
    citations: List[str] = []


class ProposalSchema(BaseModel):
    metadata: Dict[str, Any] = {}
    sections: Dict[str, ProposalSectionSchema] = {}
    citations: List[str] = []
    retrieved_evidence_count: int = 0


# ── Evaluation ───────────────────────────────────────────────────────────────

class DimensionScoreSchema(BaseModel):
    score: float
    checks: Optional[Dict[str, Any]] = None


class WinProbabilitySchema(BaseModel):
    probability: float
    percentage: str
    category: str
    factors: Dict[str, float] = {}


class RecommendationSchema(BaseModel):
    dimension: str
    current_score: float
    target_score: float
    priority: str
    action: str
    expected_impact: str


class EvaluationSchema(BaseModel):
    dimension_scores: Dict[str, DimensionScoreSchema] = {}
    weighted_score: float
    grade: str
    win_probability: WinProbabilitySchema
    recommendations: List[RecommendationSchema] = []
    strengths: List[str] = []
    critical_gaps: List[str] = []


# ── Full workflow response ────────────────────────────────────────────────────

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    generated_at: str
    execution_summary: Dict[str, Any] = {}

    requirements: Optional[Dict[str, Any]] = None
    product_matches: Optional[Dict[str, Any]] = None
    compliance_results: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    proposal: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None

    # Convenience top-level fields
    total_price: float = 0.0
    win_probability: str = "N/A"
    proposal_grade: str = "N/A"
    overall_risk_level: str = "unknown"
    compliance_status: str = "unknown"


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    progress: float
    current_step: int
    total_steps: int
    execution_log: List[Dict[str, Any]] = []
