"""
ElevateRFP – FastAPI Application Entry Point
Routes delegate all logic to the Orchestrator agent.
"""

import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from agents import orchestrator
from app.api.v1.agents import router as agents_router

app = FastAPI(title="ElevateRFP", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multi-agent orchestration routes
app.include_router(agents_router)


def _validate_pdf(file: UploadFile):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only PDF files are accepted."
        )


@app.get("/")
def health():
    return {"status": "ok", "service": "ElevateRFP", "version": "3.0"}


@app.post("/process")
async def process_rfp(file: UploadFile = File(...)):
    _validate_pdf(file)
    return orchestrator(file.file)


@app.post("/download")
async def download_proposal(file: UploadFile = File(...)):
    _validate_pdf(file)
    result = orchestrator(file.file)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    content = result["response"].encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ElevateRFP_Proposal.txt"},
    )
