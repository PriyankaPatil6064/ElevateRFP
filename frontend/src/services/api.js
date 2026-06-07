// services/api.js — centralised API calls

const BASE = "http://localhost:8000";

// ── New 7-agent pipeline ──────────────────────────────────────────────────

/**
 * Upload a PDF and run the full 7-agent pipeline asynchronously.
 * Calls onProgress(step 0-7, statusText) while polling.
 * Resolves with the final WorkflowResponse.
 */
export async function runAgentPipeline(file, onProgress) {
  const form = new FormData();
  form.append("file", file);

  // 1. Start async job
  const startRes = await fetch(`${BASE}/api/v1/agents/run/upload`, {
    method: "POST",
    body: form,
  });

  if (!startRes.ok) {
    const err = await startRes.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start agent pipeline");
  }

  // The upload endpoint runs synchronously and returns the full result directly
  const result = await startRes.json();
  if (result.workflow_id) {
    onProgress && onProgress(7, "Completed");
    return result;
  }
  throw new Error("Unexpected response from agent pipeline");
}

/**
 * Run pipeline with text content directly (no file upload).
 */
export async function runAgentPipelineText(rfpContent, onProgress) {
  onProgress && onProgress(0, "Starting pipeline…");

  const res = await fetch(`${BASE}/api/v1/agents/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rfp_content: rfpContent }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Agent pipeline failed");
  }

  const result = await res.json();
  onProgress && onProgress(7, "Completed");
  return result;
}

/**
 * Poll workflow status until completed or failed.
 * onProgress(currentStep, statusText) called on each poll.
 */
export async function pollWorkflow(workflowId, onProgress, intervalMs = 2000) {
  const STEP_LABELS = [
    "Analyzing requirements…",
    "Matching products…",
    "Validating compliance…",
    "Assessing risks…",
    "Estimating pricing…",
    "Writing proposal…",
    "Evaluating proposal…",
    "Completed",
  ];

  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${BASE}/api/v1/agents/status/${workflowId}`);
        if (!res.ok) { clearInterval(timer); reject(new Error("Status check failed")); return; }

        const status = await res.json();
        const step = Math.min(status.current_step || 0, 7);
        onProgress && onProgress(step, STEP_LABELS[step] || "Processing…");

        if (status.status === "completed") {
          clearInterval(timer);
          const resultRes = await fetch(`${BASE}/api/v1/agents/result/${workflowId}`);
          if (!resultRes.ok) { reject(new Error("Failed to fetch result")); return; }
          resolve(await resultRes.json());
        } else if (status.status === "failed") {
          clearInterval(timer);
          reject(new Error("Workflow failed on the server"));
        }
      } catch (e) {
        clearInterval(timer);
        reject(e);
      }
    }, intervalMs);
  });
}

// ── Legacy endpoints (kept for backward compatibility) ────────────────────

export async function processRFP(file) {
  const form = new FormData();
  form.append("file", file);
  const res  = await fetch(`${BASE}/process`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Server error.");
  if (data.error) throw new Error(data.error);
  return data;
}

export async function downloadProposal(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/download`, { method: "POST", body: form });
  if (!res.ok) {
    const d = await res.json();
    throw new Error(d.detail || "Download failed.");
  }
  return res.blob();
}

// ── Agent health check ────────────────────────────────────────────────────

export async function checkAgentHealth() {
  const res = await fetch(`${BASE}/api/v1/agents/health`);
  if (!res.ok) throw new Error("Agent system unavailable");
  return res.json();
}
