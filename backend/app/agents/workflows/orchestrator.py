import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.agents.memory.shared_context import WorkflowState
from app.agents.core.agent_logger import AgentExecutionLogger
from app.agents.services.requirement_analysis_agent import RequirementAnalysisAgent
from app.agents.services.product_matching_agent import ProductMatchingAgent
from app.agents.services.compliance_validation_agent import ComplianceValidationAgent
from app.agents.services.risk_assessment_agent import RiskAssessmentAgent
from app.agents.services.pricing_estimation_agent import PricingEstimationAgent
from app.agents.services.proposal_writer_agent import ProposalWriterAgent
from app.agents.services.evaluation_agent import EvaluationAgent


MAX_RETRIES = 2
RETRY_DELAY = 2.0  # seconds


class AgentOrchestrator:
    """
    Sequential multi-agent orchestrator for ElevateRFP.

    Pipeline:
        1. RequirementAnalysisAgent
        2. ProductMatchingAgent
        3. ComplianceValidationAgent
        4. RiskAssessmentAgent
        5. PricingEstimationAgent
        6. ProposalWriterAgent
        7. EvaluationAgent
    """

    PIPELINE = [
        ("requirement_analysis", RequirementAnalysisAgent,  "requirements"),
        ("product_matching",     ProductMatchingAgent,       "product_matches"),
        ("compliance_validation",ComplianceValidationAgent,  "compliance_results"),
        ("risk_assessment",      RiskAssessmentAgent,        "risk_assessment"),
        ("pricing_estimation",   PricingEstimationAgent,     "pricing"),
        ("proposal_writing",     ProposalWriterAgent,        "proposal"),
        ("evaluation",           EvaluationAgent,            "evaluation"),
    ]

    def __init__(self):
        self.state  = WorkflowState()

    async def run(self, rfp_content: str, rfp_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the full agent pipeline.

        Args:
            rfp_content: Raw text extracted from the uploaded RFP PDF.
            rfp_id:      Optional identifier for tracking.

        Returns:
            Comprehensive workflow result including proposal and evaluation.
        """
        workflow_id = rfp_id or str(uuid.uuid4())
        exec_log    = AgentExecutionLogger(workflow_id)

        self.state.start_workflow(total_steps=len(self.PIPELINE))
        exec_log.workflow_started(rfp_id=workflow_id, total_steps=len(self.PIPELINE))

        # Seed shared context with the raw RFP
        self.state.shared_context.set("rfp_content", rfp_content, agent_name="orchestrator")

        try:
            for step_idx, (step_name, AgentClass, context_key) in enumerate(self.PIPELINE, start=1):
                exec_log.agent_started(agent_name=step_name, step=step_idx)

                result = await self._run_with_retry(
                    step_name=step_name,
                    AgentClass=AgentClass,
                    exec_log=exec_log,
                    step=step_idx
                )

                # Store result in shared context
                self.state.shared_context.set(
                    key=context_key,
                    value=result.result,
                    agent_name=step_name,
                    confidence=result.confidence_score
                )

                self.state.complete_step(agent_name=step_name, result={
                    "confidence": result.confidence_score,
                    "execution_time": result.execution_time,
                    "citations_count": len(result.citations)
                })

                exec_log.agent_completed(
                    agent_name=step_name,
                    step=step_idx,
                    execution_time=result.execution_time,
                    confidence=result.confidence_score
                )

            self.state.complete_workflow()

            final_result = self._build_final_result(workflow_id)
            total_time   = (self.state.end_time - self.state.start_time).total_seconds()
            final_score  = final_result.get("evaluation", {}).get("weighted_score", 0.0)

            exec_log.workflow_completed(total_time=total_time, final_score=final_score)
            return final_result

        except Exception as e:
            self.state.fail_workflow(str(e))
            exec_log.workflow_failed(str(e))
            raise

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _run_with_retry(self, step_name: str, AgentClass, exec_log: AgentExecutionLogger, step: int):
        """Execute an agent with retry logic"""
        context = self.state.shared_context.get_all()

        for attempt in range(1, MAX_RETRIES + 2):  # +2 so range covers MAX_RETRIES retries
            try:
                agent  = AgentClass()
                result = await agent.execute(context)
                return result

            except Exception as e:
                if attempt <= MAX_RETRIES:
                    exec_log.agent_retrying(agent_name=step_name, attempt=attempt, max_attempts=MAX_RETRIES + 1)
                    await asyncio.sleep(RETRY_DELAY * attempt)
                else:
                    exec_log.agent_failed(agent_name=step_name, step=step, error=str(e))
                    raise RuntimeError(f"Agent '{step_name}' failed after {MAX_RETRIES + 1} attempts: {e}") from e

    def _build_final_result(self, workflow_id: str) -> Dict[str, Any]:
        """Assemble the final output from shared context"""
        ctx = self.state.shared_context.get_all()

        # Strip context_summary — contains non-serializable nested objects
        summary = self.state.get_execution_summary()
        summary.pop("context_summary", None)

        raw = {
            "workflow_id":        workflow_id,
            "status":             self.state.status,
            "generated_at":       datetime.now().isoformat(),
            "execution_summary":  summary,
            "requirements":       ctx.get("requirements", {}),
            "product_matches":    ctx.get("product_matches", {}),
            "compliance_results": ctx.get("compliance_results", {}),
            "risk_assessment":    ctx.get("risk_assessment", {}),
            "pricing":            ctx.get("pricing", {}),
            "proposal":           ctx.get("proposal", {}),
            "evaluation":         ctx.get("evaluation", {}),
            "total_price":        ctx.get("pricing", {}).get("pricing_breakdown", {}).get("total_price", 0),
            "win_probability":    ctx.get("evaluation", {}).get("win_probability", {}).get("percentage", "N/A"),
            "proposal_grade":     ctx.get("evaluation", {}).get("grade", "N/A"),
            "overall_risk_level": ctx.get("risk_assessment", {}).get("risk_analysis", {}).get("risk_level", "unknown"),
            "compliance_status":  ctx.get("compliance_results", {}).get("compliance_matrix", {}).get("compliance_status", "unknown"),
        }
        return self._make_serializable(raw)

    def _make_serializable(self, obj: Any) -> Any:
        """Recursively convert non-JSON-serializable objects to primitives"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dataclass_fields__"):   # any dataclass
            from dataclasses import asdict
            return self._make_serializable(asdict(obj))
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(i) for i in obj]
        return obj
