import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


def setup_agent_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """Configure a structured JSON logger for an agent"""
    Path(log_dir).mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # File handler — JSON lines
        fh = logging.FileHandler(f"{log_dir}/agents.jsonl", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(JsonFormatter())
        logger.addHandler(fh)

        # Console handler — human-readable
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s — %(message)s", "%H:%M:%S"))
        logger.addHandler(ch)

    return logger


class JsonFormatter(logging.Formatter):
    """Emit log records as JSON lines"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload)


class AgentExecutionLogger:
    """High-level logger for agent workflow events"""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.logger = setup_agent_logger(f"workflow.{workflow_id}")

    def _log(self, level: str, event: str, data: Optional[Dict[str, Any]] = None):
        extra = {"workflow_id": self.workflow_id, "event": event, **(data or {})}
        getattr(self.logger, level)(event, extra={"extra": extra})

    def workflow_started(self, rfp_id: str, total_steps: int):
        self._log("info", "workflow_started", {"rfp_id": rfp_id, "total_steps": total_steps})

    def agent_started(self, agent_name: str, step: int):
        self._log("info", "agent_started", {"agent": agent_name, "step": step})

    def agent_completed(self, agent_name: str, step: int, execution_time: float, confidence: float):
        self._log("info", "agent_completed", {
            "agent": agent_name, "step": step,
            "execution_time_s": round(execution_time, 3),
            "confidence": round(confidence, 3)
        })

    def agent_failed(self, agent_name: str, step: int, error: str):
        self._log("error", "agent_failed", {"agent": agent_name, "step": step, "error": error})

    def agent_retrying(self, agent_name: str, attempt: int, max_attempts: int):
        self._log("warning", "agent_retrying", {
            "agent": agent_name, "attempt": attempt, "max_attempts": max_attempts
        })

    def rag_retrieval(self, agent_name: str, query: str, results_count: int):
        self._log("debug", "rag_retrieval", {
            "agent": agent_name, "query": query[:120], "results": results_count
        })

    def workflow_completed(self, total_time: float, final_score: float):
        self._log("info", "workflow_completed", {
            "total_time_s": round(total_time, 3),
            "final_score": round(final_score, 3)
        })

    def workflow_failed(self, error: str):
        self._log("error", "workflow_failed", {"error": error})
