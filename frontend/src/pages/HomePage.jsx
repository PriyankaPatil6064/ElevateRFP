// pages/HomePage.jsx
// Clean enterprise hero page — no fake stats, no agent cards, no buzzwords.
// Business flow: Upload → Analyze → Recommend → Configure → Price → Propose → Validate → Assess

import { useNavigate } from "react-router-dom";
import { FileSearch, BookOpen, ArrowRight, ChevronRight } from "lucide-react";

const WORKFLOW_STEPS = [
  {
    num: "01",
    title: "Upload RFP",
    desc: "Submit an elevator RFP document in PDF or DOCX format.",
  },
  {
    num: "02",
    title: "Analyze Requirements",
    desc: "Building type, floor count, load capacity, speed, and special requirements are identified and structured.",
  },
  {
    num: "03",
    title: "Recommend Platform",
    desc: "The best-matching elevator platform is selected from the catalog based on your requirements.",
  },
  {
    num: "04",
    title: "Generate Technical Solution",
    desc: "Drive system, safety features, accessibility provisions, and monitoring are configured for the selected platform.",
  },
  {
    num: "05",
    title: "Estimate Pricing",
    desc: "A complete cost breakdown is produced across three pricing scenarios — Economy, Recommended, and Premium.",
  },
  {
    num: "06",
    title: "Prepare Proposal",
    desc: "A formal quotation document is generated, covering executive summary, warranty, delivery schedule, and exclusions.",
  },
  {
    num: "07",
    title: "Validate Standards",
    desc: "Design is reviewed against IS 14665, IS 15785, EN 81-20/50, ASME A17.1, and ISO 25745.",
  },
  {
    num: "08",
    title: "Final Assessment",
    desc: "The proposal is scored across requirement coverage, technical completeness, and pricing competitiveness. A grade and win probability are assigned.",
  },
];

const TECH_ITEMS = [
  { name: "FastAPI",  note: "Backend API server" },
  { name: "React",   note: "Frontend interface" },
  { name: "FAISS",   note: "Semantic product search" },
  { name: "Gemini",  note: "Natural language reasoning" },
  { name: "SQLite",  note: "Configuration storage" },
];

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="hp-page">

      {/* ── Hero ── */}
      <section className="hp-hero">
        <div className="hp-hero-inner">
          <div className="hp-hero-content">
            <div className="hp-hero-eyebrow">
              Elevator Proposal Automation Platform
            </div>
            <h1 className="hp-hero-title">
              ElevateRFP
            </h1>
            <p className="hp-hero-desc">
              Analyze customer requirements, recommend suitable elevator platforms,
              generate quotations, and prepare proposal documents — automatically,
              from a single uploaded RFP.
            </p>
            <div className="hp-hero-actions">
              <button
                className="btn btn-primary btn-lg"
                onClick={() => navigate("/analyze")}
              >
                <FileSearch size={16} />
                Analyze RFP
              </button>
              <button
                className="btn btn-outline btn-lg"
                onClick={() => navigate("/catalog")}
              >
                <BookOpen size={16} />
                View Platform Catalog
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Workflow ── */}
      <section className="hp-workflow">
        <div className="hp-section-inner">
          <div className="hp-section-header">
            <h2 className="hp-section-title">How It Works</h2>
            <p className="hp-section-sub">
              Eight sequential stages transform a raw RFP document into a complete,
              evaluated elevator proposal.
            </p>
          </div>

          <div className="hp-steps">
            {WORKFLOW_STEPS.map((step, i) => (
              <div key={step.num} className="hp-step">
                <div className="hp-step-left">
                  <div className="hp-step-num">{step.num}</div>
                  {i < WORKFLOW_STEPS.length - 1 && (
                    <div className="hp-step-connector" />
                  )}
                </div>
                <div className="hp-step-body">
                  <div className="hp-step-title">{step.title}</div>
                  <div className="hp-step-desc">{step.desc}</div>
                </div>
                {i < WORKFLOW_STEPS.length - 1 && (
                  <div className="hp-step-arrow">
                    <ChevronRight size={14} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section className="hp-tech">
        <div className="hp-section-inner">
          <div className="hp-section-header">
            <h2 className="hp-section-title">Technology</h2>
            <p className="hp-section-sub">
              Built on established, production-grade technologies.
            </p>
          </div>
          <div className="hp-tech-row">
            {TECH_ITEMS.map(t => (
              <div key={t.name} className="hp-tech-item">
                <div className="hp-tech-name">{t.name}</div>
                <div className="hp-tech-note">{t.note}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="hp-cta">
        <div className="hp-section-inner">
          <div className="hp-cta-inner">
            <h2 className="hp-cta-title">Ready to analyze your RFP?</h2>
            <p className="hp-cta-sub">
              Upload a PDF or DOCX and receive a complete proposal in under 30 seconds.
            </p>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => navigate("/analyze")}
            >
              Analyze RFP <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </section>

    </div>
  );
}
