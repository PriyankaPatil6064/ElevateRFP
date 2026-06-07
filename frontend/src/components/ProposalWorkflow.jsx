// components/ProposalWorkflow.jsx
// Enterprise proposal workflow — single scrolling page, no tabs, no agent names.

import { useState } from "react";
import { generateProposalPDF } from "../utils/pdfExport";
import {
  CheckCircle2, Circle, XCircle,
  ChevronDown, ChevronUp, ChevronRight,
  Download, Star, FileText, ShieldCheck,
  Zap, Eye, TrendingUp, UserCheck,
  Settings, ArrowLeftRight, Building2,
  Weight, Layers, Clock, Wrench,
  AlertCircle, Check, BookOpen
} from "lucide-react";

// ── Helpers ────────────────────────────────────────────────────────

function formatINR(amount) {
  if (amount === null || amount === undefined || amount === "") return "—";
  const num = Number(amount);
  if (isNaN(num)) return "—";
  return `₹${num.toLocaleString("en-IN")}`;
}



function SectionTitle({ label, sub }) {
  return (
    <div className="wf-section-title-block">
      <h2 className="wf-section-h2">{label}</h2>
      {sub && <p className="wf-section-sub">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    "Compliant":       { cls: "wf-badge-compliant",    label: "Compliant" },
    "Recommended":     { cls: "wf-badge-recommended",  label: "Recommended" },
    "Not Applicable":  { cls: "wf-badge-na",           label: "Not Applicable" },
    "mandatory":       { cls: "wf-badge-compliant",    label: "Mandatory" },
    "recommended":     { cls: "wf-badge-recommended",  label: "Recommended" },
    "optional":        { cls: "wf-badge-na",           label: "Optional" },
  };
  const m = map[status] || { cls: "wf-badge-na", label: status || "—" };
  return <span className={`wf-badge ${m.cls}`}>{m.label}</span>;
}

// ── § 1 — Platform Hero ───────────────────────────────────────────

function PlatformHero({ productData, pricingData, evalData, onViewProposal, onViewAlternatives }) {
  const recs    = productData?.recommendations || {};
  const primary = recs.primary_recommendation  || {};
  const product = primary.product?.metadata || primary.product || {};
  const alts    = recs.alternative_options   || [];

  const coveragePct = Math.round((primary.coverage_score || 0) * 100);
  const grade       = evalData?.grade || "—";
  const winProb     = evalData?.win_probability || {};
  const probDisplay = winProb.percentage || (winProb.probability ? `${Math.round(winProb.probability * 100)}%` : "—");
  const totalPrice  = pricingData?.pricing_breakdown?.total_price;

  const gradeColors = { A: "#16A34A", B: "#2563EB", C: "#D97706", D: "#DC2626" };
  const gradeColor  = gradeColors[grade] || "var(--text-muted)";

  return (
    <div className="wf-hero">
      {/* Top strip */}
      <div className="wf-hero-topstrip">
        <div className="wf-hero-topstrip-left">
          <span className="wf-hero-label">Recommended Platform</span>
          {product.tier && <span className="wf-hero-tier">{product.tier}</span>}
        </div>
        <span className="wf-hero-coverage">{coveragePct}% requirements coverage</span>
      </div>

      {/* Main content */}
      <div className="wf-hero-main">
        <div className="wf-hero-name-col">
          <div className="wf-hero-id">{product.product_id || ""}</div>
          <h1 className="wf-hero-name">{product.model || "Platform Selected"}</h1>
          {primary.reasoning && (
            <p className="wf-hero-desc">{primary.reasoning}</p>
          )}
          {product.recommended_use_cases?.length > 0 && (
            <div className="wf-hero-usecases">
              <span className="wf-hero-usecases-label">Suitable for:</span>
              {product.recommended_use_cases.slice(0, 4).map((u, i) => (
                <span key={i} className="wf-hero-usecase-chip">{u}</span>
              ))}
            </div>
          )}
        </div>

        <div className="wf-hero-right-col">
          {/* Specs */}
          <div className="wf-hero-specs">
            {[
              { Icon: Building2, label: "Building Type",  value: product.building_type || "—" },
              { Icon: Weight,    label: "Load Capacity",   value: product.capacity_kg ? `${product.capacity_kg} kg` : "—" },
              { Icon: Layers,    label: "Max Floors",      value: product.max_floors   ? `${product.max_floors} floors` : "—" },
              { Icon: Zap,       label: "Rated Speed",     value: product.speed_ms     ? `${product.speed_ms} m/s` : "—" },
            ].map(s => (
              <div key={s.label} className="wf-hero-spec">
                <div className="wf-hero-spec-icon"><s.Icon size={14} /></div>
                <div>
                  <div className="wf-hero-spec-label">{s.label}</div>
                  <div className="wf-hero-spec-value">{s.value}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Quotation + outcomes */}
          <div className="wf-hero-quotation-block">
            <div className="wf-hero-quotation-label">Recommended Quotation</div>
            <div className="wf-hero-quotation-amount">{formatINR(totalPrice)}</div>
            <div className="wf-hero-quotation-note">All-inclusive estimate · Subject to site survey</div>
          </div>

          <div className="wf-hero-outcome-row">
            <div className="wf-hero-outcome">
              <div className="wf-hero-outcome-label">Proposal Grade</div>
              <div className="wf-hero-outcome-value" style={{ color: gradeColor }}>{grade}</div>
            </div>
            <div className="wf-hero-outcome-divider" />
            <div className="wf-hero-outcome">
              <div className="wf-hero-outcome-label">Estimated Win Probability</div>
              <div className="wf-hero-outcome-value" style={{ color: "#16A34A" }}>{probDisplay}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="wf-hero-actions">
        <button className="btn btn-primary btn-lg" onClick={onViewProposal}>
          <FileText size={15} /> View Proposal
        </button>
        {alts.length > 0 && (
          <button className="btn btn-outline btn-lg" onClick={onViewAlternatives}>
            <Layers size={14} /> View Alternatives ({alts.length})
          </button>
        )}
      </div>
    </div>
  );
}

// ── § 2 — Alternative Platforms ───────────────────────────────────

function AlternativePlatforms({ productData }) {
  const recs = productData?.recommendations || {};
  const alts = (recs.alternative_options || []).slice(0, 3);

  if (alts.length === 0) return null;

  return (
    <div className="wf-section">
      <SectionTitle label="Alternative Platforms" />
      <div className="wf-alts-grid">
        {alts.map((alt, i) => {
          const p      = alt.product?.metadata || alt.product || {};
          const covPct = Math.round((alt.product?.coverage_score || alt.coverage_score || 0) * 100);
          const price  = p.base_price;
          return (
            <div key={i} className="wf-alt-card">
              <div className="wf-alt-card-header">
                <div>
                  <div className="wf-alt-rank">Option {i + 2}</div>
                  <div className="wf-alt-name">{p.model || `Alternative ${i + 2}`}</div>
                  {p.product_id && <div className="wf-alt-id">{p.product_id}</div>}
                </div>
                {p.tier && <span className="wf-tier-badge">{p.tier}</span>}
              </div>
              <div className="wf-alt-specs">
                {covPct > 0 && <span><Check size={12} /> {covPct}% coverage</span>}
                {p.capacity_kg && <span><Weight size={12} /> {p.capacity_kg} kg</span>}
                {p.max_floors  && <span><Layers size={12} /> {p.max_floors} floors</span>}
              </div>
              {price && (
                <div className="wf-alt-price">
                  Starting from {formatINR(price)}
                </div>
              )}
              {alt.differentiation && (
                <p className="wf-alt-diff">{alt.differentiation}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── § 3 — Why This Platform Was Selected ─────────────────────────

function SelectionRationale({ productData }) {
  const recs            = productData?.recommendations || {};
  const primary         = recs.primary_recommendation  || {};
  const coverageDetails = primary.coverage_details     || {};
  const strengths       = primary.key_strengths        || [];

  // Convert coverage_details dict to displayable rows
  // Keys may be snake_case — prettify them
  function prettify(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  function isTruthy(val) {
    if (typeof val === "boolean") return val;
    if (typeof val === "string")  return val.toLowerCase() !== "false" && val !== "no" && val !== "0" && val.length > 0;
    if (typeof val === "number")  return val > 0;
    return !!val;
  }

  const detailEntries = Object.entries(coverageDetails).filter(([k]) => !["score", "total"].includes(k));

  if (detailEntries.length === 0 && strengths.length === 0) return null;

  return (
    <div className="wf-section">
      <SectionTitle label="Why This Platform Was Selected" />
      <div className="wf-card">
        {detailEntries.length > 0 && (
          <div className="wf-checklist">
            {detailEntries.map(([key, val]) => {
              const ok = isTruthy(val);
              return (
                <div key={key} className={`wf-check-row ${ok ? "ok" : "na"}`}>
                  <div className={`wf-check-icon ${ok ? "ok" : "na"}`}>
                    {ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  </div>
                  <div className="wf-check-body">
                    <span className="wf-check-label">{prettify(key)}</span>
                    {typeof val === "string" && val.length > 5 && (
                      <span className="wf-check-note">{val}</span>
                    )}
                  </div>
                  <StatusBadge status={ok ? "Compliant" : "Not Applicable"} />
                </div>
              );
            })}
          </div>
        )}

        {strengths.length > 0 && (
          <div className={detailEntries.length > 0 ? "wf-strengths-section" : ""}>
            {detailEntries.length > 0 && <div className="wf-section-divider" />}
            <div className="wf-strengths-title">Key Strengths</div>
            <div className="wf-strengths-grid">
              {strengths.map((s, i) => (
                <div key={i} className="wf-strength-item">
                  <Check size={13} /> {s}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── § 4 — Technical Configuration ────────────────────────────────

const TECH_GROUPS = [
  { key: "drive_system",  label: "Drive System",         Icon: Zap,          categories: ["drive_system", "electrical"] },
  { key: "safety",        label: "Safety Features",      Icon: ShieldCheck,  categories: ["safety"] },
  { key: "accessibility", label: "Accessibility",        Icon: UserCheck,    categories: ["accessibility", "passenger_interface"] },
  { key: "monitoring",    label: "Monitoring & Control", Icon: Eye,          categories: ["monitoring", "controls"] },
  { key: "energy",        label: "Energy Efficiency",    Icon: TrendingUp,   categories: ["energy"] },
  { key: "doors",         label: "Doors",                Icon: ArrowLeftRight, categories: ["doors"] },
];

function TechAccordion({ group, items }) {
  const [open, setOpen] = useState(false);
  const { Icon } = group;

  if (items.length === 0) return null;

  return (
    <div className={`wf-accordion ${open ? "open" : ""}`}>
      <button className="wf-accordion-trigger" onClick={() => setOpen(o => !o)}>
        <div className="wf-accordion-left">
          <span className="wf-accordion-icon"><Icon size={15} /></span>
          <span className="wf-accordion-label">{group.label}</span>
          <span className="wf-accordion-count">{items.length} items</span>
        </div>
        {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>

      {open && (
        <div className="wf-accordion-body">
          {items.map((item, i) => (
            <div key={i} className="wf-tech-row">
              <div className="wf-tech-row-main">
                <div className="wf-tech-feature">{item.feature}</div>
                <div className="wf-tech-value">{item.value}</div>
              </div>
              <div className="wf-tech-row-meta">
                <StatusBadge status={item.applicability} />
                {item.rationale && (
                  <div className="wf-tech-rationale">{item.rationale}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TechnicalConfiguration({ riskData }) {
  const techList = riskData?.technical_configuration || [];
  const notes    = riskData?.engineering_notes || [];

  if (techList.length === 0) return null;

  // Group items by category field
  function getItems(categories) {
    return techList.filter(item => categories.includes(item.category));
  }

  return (
    <div className="wf-section">
      <SectionTitle
        label="Technical Configuration"
        sub="System design, features, and applicability — all based on building requirements and applicable standards"
      />
      <div className="wf-card" style={{ padding: 0, overflow: "hidden" }}>
        {TECH_GROUPS.map(group => (
          <TechAccordion key={group.key} group={group} items={getItems(group.categories)} />
        ))}
      </div>

      {notes.length > 0 && (
        <div className="wf-engineering-notes">
          <div className="wf-notes-title">
            <Wrench size={13} /> Engineering Notes
          </div>
          {notes.slice(0, 4).map((note, i) => (
            <div key={i} className="wf-note-item">{note}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── § 5 — Pricing ─────────────────────────────────────────────────

const SCENARIO_MAP = {
  pessimistic: { label: "Economy",     note: "Minimum specification",      star: false },
  most_likely: { label: "Recommended", note: "Best value for requirements", star: true  },
  optimistic:  { label: "Premium",     note: "Enhanced specification",      star: false },
};

const COMPONENT_LABELS = {
  base_product_cost:  "Base Platform Cost",
  installation_cost:  "Installation & Commissioning",
  customization_cost: "Customisation",
  compliance_cost:    "Standards & Certification",
  risk_adjustment:    "Contingency Buffer",
};

function PricingSection({ pricingData }) {
  const breakdown  = pricingData?.pricing_breakdown || {};
  const scenarios  = pricingData?.pricing_scenarios || {};
  const components = breakdown.components           || {};

  const scenarioOrder = ["pessimistic", "most_likely", "optimistic"];
  const activeScenarios = scenarioOrder.filter(k => scenarios[k]);

  return (
    <div className="wf-section">
      <SectionTitle
        label="Pricing"
        sub="All amounts in Indian Rupees (INR). Indicative estimate — subject to final site survey and detailed engineering."
      />

      {/* 3-column scenarios */}
      {activeScenarios.length > 0 && (
        <div className="wf-pricing-grid">
          {activeScenarios.map(k => {
            const s    = scenarios[k];
            const meta = SCENARIO_MAP[k] || { label: k, note: "", star: false };
            return (
              <div key={k} className={`wf-scenario-card ${meta.star ? "recommended" : ""}`}>
                <div className="wf-scenario-header">
                  <span className="wf-scenario-label">{meta.label}</span>
                  {meta.star && (
                    <span className="wf-scenario-star">
                      <Star size={11} fill="currentColor" /> Recommended
                    </span>
                  )}
                </div>
                <div className="wf-scenario-price">{formatINR(s.total_price)}</div>
                <div className="wf-scenario-note">{meta.note}</div>
                {s.rationale && <div className="wf-scenario-rationale">{s.rationale}</div>}
              </div>
            );
          })}
        </div>
      )}

      {/* Cost breakdown */}
      {Object.keys(components).length > 0 && (
        <div className="wf-card mt-4">
          <div className="wf-breakdown-title">Cost Breakdown</div>
          <table className="wf-breakdown-table">
            <tbody>
              {Object.entries(components).map(([key, val]) => (
                <tr key={key}>
                  <td>{COMPONENT_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</td>
                  <td className="wf-breakdown-amount">{formatINR(val)}</td>
                </tr>
              ))}
              {breakdown.tax_amount > 0 && (
                <tr>
                  <td>GST / Tax</td>
                  <td className="wf-breakdown-amount">{formatINR(breakdown.tax_amount)}</td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr>
                <td><strong>Total Quotation Value</strong></td>
                <td className="wf-breakdown-amount"><strong>{formatINR(breakdown.total_price)}</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}

// ── § 6 — Proposal Summary ────────────────────────────────────────

const PROPOSAL_CARDS = [
  { key: "executive_summary",    label: "Executive Summary",    Icon: BookOpen },
  { key: "warranty",             label: "Warranty",             Icon: ShieldCheck },
  { key: "implementation_plan",  label: "Delivery Schedule",    Icon: Clock },
  { key: "conclusion",           label: "Payment Terms & Contact", Icon: FileText },
  { key: "engineering_exclusions", label: "Engineering Exclusions", Icon: Wrench },
  { key: "amc",                  label: "Annual Maintenance",   Icon: Settings },
];

function ProposalSummary({ proposalData, result }) {
  const sections   = proposalData?.sections || {};
  const [modal, setModal] = useState(null);

  function findSection(key) {
    if (sections[key]) return sections[key];
    // Fuzzy match by title
    const lk = key.toLowerCase().replace(/_/g, " ").split(" ")[0];
    return Object.values(sections).find(s => s.title?.toLowerCase().includes(lk));
  }

  function handleDownload() {
    try {
      generateProposalPDF(result);
    } catch (err) {
      console.error("PDF generation failed:", err);
      alert("PDF generation failed. Please try again.");
    }
  }

  return (
    <div className="wf-section" id="wf-proposal">
      <SectionTitle
        label="Proposal Summary"
        sub="Key sections of the generated proposal. Click any card to read the full section."
      />

      <div className="wf-proposal-grid">
        {PROPOSAL_CARDS.map(({ key, label, Icon }) => {
          const section = findSection(key);
          const excerpt = section?.content?.trim().slice(0, 140);
          return (
            <div
              key={key}
              className={`wf-proposal-card ${section ? "has-content" : "no-content"}`}
              onClick={() => section && setModal({ label, content: section.content })}
            >
              <div className="wf-proposal-card-icon"><Icon size={16} /></div>
              <div className="wf-proposal-card-label">{label}</div>
              {excerpt ? (
                <div className="wf-proposal-card-excerpt">{excerpt}…</div>
              ) : (
                <div className="wf-proposal-card-empty">Not included in proposal</div>
              )}
              {section && (
                <div className="wf-proposal-card-read">
                  Read more <ChevronRight size={11} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="wf-download-row">
        <button className="btn btn-primary btn-lg" onClick={handleDownload}>
          <Download size={15} /> Download PDF Proposal
        </button>
        <span className="wf-download-note">
          {Object.keys(sections).length} sections · professional PDF format
        </span>
      </div>

      {/* Inline modal */}
      {modal && (
        <div className="wf-modal-overlay" onClick={() => setModal(null)}>
          <div className="wf-modal" onClick={e => e.stopPropagation()}>
            <div className="wf-modal-header">
              <span className="wf-modal-title">{modal.label}</span>
              <button className="wf-modal-close" onClick={() => setModal(null)}>✕</button>
            </div>
            <div className="wf-modal-body">
              <pre className="wf-modal-text">{modal.content}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── § 7 — Standards & Safety ──────────────────────────────────────

function FeatureRow({ item }) {
  const isOk  = item.status === "Compliant";
  const isNA  = item.status === "Not Applicable";
  return (
    <div className={`wf-feature-row ${isOk ? "ok" : isNA ? "na" : "rec"}`}>
      <div className={`wf-feature-icon ${isOk ? "ok" : isNA ? "na" : "rec"}`}>
        {isOk  ? <CheckCircle2 size={15} /> :
         isNA  ? <Circle size={15} />       :
                 <ShieldCheck size={15} />}
      </div>
      <div className="wf-feature-body">
        <span className="wf-feature-name">{item.feature || item.standard_name}</span>
        {item.standard && <span className="wf-feature-standard">{item.standard}</span>}
        {item.rationale && <div className="wf-feature-rationale">{item.rationale}</div>}
      </div>
      <StatusBadge status={item.status} />
    </div>
  );
}

function FeatureGroup({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="wf-feature-group">
      <div className="wf-feature-group-title">{title}</div>
      {items.map((item, i) => <FeatureRow key={i} item={item} />)}
    </div>
  );
}

function StandardsAndSafety({ complianceData }) {
  const safetyFeatures       = complianceData?.safety_features       || [];
  const accessibilityFeatures = complianceData?.accessibility_features || [];
  const energyEfficiency     = complianceData?.energy_efficiency      || [];
  const fireSafety           = complianceData?.fire_safety            || [];
  const standardsCompliance  = complianceData?.standards_compliance   || [];

  return (
    <div className="wf-section">
      <SectionTitle
        label="Standards & Safety"
        sub="Design compliance and feature applicability per IS 14665, IS 15785, EN 81, ASME A17.1, and ISO 25745"
      />

      {/* Standards reference strip */}
      {standardsCompliance.length > 0 && (
        <div className="wf-standards-strip">
          {standardsCompliance.map((s, i) => (
            <div key={i} className={`wf-standard-pill ${s.status === "Compliant" ? "compliant" : "recommended"}`}>
              <CheckCircle2 size={12} />
              <span className="wf-standard-pill-name">{s.standard_name}</span>
              <span className="wf-standard-pill-status">{s.status}</span>
            </div>
          ))}
        </div>
      )}

      <div className="wf-features-layout">
        <FeatureGroup title="Safety Features" items={safetyFeatures} />
        <FeatureGroup title="Accessibility" items={accessibilityFeatures} />
        <FeatureGroup title="Energy Efficiency" items={energyEfficiency} />
        {fireSafety.length > 0 && (
          <FeatureGroup title="Fire Safety" items={fireSafety} />
        )}
      </div>

      <p className="wf-standards-footnote">
        "Designed in accordance with" indicates the product meets the cited standard's design requirements.
        "Recommended under" indicates the standard is applicable and the product follows its guidance.
        Statutory certification requires inspection by a registered authority.
      </p>
    </div>
  );
}

// ── § 8 — Final Evaluation ────────────────────────────────────────

function FinalEvaluation({ evalData }) {
  const grade      = evalData?.grade             || "—";
  const winProb    = evalData?.win_probability   || {};
  const strengths  = evalData?.strengths         || [];
  const gaps       = evalData?.critical_gaps     || [];
  const assessment = evalData?.overall_assessment || evalData?.summary || "";
  const weighted   = Math.round(evalData?.weighted_score || 0);
  const scores     = evalData?.dimension_scores  || {};

  const probDisplay = winProb.percentage
    || (winProb.probability ? `${Math.round(winProb.probability * 100)}%` : "—");

  const GRADE_DESC = {
    A: "Excellent Proposal — Strong competitive position",
    B: "Strong Proposal — Well-suited to requirements",
    C: "Moderate Proposal — Improvements recommended",
    D: "Needs Improvement — Review critical areas",
  };
  const gradeColors = { A: "#16A34A", B: "#2563EB", C: "#D97706", D: "#DC2626" };
  const gradeColor  = gradeColors[grade] || "var(--text-muted)";

  const DIM_LABELS = {
    requirement_coverage:    "Requirement Coverage",
    standards_compliance:    "Standards Compliance",
    technical_completeness:  "Technical Completeness",
    proposal_completeness:   "Proposal Completeness",
    pricing_competitiveness: "Pricing Competitiveness",
  };

  function dimColor(pct) {
    if (pct >= 75) return "#16A34A";
    if (pct >= 50) return "#D97706";
    return "#DC2626";
  }

  return (
    <div className="wf-section">
      <SectionTitle label="Final Evaluation" />

      <div className="wf-eval-card">
        {/* Grade + win probability */}
        <div className="wf-eval-top">
          <div className="wf-eval-grade-block">
            <div className="wf-eval-grade" style={{ color: gradeColor }}>{grade}</div>
            <div className="wf-eval-grade-desc">{GRADE_DESC[grade] || "Evaluation complete"}</div>
            {weighted > 0 && <div className="wf-eval-score">{weighted} overall score</div>}
          </div>
          <div className="wf-eval-divider" />
          <div className="wf-eval-prob-block">
            <div className="wf-eval-prob-label">Estimated Win Probability</div>
            <div className="wf-eval-prob-value">{probDisplay}</div>
            {winProb.category && <div className="wf-eval-prob-cat">{winProb.category}</div>}
          </div>
        </div>

        {/* Dimension bars */}
        {Object.keys(scores).length > 0 && (
          <div className="wf-eval-dims">
            {Object.entries(scores).map(([dim, info]) => {
              const pct = Math.round((info.score || 0) * 100);
              return (
                <div key={dim} className="wf-dim-row">
                  <span className="wf-dim-label">{DIM_LABELS[dim] || dim.replace(/_/g, " ")}</span>
                  <div className="wf-dim-track">
                    <div
                      className="wf-dim-fill"
                      style={{ width: `${pct}%`, background: dimColor(pct) }}
                    />
                  </div>
                  <span className="wf-dim-score" style={{ color: dimColor(pct) }}>{pct}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Strengths + Improvement areas */}
        {(strengths.length > 0 || gaps.length > 0) && (
          <div className="wf-eval-bottom">
            {strengths.length > 0 && (
              <div className="wf-eval-col">
                <div className="wf-eval-col-title">Strengths</div>
                {strengths.map((s, i) => (
                  <div key={i} className="wf-eval-item ok">
                    <CheckCircle2 size={13} /> {s}
                  </div>
                ))}
              </div>
            )}
            {gaps.length > 0 && (
              <div className="wf-eval-col">
                <div className="wf-eval-col-title">Improvement Areas</div>
                {gaps.map((g, i) => (
                  <div key={i} className="wf-eval-item gap">
                    <AlertCircle size={13} />
                    {typeof g === "string" ? g : g.description || g.gap || JSON.stringify(g)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Overall assessment */}
        {assessment && (
          <div className="wf-eval-assessment">
            <div className="wf-eval-assessment-label">Overall Assessment</div>
            <p className="wf-eval-assessment-text">{assessment}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────

export default function ProposalWorkflow({ result }) {
  const [showAlts, setShowAlts] = useState(false);

  function scrollTo(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="wf-root">

      {/* § 1 — Recommended Platform */}
      <PlatformHero
        productData={result?.product_matches}
        pricingData={result?.pricing}
        evalData={result?.evaluation}
        onViewProposal={() => scrollTo("wf-proposal")}
        onViewAlternatives={() => setShowAlts(s => !s)}
      />

      {/* § 2 — Alternative Platforms */}
      {showAlts && (
        <AlternativePlatforms productData={result?.product_matches} />
      )}
      {!showAlts && (result?.product_matches?.recommendations?.alternative_options || []).length > 0 && (
        <div style={{ textAlign: "center", padding: "8px 0 0" }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setShowAlts(true)}
            style={{ color: "var(--text-muted)", fontSize: 13 }}
          >
            Show alternative platforms <ChevronDown size={13} />
          </button>
        </div>
      )}

      {/* § 3 — Why This Platform Was Selected */}
      <SelectionRationale productData={result?.product_matches} />

      {/* § 4 — Technical Configuration */}
      <TechnicalConfiguration riskData={result?.risk_assessment} />

      {/* § 5 — Pricing */}
      <PricingSection pricingData={result?.pricing} />

      {/* § 6 — Proposal Summary */}
      <ProposalSummary proposalData={result?.proposal} result={result} />

      {/* § 7 — Standards & Safety */}
      <StandardsAndSafety complianceData={result?.compliance_results} />

      {/* § 8 — Final Evaluation */}
      <FinalEvaluation evalData={result?.evaluation} />

    </div>
  );
}
