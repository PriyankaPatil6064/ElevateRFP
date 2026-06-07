// components/ResultTabs.jsx
import { useState } from "react";
import {
  FileText, Package, ShieldCheck, AlertTriangle, DollarSign,
  BookOpen, BarChart3, Terminal, Check, CheckCircle2, Clock,
  Download, ChevronRight, TrendingUp
} from "lucide-react";
import AgentLog from "./AgentLog";

// ── Shared helpers ────────────────────────────────────────────────

function downloadText(content, filename) {
  const blob = new Blob([content], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function ProgressBar({ pct, cls }) {
  return (
    <div className="progress-bar-wrap">
      <div className={`progress-bar-fill progress-${cls}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function scoreClass(pct) {
  if (pct >= 75) return "high";
  if (pct >= 50) return "medium";
  return "low";
}

// ── TAB: Requirements ─────────────────────────────────────────────

function RequirementsTab({ data }) {
  const basic    = data?.basic_requirements  || {};
  const summary  = data?.structured_summary  || {};
  const meta     = data?.analysis_metadata   || {};
  const funcReqs = summary.functional_requirements?.requirements || [];
  const critical = summary.critical_requirements || [];
  const confPct  = Math.round((meta.confidence_score || 0) * 100);

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag">
          <FileText size={10} /> Requirement Analysis Agent
        </div>
        <div className="tab-header-row">
          <h3 className="tab-title">Extracted Requirements</h3>
        </div>
        <p className="tab-meta">
          {meta.total_requirements || 0} total · {meta.mandatory_count || 0} mandatory · {meta.optional_count || 0} optional
        </p>
      </div>

      {/* Key specs */}
      <div className="spec-cards-row">
        {[
          { label: "Number of Floors", value: basic.max_floors,  unit: "floors", cls: "blue" },
          { label: "Load Capacity",    value: basic.capacity_kg, unit: "kg",     cls: "purple" },
          { label: "Elevator Speed",   value: basic.speed_ms,    unit: "m/s",    cls: "green" },
        ].map(s => (
          <div key={s.label} className={`spec-card ${s.value != null ? "found" : "missing"}`}>
            <div className={`spec-icon ${s.cls}`}>
              <TrendingUp size={14} />
            </div>
            <div className="spec-label">{s.label}</div>
            {s.value != null ? (
              <div className="spec-value">
                {s.value}<span className="spec-unit">{s.unit}</span>
              </div>
            ) : (
              <div className="spec-missing">Not specified</div>
            )}
          </div>
        ))}
      </div>

      {/* Confidence */}
      <div className="match-bar-wrap mb-4">
        <div className="match-bar-header">
          <span>Extraction Confidence</span>
          <span className="match-pct">{confPct}%</span>
        </div>
        <ProgressBar pct={confPct} cls={confPct >= 75 ? "blue" : confPct >= 50 ? "amber" : "red"} />
      </div>

      {/* Keywords */}
      {basic.keywords?.length > 0 && (
        <div className="mb-5">
          <div className="req-section-title">Detected Keywords</div>
          <div className="keywords-row">
            {basic.keywords.map(k => <span key={k} className="keyword-chip">{k}</span>)}
          </div>
        </div>
      )}

      {/* Functional */}
      {funcReqs.length > 0 && (
        <div className="req-section">
          <div className="req-section-title">
            Functional Requirements
            <span className="badge badge-blue">{funcReqs.length}</span>
          </div>
          <ul className="req-list">
            {funcReqs.slice(0, 8).map((r, i) => <li key={i}>{r}</li>)}
            {funcReqs.length > 8 && (
              <li style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                …and {funcReqs.length - 8} more
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Critical */}
      {critical.length > 0 && (
        <div className="req-section mt-4">
          <div className="req-section-title">
            Critical Requirements
            <span className="badge badge-red">{critical.length}</span>
          </div>
          <ul className="req-list req-list-critical">
            {critical.slice(0, 5).map((r, i) => <li key={i}>{r.requirement || r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── TAB: Product ──────────────────────────────────────────────────

function ProductTab({ data }) {
  const matches = data?.product_matches || [];
  const recs    = data?.recommendations || {};
  const primary = recs.primary_recommendation || {};
  const alts    = recs.alternative_options    || [];
  const meta    = data?.matching_metadata     || {};
  const product = primary.product?.metadata   || primary.product || {};
  const confPct = Math.round((meta.overall_confidence || 0) * 100);

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag">
          <Package size={10} /> Product Matching Agent
        </div>
        <div className="tab-header-row">
          <h3 className="tab-title">Recommended Product</h3>
        </div>
        <p className="tab-meta">
          {meta.total_products_evaluated || matches.length} products evaluated · {meta.high_confidence_matches || 0} high-confidence matches
        </p>
      </div>

      {/* Hero card */}
      <div className="product-hero mb-4">
        <div className="product-hero-header">
          <div>
            {product.product_id && (
              <div className="product-id-tag">{product.product_id}</div>
            )}
            <div className="product-hero-name">{product.model || "Recommended Model"}</div>
          </div>
          <div className="product-hero-badge">AI Selected</div>
        </div>

        <div className="product-hero-body">
          {/* Specs grid */}
          <div className="product-specs-grid mb-4">
            {[
              { label: "Max Capacity", value: product.capacity_kg, unit: "kg" },
              { label: "Max Floors",   value: product.max_floors,  unit: "floors" },
              { label: "Speed",        value: product.speed_ms,    unit: "m/s" },
              { label: "Base Price",   value: product.base_price   ? `$${Number(product.base_price).toLocaleString()}` : null, unit: "" },
            ].map(s => (
              <div key={s.label} className="product-spec-cell">
                <div className="product-spec-label">{s.label}</div>
                {s.value != null ? (
                  <div className="product-spec-value">
                    {s.value}
                    {s.unit && <span className="product-spec-unit"> {s.unit}</span>}
                  </div>
                ) : (
                  <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>—</div>
                )}
              </div>
            ))}
          </div>

          {/* Confidence */}
          <div className="match-bar-wrap mb-4">
            <div className="match-bar-header">
              <span>Match Confidence</span>
              <span className="match-pct">{confPct}%</span>
            </div>
            <ProgressBar pct={confPct} cls={confPct >= 75 ? "blue" : confPct >= 50 ? "amber" : "red"} />
          </div>

          {/* Rationale */}
          <div className="selection-rationale">
            <div className="selection-rationale-title">Selection Rationale</div>
            <p className="selection-rationale-text">
              {primary.reasoning || "Best overall semantic match for your requirements."}
            </p>
            {primary.key_strengths?.length > 0 && (
              <ul className="strengths-list">
                {primary.key_strengths.map((s, i) => (
                  <li key={i}><CheckCircle2 size={13} /> {s}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Alternatives */}
      {alts.length > 0 && (
        <div className="alternatives-section">
          <div className="alternatives-title">Alternative Options</div>
          <div className="alt-list">
            {alts.map((alt, i) => {
              const p = alt.product?.metadata || alt.product || {};
              return (
                <div key={i} className="alt-item">
                  <span className="alt-rank">#{i + 2}</span>
                  <span className="alt-id">{p.product_id || `Option ${i + 2}`}</span>
                  <span className="alt-meta">{p.model || ""}{alt.differentiation ? ` · ${alt.differentiation}` : ""}</span>
                  <span className="alt-score">{Math.round((alt.product?.confidence_score || 0) * 100)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── TAB: Compliance ───────────────────────────────────────────────

function ComplianceTab({ data }) {
  const matrix     = data?.compliance_matrix || {};
  const gaps       = data?.compliance_gaps   || [];
  const plan       = data?.remediation_plan  || {};
  const frameworks = matrix.framework_summary || {};
  const overall    = matrix.compliance_status || "unknown";
  const score      = matrix.overall_score     || 0;
  const scorePct   = Math.round(score * 100);

  const barCls = {
    compliant:            "compliance-bar-success",
    partially_compliant:  "compliance-bar-warning",
    non_compliant:        "compliance-bar-danger",
  }[overall] || "compliance-bar-default";

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag">
          <ShieldCheck size={10} /> Standards & Safety Agent
        </div>
        <div className="tab-header-row">
          <h3 className="tab-title">Compliance & Standards</h3>
        </div>
        <p className="tab-meta">
          {Object.keys(frameworks).length} frameworks evaluated · {gaps.length} gaps identified
        </p>
      </div>

      {/* Status banner */}
      <div className={`compliance-status-bar ${barCls} mb-5`}>
        <span className="compliance-bar-label">{overall.replace(/_/g, " ").toUpperCase()}</span>
        <span className="compliance-bar-score">Overall Score: {scorePct}%</span>
      </div>

      {/* Framework matrix */}
      <div className="standards-grid mb-5">
        {Object.entries(frameworks).map(([fw, info]) => {
          const fwPct = Math.round((info.score || 0) * 100);
          const fwCls = {
            compliant:           "success",
            partially_compliant: "warning",
            non_compliant:       "danger",
          }[info.status] || "";
          return (
            <div key={fw} className={`standard-card ${fwCls}`}>
              <div className="standard-name">{fw}</div>
              <div className="standard-score">{fwPct}%</div>
              <span className={`badge ${fwCls === "success" ? "badge-green" : fwCls === "warning" ? "badge-amber" : "badge-red"}`}>
                {(info.status || "unknown").replace(/_/g, " ")}
              </span>
            </div>
          );
        })}
      </div>

      {/* Gaps */}
      {gaps.length > 0 && (
        <div className="gaps-section mb-4">
          <div className="gaps-title">
            Identified Gaps
            <span className="badge badge-red">{gaps.length}</span>
          </div>
          {gaps.slice(0, 6).map((gap, i) => (
            <div key={i} className={`gap-item ${gap.severity}`}>
              <span className={`gap-sev ${gap.severity}`}>{gap.severity?.toUpperCase()}</span>
              <span className="gap-fw">{gap.framework}</span>
              <span className="gap-desc">{gap.description}</span>
            </div>
          ))}
        </div>
      )}

      {/* Remediation */}
      {plan.estimated_timeline && (
        <div className="remediation-box">
          <div className="remediation-title">Remediation Plan</div>
          <div className="remediation-timeline">
            <Clock size={13} /> {plan.estimated_timeline}
          </div>
          <div className="remediation-counts">
            <span>{plan.immediate_actions?.length || 0} immediate actions</span>
            <span>{plan.short_term_actions?.length  || 0} short-term actions</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── TAB: Risk ─────────────────────────────────────────────────────

function RiskTab({ data }) {
  const analysis    = data?.risk_analysis          || {};
  const mitigation  = data?.mitigation_strategies  || {};
  const topRisks    = analysis.top_risks            || [];
  const dist        = analysis.risk_distribution    || {};
  const level       = analysis.risk_level           || "unknown";
  const score       = analysis.overall_risk_score   || 0;

  const barCls = { low: "risk-bar-success", medium: "risk-bar-warning", high: "risk-bar-danger", critical: "risk-bar-danger" }[level] || "risk-bar-default";

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag">
          <AlertTriangle size={10} /> Risk Assessment Agent
        </div>
        <div className="tab-header-row">
          <h3 className="tab-title">Risk Assessment</h3>
        </div>
        <p className="tab-meta">
          {analysis.identified_risks?.length || 0} risks identified · overall score {(score * 100).toFixed(0)}/100
        </p>
      </div>

      <div className={`risk-status-bar ${barCls} mb-5`}>
        <span className="risk-bar-level">
          <AlertTriangle size={14} />
          {level.toUpperCase()} RISK
        </span>
        <span className="risk-bar-score">Score: {(score * 100).toFixed(1)}</span>
      </div>

      {/* Distribution */}
      <div className="risk-dist-row mb-5">
        {Object.entries(dist).map(([sev, count]) => count > 0 && (
          <div key={sev} className={`risk-dist-pill ${sev}`}>
            <span className="risk-dist-count">{count}</span>
            <span className="risk-dist-label">{sev}</span>
          </div>
        ))}
      </div>

      {/* Top risks */}
      {topRisks.length > 0 && (
        <div className="mb-5">
          <div className="req-section-title mb-3">Top Identified Risks</div>
          {topRisks.map((risk, i) => (
            <div key={i} className={`risk-item ${risk.severity}`}>
              <div className="risk-item-header">
                <span className={`risk-sev-tag ${risk.severity}`}>{risk.severity?.toUpperCase()}</span>
                <span className="risk-category">{risk.category}</span>
                <span className="risk-prob">
                  P={Math.round((risk.probability || 0) * 100)}% · I={Math.round((risk.impact || 0) * 100)}%
                </span>
              </div>
              <p className="risk-desc">{risk.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Mitigation summary */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Mitigation Strategy Summary</span>
        </div>
        <div className="card-body">
          <div className="mitigation-grid">
            {[
              { count: mitigation.immediate_actions?.length    || 0, label: "Immediate Actions" },
              { count: mitigation.preventive_measures?.length  || 0, label: "Preventive Measures" },
              { count: mitigation.contingency_plans?.length    || 0, label: "Contingency Plans" },
              { count: mitigation.monitoring_requirements?.length || 0, label: "Monitoring Items" },
            ].map(m => (
              <div key={m.label} className="mit-cell">
                <span className="mit-count">{m.count}</span>
                <span className="mit-label">{m.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── TAB: Pricing ─────────────────────────────────────────────────

function PricingTab({ data }) {
  const breakdown  = data?.pricing_breakdown  || {};
  const scenarios  = data?.pricing_scenarios  || {};
  const meta       = data?.pricing_metadata   || {};
  const components = breakdown.components     || {};

  const COMPONENT_LABELS = {
    base_product_cost:  "Base Product Cost",
    installation_cost:  "Installation",
    customization_cost: "Customization",
    compliance_cost:    "Compliance & Certification",
    risk_adjustment:    "Risk Adjustment",
  };

  const scenarioOrder = ["pessimistic", "most_likely", "optimistic"];
  const scenarioEntries = scenarioOrder
    .filter(k => scenarios[k])
    .map(k => [k, scenarios[k]]);

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag">
          <DollarSign size={10} /> Pricing Estimation Agent
        </div>
        <div className="tab-header-row">
          <h3 className="tab-title">Pricing & Investment</h3>
        </div>
        <p className="tab-meta">
          Confidence: {Math.round((meta.confidence_level || 0) * 100)}% · Position: {(meta.competitive_position || "unknown").replace(/_/g, " ")}
        </p>
      </div>

      {/* Cost breakdown table */}
      <div className="pricing-breakdown-table mb-5">
        <table>
          <tbody>
            {Object.entries(components).map(([key, val]) => (
              <tr key={key}>
                <td>{COMPONENT_LABELS[key] || key.replace(/_/g, " ")}</td>
                <td>${Number(val || 0).toLocaleString()}</td>
              </tr>
            ))}
            <tr>
              <td>Tax (8%)</td>
              <td>${Number(breakdown.tax_amount || 0).toLocaleString()}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td><strong>Total Investment</strong></td>
              <td><strong>${Number(breakdown.total_price || 0).toLocaleString()}</strong></td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* 3-column scenario comparison */}
      {scenarioEntries.length > 0 && (
        <div className="mb-5">
          <div className="scenarios-label">Pricing Scenarios</div>
          <div className="pricing-scenarios-grid">
            {scenarioEntries.map(([name, s]) => {
              const isRec = name === "most_likely";
              return (
                <div key={name} className={`scenario-card ${isRec ? "recommended" : ""}`}>
                  <div className="scenario-header">
                    <span className="scenario-name">
                      {name === "most_likely" ? "Recommended" : name.charAt(0).toUpperCase() + name.slice(1)}
                    </span>
                    {isRec && <span className="scenario-rec-badge">Recommended</span>}
                  </div>
                  <div className="scenario-body">
                    <div className="scenario-price">${Number(s.total_price || 0).toLocaleString()}</div>
                    <div className="scenario-rationale">{s.rationale}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Pricing risks */}
      {meta.pricing_risks?.length > 0 && (
        <div className="pricing-risks-row">
          {meta.pricing_risks.map((r, i) => (
            <div key={i} className="pricing-risk-item">
              <AlertTriangle size={12} /> {r}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── TAB: Proposal ────────────────────────────────────────────────

function ProposalTab({ data }) {
  const sections   = data?.sections  || {};
  const citations  = data?.citations || [];
  const sectionKeys = Object.keys(sections);
  const [active, setActive] = useState(sectionKeys[0] || "");

  function handleDownload() {
    const text = Object.values(sections)
      .map(s => `${"=".repeat(60)}\n${s.title?.toUpperCase()}\n${"=".repeat(60)}\n\n${s.content}`)
      .join("\n\n");
    downloadText(text, "ElevateRFP_Proposal.txt");
  }

  if (sectionKeys.length === 0) {
    return (
      <div>
        <div className="tab-header">
          <div className="tab-agent-tag"><BookOpen size={10} /> Proposal Writer Agent</div>
          <h3 className="tab-title">Generated Proposal</h3>
        </div>
        <div style={{ color: "var(--text-muted)", fontStyle: "italic", padding: "40px", textAlign: "center" }}>
          No proposal sections generated.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag"><BookOpen size={10} /> Proposal Writer Agent</div>
        <div className="tab-header-row">
          <h3 className="tab-title">Generated Proposal</h3>
        </div>
        <p className="tab-meta">
          {sectionKeys.length} sections · {citations.length} citations · {data?.retrieved_evidence_count || 0} knowledge sources
        </p>
      </div>

      <div className="proposal-viewer">
        {/* Section nav */}
        <div className="proposal-nav">
          <div className="proposal-nav-title">Sections</div>
          {sectionKeys.map(key => (
            <button
              key={key}
              className={`proposal-nav-btn ${active === key ? "active" : ""}`}
              onClick={() => setActive(key)}
            >
              <ChevronRight size={12} />
              {sections[key].title}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="proposal-content">
          {active && sections[active] && (
            <>
              <div className="proposal-content-header">
                <div>
                  <div className="proposal-content-title">{sections[active].title}</div>
                  <div className="proposal-content-meta">
                    {sections[active].word_count} words
                    {sections[active].citations?.length > 0 && ` · ${sections[active].citations.length} citations`}
                  </div>
                </div>
              </div>
              <div className="proposal-content-body">
                <pre className="proposal-text">{sections[active].content}</pre>
              </div>
            </>
          )}
          <div className="proposal-actions">
            <button className="btn btn-outline btn-sm" onClick={handleDownload}>
              <Download size={13} />
              Download Proposal
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── TAB: Evaluation ──────────────────────────────────────────────

function EvaluationTab({ data }) {
  const scores    = data?.dimension_scores  || {};
  const winProb   = data?.win_probability   || {};
  const recs      = data?.recommendations   || [];
  const strengths = data?.strengths         || [];
  const gaps      = data?.critical_gaps     || [];
  const grade     = data?.grade             || "N/A";
  const weighted  = data?.weighted_score    || 0;

  // Updated dimension labels for the new 5-dimension schema
  const DIM_LABELS = {
    requirement_coverage:    "Requirement Coverage",
    standards_compliance:    "Standards Compliance",
    technical_completeness:  "Technical Completeness",
    proposal_completeness:   "Proposal Completeness",
    pricing_competitiveness: "Pricing Competitiveness",
    // Legacy fallbacks
    completeness:            "Completeness",
    technical_accuracy:      "Technical Accuracy",
    compliance_coverage:     "Compliance Coverage",
    pricing_clarity:         "Pricing Clarity",
    risk_management:         "Risk Management",
    writing_quality:         "Writing Quality",
  };

  const probPct = winProb.percentage
    ? parseInt(winProb.percentage)
    : Math.round((winProb.probability || 0) * 100);

  const probCls = probPct >= 70 ? "high" : probPct >= 50 ? "medium" : "low";

  return (
    <div>
      <div className="tab-header">
        <div className="tab-agent-tag"><BarChart3 size={10} /> Evaluation Agent</div>
        <div className="tab-header-row">
          <h3 className="tab-title">Proposal Evaluation</h3>
        </div>
        <p className="tab-meta">Deterministic scoring — no AI randomness</p>
      </div>

      {/* Hero row: grade, win prob, summary */}
      <div className="eval-hero-row mb-6">
        <div className="eval-metric-card">
          <div className="eval-metric-label">Proposal Grade</div>
          <div className={`eval-grade ${grade}`}>{grade}</div>
          <div className="eval-weighted">{Math.round(weighted)}% weighted score</div>
        </div>

        <div className="eval-metric-card">
          <div className="eval-metric-label">Estimated Win Probability</div>
          <div className={`eval-win-pct ${probCls}`}>
            {winProb.percentage || `${probPct}%`}
          </div>
          <div className="eval-win-category">{winProb.category || ""}</div>
        </div>

        <div className="eval-metric-card">
          <div className="eval-metric-label">Summary</div>
          <div className="eval-summary-rows">
            <div className="eval-summary-row">
              <span>Strengths</span>
              <strong style={{ color: "var(--success)" }}>{strengths.length}</strong>
            </div>
            <div className="eval-summary-row">
              <span>Critical Gaps</span>
              <strong style={{ color: "var(--danger)" }}>{gaps.length}</strong>
            </div>
            <div className="eval-summary-row">
              <span>Recommendations</span>
              <strong>{recs.length}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Dimension scores */}
      {Object.keys(scores).length > 0 && (
        <div className="dim-scores-section mb-5">
          <div className="dim-scores-title">Dimension Scores</div>
          {Object.entries(scores).map(([dim, info]) => {
            const pct = Math.round((info.score || 0) * 100);
            const cls = scoreClass(pct);
            return (
              <div key={dim} className="dim-row">
                <span className="dim-label">{DIM_LABELS[dim] || dim.replace(/_/g, " ")}</span>
                <div className="dim-bar-wrap">
                  <div className="dim-bar">
                    <div className={`dim-fill ${cls}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
                <span className={`dim-pct ${cls}`}>{pct}%</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Recommendations */}
      {recs.length > 0 && (
        <div className="mb-5">
          <div className="dim-scores-title">Improvement Recommendations</div>
          {recs.slice(0, 5).map((rec, i) => (
            <div key={i} className={`rec-item ${rec.priority}`}>
              <div className="rec-item-header">
                <span className={`rec-priority ${rec.priority}`}>{rec.priority?.toUpperCase()}</span>
                <span className="rec-dimension">{DIM_LABELS[rec.dimension] || rec.dimension}</span>
                <span className="rec-impact">{rec.expected_impact}</span>
              </div>
              <p className="rec-action">{rec.action}</p>
            </div>
          ))}
        </div>
      )}

      {/* Strengths */}
      {strengths.length > 0 && (
        <div>
          <div className="dim-scores-title">Strengths</div>
          <div className="strength-tags">
            {strengths.map((s, i) => (
              <span key={i} className="strength-tag">
                <Check size={11} /> {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab config ────────────────────────────────────────────────────

const TABS = [
  { key: "requirements", label: "Requirements", icon: FileText },
  { key: "product",      label: "Product",      icon: Package },
  { key: "compliance",   label: "Compliance",   icon: ShieldCheck },
  { key: "risk",         label: "Risk",         icon: AlertTriangle },
  { key: "pricing",      label: "Pricing",      icon: DollarSign },
  { key: "proposal",     label: "Proposal",     icon: BookOpen },
  { key: "evaluation",   label: "Evaluation",   icon: BarChart3 },
  { key: "logs",         label: "Agent Logs",   icon: Terminal },
];

// ── Main component ────────────────────────────────────────────────

export default function ResultTabs({ result, file }) {
  const [activeTab, setActiveTab] = useState("requirements");
  const execLog = result?.execution_summary?.execution_log || [];
  const isNewPipeline = !!result?.workflow_id;

  return (
    <div className="result-tabs-wrapper">
      {/* Tab nav */}
      <div className="result-nav">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={`result-nav-tab ${activeTab === key ? "active" : ""}`}
            onClick={() => setActiveTab(key)}
          >
            <Icon size={13} />
            {label}
            {key === "logs" && (
              <span className="result-tab-count">{execLog.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="result-tab-content">
        {activeTab === "requirements" && <RequirementsTab data={result?.requirements} />}
        {activeTab === "product"      && <ProductTab      data={result?.product_matches} />}
        {activeTab === "compliance"   && <ComplianceTab   data={result?.compliance_results} />}
        {activeTab === "risk"         && <RiskTab         data={result?.risk_assessment} />}
        {activeTab === "pricing"      && <PricingTab      data={result?.pricing} />}
        {activeTab === "proposal"     && <ProposalTab     data={result?.proposal} />}
        {activeTab === "evaluation"   && <EvaluationTab   data={result?.evaluation} />}
        {activeTab === "logs"         && (
          <AgentLog
            result={isNewPipeline ? result : null}
            logs={result?.agent_logs}
          />
        )}
      </div>
    </div>
  );
}
