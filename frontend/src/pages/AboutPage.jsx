// pages/AboutPage.jsx
// Business-language overview — no "Agent Pipeline", no "Risk", no "LLM", no buzzwords.
// Sections: Problem Statement, System Workflow, Architecture, Technologies, Features, Future Scope.

import { CheckCircle2, ArrowDown } from "lucide-react";

const WORKFLOW_STAGES = [
  {
    num: "01",
    title: "Requirement Analysis",
    desc: "Extracts building type, floor count, load capacity, speed, lift type, and special requirements from the uploaded document. Missing parameters are recorded as unspecified.",
  },
  {
    num: "02",
    title: "Platform Recommendation",
    desc: "Matches extracted requirements against the platform catalog using semantic search and scoring. Selects the best-fit platform with a coverage score and identifies alternatives.",
  },
  {
    num: "03",
    title: "Technical Configuration",
    desc: "Determines the appropriate drive system, safety features, accessibility provisions, monitoring setup, and energy efficiency measures based on the selected platform and standards.",
  },
  {
    num: "04",
    title: "Pricing",
    desc: "Calculates a complete cost breakdown — base platform cost, installation, customisation, and taxes — across three scenarios: Economy, Recommended, and Premium.",
  },
  {
    num: "05",
    title: "Proposal Generation",
    desc: "Produces a formal proposal document covering executive summary, product recommendation, technical solution, pricing, warranty, delivery schedule, and engineering exclusions.",
  },
  {
    num: "06",
    title: "Standards & Safety",
    desc: "Reviews design against IS 14665, IS 15785, EN 81-20/50, ASME A17.1, and ISO 25745. Each feature is marked Compliant, Recommended, or Not Applicable.",
  },
  {
    num: "07",
    title: "Final Assessment",
    desc: "Scores the proposal across requirement coverage, standards compliance, technical completeness, proposal completeness, and pricing competitiveness. Assigns a grade (A–D) and estimated win probability.",
  },
];

const TECH_STACK = [
  { layer: "API Server",        tech: "FastAPI (Python)",     role: "Request handling, document processing, response orchestration" },
  { layer: "Language Model",    tech: "Google Gemini",        role: "Natural language reasoning, proposal text generation" },
  { layer: "Semantic Search",   tech: "FAISS",                role: "Vector similarity search across the platform catalog" },
  { layer: "Document Parsing",  tech: "PyPDF2",               role: "PDF text extraction and preprocessing" },
  { layer: "Frontend",          tech: "React",                role: "Single-page application interface" },
  { layer: "Data Store",        tech: "SQLite",               role: "Configuration and catalog storage" },
  { layer: "Icon System",       tech: "Lucide React",         role: "Consistent SVG icon set" },
];

const FEATURES = [
  "Accepts PDF and DOCX elevator RFP documents",
  "Rejects non-elevator documents before any processing begins",
  "Extracts structured requirements without manual configuration",
  "Selects from a catalog of 16 elevator platforms across 6 tiers",
  "Produces three pricing scenarios with itemised cost breakdown",
  "Generates a formal 13-section proposal document",
  "Validates design against five Indian and international standards",
  "Assigns a deterministic proposal grade using a weighted formula",
  "Provides download of the complete proposal as a professional PDF document",
  "Stores the last analysis for quick access from the Dashboard",
];

const FUTURE_SCOPE = [
  "Multi-language proposal generation",
  "Support for hydraulic and home-lift RFP specifications",
  "Integration with customer CRM systems for proposal tracking",
  "Competitive benchmarking across multiple vendors",
  "Revision history and version control for proposals",
  "Digital signature and PDF export of the proposal document",
];

export default function AboutPage() {
  return (
    <div className="ab-page">

      {/* Page header */}
      <div className="ab-page-header">
        <h1 className="ab-page-title">About ElevateRFP</h1>
        <p className="ab-page-sub">
          An automated platform that transforms elevator RFP documents into complete,
          standards-validated proposal packages — without manual data entry.
        </p>
      </div>

      <div className="ab-body">

        {/* Problem Statement */}
        <div className="ab-section">
          <div className="ab-section-title">Problem Statement</div>
          <div className="ab-card">
            <p className="ab-para">
              Preparing a formal elevator quotation response is a multi-step process
              involving requirement extraction, platform selection, technical configuration,
              cost estimation, standards review, and document preparation. Each step
              requires domain expertise and typically takes several hours.
            </p>
            <p className="ab-para">
              ElevateRFP automates this entire workflow. A salesperson or bid manager
              uploads an RFP document and receives a complete, evaluated proposal
              package in under 30 seconds.
            </p>
          </div>
        </div>

        {/* System Workflow */}
        <div className="ab-section">
          <div className="ab-section-title">Processing Architecture</div>
          <div className="ab-section-sub">Seven sequential stages, each with a single well-defined responsibility.</div>
          <div className="ab-flow">
            {WORKFLOW_STAGES.map((stage, i) => (
              <div key={stage.num} className="ab-flow-item">
                <div className="ab-flow-card">
                  <div className="ab-flow-num">{stage.num}</div>
                  <div className="ab-flow-body">
                    <div className="ab-flow-title">{stage.title}</div>
                    <div className="ab-flow-desc">{stage.desc}</div>
                  </div>
                </div>
                {i < WORKFLOW_STAGES.length - 1 && (
                  <div className="ab-flow-arrow">
                    <ArrowDown size={16} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Technology Stack */}
        <div className="ab-section">
          <div className="ab-section-title">Technologies Used</div>
          <div className="ab-card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="ab-tech-table">
              <thead>
                <tr>
                  <th>Layer</th>
                  <th>Technology</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {TECH_STACK.map(t => (
                  <tr key={t.layer}>
                    <td className="ab-tech-layer">{t.layer}</td>
                    <td className="ab-tech-name">{t.tech}</td>
                    <td className="ab-tech-role">{t.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Features */}
        <div className="ab-section">
          <div className="ab-section-title">Features</div>
          <div className="ab-card">
            <div className="ab-features-list">
              {FEATURES.map((f, i) => (
                <div key={i} className="ab-feature-item">
                  <CheckCircle2 size={13} style={{ color: "var(--success)", flexShrink: 0, marginTop: 2 }} />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Future Scope */}
        <div className="ab-section">
          <div className="ab-section-title">Future Scope</div>
          <div className="ab-card">
            <div className="ab-features-list">
              {FUTURE_SCOPE.map((f, i) => (
                <div key={i} className="ab-feature-item future">
                  <div className="ab-future-dot" />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
