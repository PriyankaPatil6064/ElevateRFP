// components/AgentLog.jsx
import { Clock, Link as LinkIcon, CheckCircle } from "lucide-react";

const AGENT_META = {
  requirement_analyst:  { label: "Requirement Analyst",  short: "RA", color: "#2563EB" },
  product_matcher:      { label: "Product Matcher",       short: "PM", color: "#D97706" },
  compliance_validator: { label: "Compliance Validator",  short: "CV", color: "#16A34A" },
  risk_assessor:        { label: "Risk Assessor",         short: "RS", color: "#DC2626" },
  pricing_estimator:    { label: "Pricing Estimator",     short: "PE", color: "#7C3AED" },
  proposal_writer:      { label: "Proposal Writer",       short: "PW", color: "#0891B2" },
  evaluator:            { label: "Evaluator",             short: "EV", color: "#64748B" },
};

const STEP_TO_META_KEY = {
  requirement_analysis:  "requirement_analyst",
  product_matching:      "product_matcher",
  compliance_validation: "compliance_validator",
  risk_assessment:       "risk_assessor",
  pricing_estimation:    "pricing_estimator",
  proposal_writing:      "proposal_writer",
  evaluation:            "evaluator",
};

export default function AgentLog({ result, logs }) {

  // ── New pipeline ─────────────────────────────────────────────────
  if (result && result.workflow_id) {
    const execLog = result.execution_summary?.execution_log || [];

    return (
      <div className="agent-log-timeline">
        <div className="log-summary-bar">
          <span>
            <LinkIcon size={12} />
            Workflow <code>{result.workflow_id?.slice(0, 8)}…</code>
          </span>
          <span>
            <Clock size={12} />
            {result.execution_summary?.duration_seconds?.toFixed(1) || "—"}s total
          </span>
          <span>
            <CheckCircle size={12} />
            {execLog.length} / 7 agents completed
          </span>
        </div>

        {execLog.length > 0 ? (
          execLog.map((entry, i) => {
            const metaKey = STEP_TO_META_KEY[entry.agent] || entry.agent;
            const meta = AGENT_META[metaKey] || { color: "#64748B", short: "AG", label: entry.agent };
            const conf = Math.round((entry.result?.confidence || 0) * 100);

            return (
              <div key={i} className="log-timeline-item">
                <div
                  className="log-avatar"
                  style={{
                    background: meta.color + "18",
                    color: meta.color,
                    border: `1px solid ${meta.color}30`,
                  }}
                >
                  {meta.short}
                </div>
                <div
                  className="log-bubble"
                  style={{ borderLeft: `3px solid ${meta.color}` }}
                >
                  <div className="log-bubble-header">
                    <span className="log-agent-name" style={{ color: meta.color }}>
                      {meta.label}
                    </span>
                    {conf > 0 && (
                      <span
                        className="badge"
                        style={{
                          background: meta.color + "18",
                          color: meta.color,
                        }}
                      >
                        {conf}%
                      </span>
                    )}
                  </div>
                  <span className="log-message">
                    Step {entry.step} completed
                    {entry.result?.execution_time
                      ? ` · ${entry.result.execution_time.toFixed(2)}s`
                      : ""}
                    {entry.result?.citations_count
                      ? ` · ${entry.result.citations_count} citations`
                      : ""}
                  </span>
                </div>
              </div>
            );
          })
        ) : (
          <div className="log-empty">No execution log available</div>
        )}
      </div>
    );
  }

  // ── Legacy pipeline: string array ─────────────────────────────────
  const LEGACY_META = {
    "Sales Agent":      { color: "#2563EB", short: "SA" },
    "Extraction Agent": { color: "#7C3AED", short: "EA" },
    "Matching Agent":   { color: "#D97706", short: "MA" },
    "Pricing Agent":    { color: "#16A34A", short: "PA" },
    "Response Agent":   { color: "#DB2777", short: "RA" },
    "Orchestrator":     { color: "#64748B", short: "OR" },
  };

  function getLegacyMeta(log) {
    for (const [name, meta] of Object.entries(LEGACY_META)) {
      if (log.includes(name)) return { name, ...meta };
    }
    return { name: "System", color: "#64748B", short: "SY" };
  }

  return (
    <div className="agent-log-timeline">
      {(logs || []).map((log, i) => {
        const meta = getLegacyMeta(log);
        return (
          <div key={i} className="log-timeline-item">
            <div
              className="log-avatar"
              style={{
                background: meta.color + "18",
                color: meta.color,
                border: `1px solid ${meta.color}30`,
              }}
            >
              {meta.short}
            </div>
            <div
              className="log-bubble"
              style={{ borderLeft: `3px solid ${meta.color}` }}
            >
              <span className="log-agent-name" style={{ color: meta.color }}>
                {meta.name}
              </span>{" "}
              <span className="log-message">
                {log.replace(/\[.*?\]\s*/, "")}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
