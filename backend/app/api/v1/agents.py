import asyncio
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.agents.workflows.orchestrator import AgentOrchestrator
from app.agents.schemas import AgentWorkflowRequest, WorkflowResponse, WorkflowStatusResponse

router = APIRouter(prefix="/agents", tags=["Multi-Agent Orchestration"])

# In-memory workflow registry (replace with Redis/DB in production)
_workflow_registry: Dict[str, Dict[str, Any]] = {}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", response_model=WorkflowResponse, summary="Run full agent pipeline")
async def run_agent_pipeline(request: AgentWorkflowRequest):
    """
    Execute the complete 7-agent pipeline synchronously.

    Accepts raw RFP text and returns the full proposal with evaluation.
    """
    try:
        orchestrator = AgentOrchestrator()
        result = await orchestrator.run(
            rfp_content=request.rfp_content,
            rfp_id=request.rfp_id
        )
        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(e)}")


@router.post("/run/upload", response_model=WorkflowResponse, summary="Run pipeline from PDF upload")
async def run_pipeline_from_upload(file: UploadFile = File(...)):
    """
    Accept a PDF upload, extract text, and run the full agent pipeline.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Extract text from PDF
        rfp_content = await _extract_pdf_text(file)
        if not rfp_content or len(rfp_content.strip()) < 50:
            raise HTTPException(status_code=422, detail="Could not extract sufficient text from PDF")

        orchestrator = AgentOrchestrator()
        result = await orchestrator.run(rfp_content=rfp_content)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post("/run/async", summary="Start pipeline asynchronously, returns workflow_id")
async def run_pipeline_async(request: AgentWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Start the agent pipeline in the background and return a workflow_id for polling.
    """
    workflow_id = request.rfp_id or str(uuid.uuid4())
    _workflow_registry[workflow_id] = {"status": "queued", "result": None, "error": None}

    background_tasks.add_task(_run_pipeline_background, workflow_id, request.rfp_content)

    return {"workflow_id": workflow_id, "status": "queued", "poll_url": f"/api/v1/agents/status/{workflow_id}"}


@router.get("/status/{workflow_id}", response_model=WorkflowStatusResponse, summary="Poll workflow status")
async def get_workflow_status(workflow_id: str):
    """
    Poll the status of an async workflow.
    """
    entry = _workflow_registry.get(workflow_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    state = entry.get("state")
    if state:
        summary = state.get_execution_summary()
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=summary["status"],
            progress=summary["progress"],
            current_step=summary["current_step"],
            total_steps=summary["total_steps"],
            execution_log=summary["execution_log"]
        )

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        status=entry["status"],
        progress=0.0,
        current_step=0,
        total_steps=7
    )


@router.get("/result/{workflow_id}", response_model=WorkflowResponse, summary="Retrieve async workflow result")
async def get_workflow_result(workflow_id: str):
    """
    Retrieve the completed result of an async workflow.
    """
    entry = _workflow_registry.get(workflow_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    if entry["status"] == "running":
        raise HTTPException(status_code=202, detail="Workflow still running")

    if entry["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Workflow failed: {entry.get('error', 'Unknown error')}")

    if entry["status"] != "completed" or not entry.get("result"):
        raise HTTPException(status_code=404, detail="Result not available yet")

    return JSONResponse(content=entry["result"])


@router.get("/health", summary="Agent system health check")
async def agent_health():
    return {
        "status": "healthy",
        "agents": [step[0] for step in AgentOrchestrator.PIPELINE],
        "active_workflows": len([w for w in _workflow_registry.values() if w["status"] == "running"])
    }


# ── Background task helper ───────────────────────────────────────────────────

async def _run_pipeline_background(workflow_id: str, rfp_content: str):
    """Background task for async pipeline execution"""
    _workflow_registry[workflow_id]["status"] = "running"
    try:
        orchestrator = AgentOrchestrator()
        _workflow_registry[workflow_id]["state"] = orchestrator.state
        result = await orchestrator.run(rfp_content=rfp_content, rfp_id=workflow_id)
        _workflow_registry[workflow_id]["status"] = "completed"
        _workflow_registry[workflow_id]["result"] = result
    except Exception as e:
        _workflow_registry[workflow_id]["status"] = "failed"
        _workflow_registry[workflow_id]["error"] = str(e)


async def _extract_pdf_text(file: UploadFile) -> str:
    """Extract text from uploaded PDF"""
    try:
        import pdfplumber
        import io
        content = await file.read()
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        # Fallback: try PyPDF2
        try:
            import PyPDF2
            import io
            content = await file.read()
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            raise HTTPException(status_code=500, detail="PDF extraction library not available")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {str(e)}")
