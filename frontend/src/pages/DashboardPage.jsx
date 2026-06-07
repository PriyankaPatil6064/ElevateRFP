// pages/DashboardPage.jsx
// Shows last analysis from localStorage. No fake data, no system status, no metrics.
// Empty state when no analysis exists.

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateProposalPDF } from "../utils/pdfExport";
import {
  FileText, Upload, CheckCircle2, AlertCircle,
  Star, Download
} from "lucide-react";

// ── Data helpers ─────────────────────────────────────────────────

function safeGet(obj, path, fallback = null) {
  return path.reduce(
    (acc, key) => (acc && acc[key] !== undefined ? acc[key] : fallback),
    obj
  );
}

function formatINR(amount) {
  const num = Number(amount);
  if (!amount || isNaN(num)) return "—";
  return `₹${num.toLocaleString("en-IN")}`;
}

function getPrimaryPlatform(r) {
  return (
    safeGet(r, ["product_matches","recommendations","primary_recommendation","product","metadata","model"]) ||
    safeGet(r, ["product_matches","recommendations","primary_recommendation","product","model"]) ||
    null
  );
}

function getCoverage(r) {
  const raw = safeGet(r, ["product_matches","recommendations","primary_recommendation","coverage_score"]);
  return raw !== null ? Math.round(raw * 100) : null;
}

function getTotalPrice(r) {
  return (
    safeGet(r, ["pricing","pricing_breakdown","total_price"]) ||
    safeGet(r, ["pricing","total_price"]) ||
    null
  );
}

function getGrade(r) {
  return safeGet(r, ["evaluation","grade"]) || null;
}

function getWinProb(r) {
  const pct  = safeGet(r, ["evaluation","win_probability","percentage"]);
  const prob = safeGet(r, ["evaluation","win_probability","probability"]);
  const cat  = safeGet(r, ["evaluation","win_probability","category"]);
  if (pct)  return { display: pct, category: cat };
  if (prob) return { display: `${Math.round(prob * 100)}%`, category: cat };
  return null;
}

function getStrengths(r) {
  return safeGet(r, ["evaluation","strengths"]) || [];
}

function getGaps(r) {
  return safeGet(r, ["evaluation","critical_gaps"]) || [];
}

function getTechConfigSummary(r) {
  const list = safeGet(r, ["risk_assessment","technical_configuration"]) || [];
  // Group into 5 buckets
  const groups = {
    "Drive System":          list.filter(i => ["drive_system","electrical"].includes(i.category)),
    "Safety Features":       list.filter(i => i.category === "safety"),
    "Accessibility":         list.filter(i => ["accessibility","passenger_interface"].includes(i.category)),
    "Monitoring & Control":  list.filter(i => ["monitoring","controls"].includes(i.category)),
    "Energy Efficiency":     list.filter(i => i.category === "energy"),
  };
  return groups;
}

function getPricingScenarios(r) {
  return safeGet(r, ["pricing","pricing_scenarios"]) || {};
}

function getProposalSections(r) {
  return safeGet(r, ["proposal","sections"]) || {};
}

// ── Grade styling ─────────────────────────────────────────────────
const GRADE_META = {
  A: { color: "#16A34A", label: "Excellent" },
  B: { color: "#2563EB", label: "Strong" },
  C: { color: "#D97706", label: "Moderate" },
  D: { color: "#DC2626", label: "Needs Work" },
};

const SCENARIO_LABELS = {
  pessimistic: "Economy",
  most_likely: "Recommended",
  optimistic:  "Premium",
};

// ── Empty state ───────────────────────────────────────────────────

function EmptyState({ onAnalyze }) {
  return (
    <div className="db-empty">
      <div className="db-empty-icon">
        <FileText size={36} />
      </div>
      <h2 className="db-empty-title">No Proposal Analysis Available</h2>
      <p className="db-empty-msg">
        Upload an elevator RFP to generate recommendations and quotations.
      </p>
      <button className="btn btn-primary btn-lg" onClick={onAnalyze}>
        <Upload size={15} />
        Analyze RFP
      </button>
    </div>
  );
}

// ── Dashboard with result ─────────────────────────────────────────

function DashboardResult({ result, onNewAnalysis }) {
  const platform  = getPrimaryPlatform(result);
  const coverage  = getCoverage(result);
  const totalPrice = getTotalPrice(result);
  const grade     = getGrade(result);
  const winProb   = getWinProb(result);
  const strengths = getStrengths(result);
  const gaps      = getGaps(result);
  const techGroups = getTechConfigSummary(result);
  const scenarios  = getPricingScenarios(result);
  const proposalSections = getProposalSections(result);
  const sectionCount = Object.keys(proposalSections).length;

  const gradeMeta = GRADE_META[grade] || { color: "var(--text-muted)", label: "—" };

  function downloadProposal() {
    try {
      generateProposalPDF(result);
    } catch (err) {
      console.error("PDF generation failed:", err);
      alert("PDF generation failed. Please try again.");
    }
  }

  return (
    <div className="db-result">

      {/* Top bar */}
      <div className="db-result-topbar">
        <div className="db-result-label">Last Analysis</div>
        <button className="btn btn-outline btn-sm" onClick={onNewAnalysis}>
          <Upload size={12} /> New Analysis
        </button>
      </div>

      {/* § 1 — Hero summary card */}
      <div className="db-hero-card">
        <div className="db-hero-topstrip">
          <span>Recommended Platform</span>
          {coverage !== null && <span>{coverage}% requirements coverage</span>}
        </div>
        <div className="db-hero-body">
          <div className="db-hero-platform">
            <div className="db-hero-platform-name">{platform || "Platform Selected"}</div>
            {totalPrice && (
              <div className="db-hero-price">{formatINR(totalPrice)}</div>
            )}
            {totalPrice && (
              <div className="db-hero-price-note">Recommended quotation · Subject to site survey</div>
            )}
          </div>
          <div className="db-hero-outcomes">
            <div className="db-hero-outcome">
              <div className="db-hero-outcome-label">Proposal Grade</div>
              <div className="db-hero-outcome-grade" style={{ color: gradeMeta.color }}>
                {grade || "—"}
              </div>
              <div className="db-hero-outcome-sub">{gradeMeta.label}</div>
            </div>
            <div className="db-hero-outcome-divider" />
            <div className="db-hero-outcome">
              <div className="db-hero-outcome-label">Estimated Win Probability</div>
              <div className="db-hero-outcome-prob">{winProb?.display || "—"}</div>
              {winProb?.category && (
                <div className="db-hero-outcome-sub">{winProb.category}</div>
              )}
            </div>
            <div className="db-hero-outcome-divider" />
            <div className="db-hero-outcome">
              <div className="db-hero-outcome-label">Proposal Status</div>
              <div className="db-hero-outcome-sections">
                {sectionCount > 0
                  ? <><CheckCircle2 size={14} style={{ color: "var(--success)" }} /> {sectionCount} sections ready</>
                  : "—"}
              </div>
              {sectionCount > 0 && (
                <button
                  className="db-hero-download-btn"
                  onClick={downloadProposal}
                >
                  <Download size={11} /> Download PDF
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* § 2 — Strengths + Improvements */}
      {(strengths.length > 0 || gaps.length > 0) && (
        <div className="db-two-col">
          {strengths.length > 0 && (
            <div className="db-panel">
              <div className="db-panel-title">Strengths</div>
              {strengths.map((s, i) => (
                <div key={i} className="db-panel-item ok">
                  <CheckCircle2 size={13} /> {s}
                </div>
              ))}
            </div>
          )}
          {gaps.length > 0 && (
            <div className="db-panel">
              <div className="db-panel-title">Improvement Areas</div>
              {gaps.map((g, i) => (
                <div key={i} className="db-panel-item gap">
                  <AlertCircle size={13} />
                  {typeof g === "string" ? g : g.description || g.gap || JSON.stringify(g)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* § 3 — Technical Configuration Summary */}
      {Object.values(techGroups).some(v => v.length > 0) && (
        <div className="db-section">
          <div className="db-section-title">Technical Configuration Summary</div>
          <div className="db-tech-grid">
            {Object.entries(techGroups).map(([groupLabel, items]) => {
              if (items.length === 0) return null;
              return (
                <div key={groupLabel} className="db-tech-group">
                  <div className="db-tech-group-label">{groupLabel}</div>
                  {items.slice(0, 3).map((item, i) => (
                    <div key={i} className="db-tech-item">
                      <span className="db-tech-feature">{item.feature}</span>
                      <span className="db-tech-value">{item.value}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* § 4 — Pricing Highlights */}
      {Object.keys(scenarios).length > 0 && (
        <div className="db-section">
          <div className="db-section-title">Pricing Highlights</div>
          <div className="db-pricing-row">
            {["pessimistic", "most_likely", "optimistic"].map(key => {
              const s = scenarios[key];
              if (!s) return null;
              const isRec = key === "most_likely";
              return (
                <div key={key} className={`db-price-card ${isRec ? "recommended" : ""}`}>
                  <div className="db-price-label">
                    {SCENARIO_LABELS[key]}
                    {isRec && <Star size={11} fill="currentColor" style={{ marginLeft: 4 }} />}
                  </div>
                  <div className="db-price-value">{formatINR(s.total_price)}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("elevate_last_result");
      if (stored) setResult(JSON.parse(stored));
    } catch (_) {}
    setLoaded(true);
  }, []);

  if (!loaded) return null;

  return (
    <div className="db-page">
      <div className="db-page-header">
        <h1 className="db-page-title">Dashboard</h1>
        <p className="db-page-sub">
          Summary of the last analyzed RFP proposal.
        </p>
      </div>

      {result
        ? <DashboardResult result={result} onNewAnalysis={() => navigate("/analyze")} />
        : <EmptyState onAnalyze={() => navigate("/analyze")} />
      }
    </div>
  );
}