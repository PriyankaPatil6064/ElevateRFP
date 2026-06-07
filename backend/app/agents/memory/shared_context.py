from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
from threading import Lock

@dataclass
class ContextEntry:
    """Single context entry with metadata"""
    key: str
    value: Any
    agent_name: str
    timestamp: datetime
    confidence: float
    sources: List[str] = field(default_factory=list)

class SharedMemoryContext:
    """Shared memory system for inter-agent communication"""
    
    def __init__(self):
        self._context: Dict[str, ContextEntry] = {}
        self._lock = Lock()
        self._history: List[ContextEntry] = []
    
    def set(self, key: str, value: Any, agent_name: str, confidence: float = 1.0, sources: List[str] = None):
        """Set context value with metadata"""
        with self._lock:
            entry = ContextEntry(
                key=key,
                value=value,
                agent_name=agent_name,
                timestamp=datetime.now(),
                confidence=confidence,
                sources=sources or []
            )
            self._context[key] = entry
            self._history.append(entry)
    
    def get(self, key: str) -> Optional[Any]:
        """Get context value"""
        with self._lock:
            entry = self._context.get(key)
            return entry.value if entry else None
    
    def get_entry(self, key: str) -> Optional[ContextEntry]:
        """Get full context entry with metadata"""
        with self._lock:
            return self._context.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all context values"""
        with self._lock:
            return {k: v.value for k, v in self._context.items()}
    
    def get_by_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get all values set by specific agent"""
        with self._lock:
            return {k: v.value for k, v in self._context.items() if v.agent_name == agent_name}
    
    def get_history(self) -> List[ContextEntry]:
        """Get context history"""
        with self._lock:
            return self._history.copy()
    
    def clear(self):
        """Clear all context"""
        with self._lock:
            self._context.clear()
            self._history.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export context to dictionary"""
        with self._lock:
            return {
                "context": {k: {
                    "value": v.value,
                    "agent_name": v.agent_name,
                    "timestamp": v.timestamp.isoformat(),
                    "confidence": v.confidence,
                    "sources": v.sources
                } for k, v in self._context.items()},
                "history_count": len(self._history)
            }

class WorkflowState:
    """Workflow execution state management"""
    
    def __init__(self):
        self.shared_context = SharedMemoryContext()
        self.execution_log: List[Dict[str, Any]] = []
        self.current_step = 0
        self.total_steps = 0
        self.status = "initialized"
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start_workflow(self, total_steps: int):
        """Start workflow execution"""
        self.total_steps = total_steps
        self.start_time = datetime.now()
        self.status = "running"
    
    def complete_step(self, agent_name: str, result: Dict[str, Any]):
        """Mark step as completed"""
        self.current_step += 1
        self.execution_log.append({
            "step": self.current_step,
            "agent": agent_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    def complete_workflow(self):
        """Mark workflow as completed"""
        self.end_time = datetime.now()
        self.status = "completed"
    
    def fail_workflow(self, error: str):
        """Mark workflow as failed"""
        self.end_time = datetime.now()
        self.status = "failed"
        self.execution_log.append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_progress(self) -> float:
        """Get workflow progress percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get workflow execution summary"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "status": self.status,
            "progress": self.get_progress(),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "duration_seconds": duration,
            "execution_log": self.execution_log,
            "context_summary": self.shared_context.to_dict()
        }