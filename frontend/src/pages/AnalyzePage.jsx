// pages/AnalyzePage.jsx
// Single-flow page: Upload → Processing → ProposalWorkflow
// No sidebar, no tabs, no PipelineStepper, no agent terminology.

import { useState } from "react";
import {
  Upload, FileText, AlertCircle, X,
  CheckCircle2, Circle, Loader2, TriangleAlert
} from "lucide-react";
import ProposalWorkflow from "../components/ProposalWorkflow";
import { runAgentPipeline } from "../services/api";

// ── Business-language processing steps ──────────────────────────

const PROCESS_STEPS = [
  "Requirements Extracted",
  "Platform Selected",
  "Technical Configuration Generated",
  "Pricing Calculated",
  "Proposal Generated",
  "Standards Validated",
  "Evaluation Completed",
];

// ── Upload section ───────────────────────────────────────────────

function UploadSection({ file, loading, onFileSelect, onAnalyze, error, onDismissError }) {
  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) onFileSelect(f);
  }
  function handleDragOver(e) { e.preventDefault(); }
  function handleInput(e)    { if (e.target.files[0]) onFileSelect(e.target.files[0]); }

  return (
    <div className="az-upload-wrap">
      <div className="az-upload-header">
        <h1 className="az-upload-title">Analyze RFP Document</h1>
        <p className="az-upload-sub">
          Upload an elevator RFP and receive a complete platform recommendation,
          technical configuration, pricing, and proposal — in under 30 seconds.
        </p>
      </div>

      {error && (
        <div className="alert alert-error az-error">
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          <span>{error}</span>
          <button
            onClick={onDismissError}
            style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "inherit" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Drop zone */}
      <label
        className={`az-dropzone ${file ? "has-file" : ""} ${loading ? "is-loading" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        htmlFor="az-file-input"
      >
        <input
          id="az-file-input"
          type="file"
          accept=".pdf,.docx"
          style={{ display: "none" }}
          onChange={handleInput}
          disabled={loading}
        />
        {file ? (
          <div className="az-file-info">
            <div className="az-file-icon"><FileText size={28} /></div>
            <div>
              <div className="az-file-name">{file.name}</div>
              <div className="az-file-size">{(file.size / 1024).toFixed(0)} KB</div>
            </div>
          </div>
        ) : (
          <div className="az-drop-prompt">
            <div className="az-drop-icon"><Upload size={28} /></div>
            <div className="az-drop-primary">Drop your RFP document here</div>
            <div className="az-drop-secondary">or click to browse</div>
            <div className="az-drop-formats">PDF · DOCX &nbsp;·&nbsp; Max 20 MB</div>
          </div>
        )}
      </label>

      {file && !loading && (
        <button className="btn btn-primary btn-lg az-analyze-btn" onClick={onAnalyze}>
          <FileText size={16} />
          Generate Proposal
        </button>
      )}

      {/* Supported document types note */}
      <div className="az-upload-note">
        Supported documents: elevator tenders, lift specifications, building vertical
        transportation requirements, and elevator quotations.
      </div>
    </div>
  );
}

// ── Processing checklist ─────────────────────────────────────────

function ProcessingChecklist({ activeStep }) {
  return (
    <div className="az-processing-wrap">
      <div className="az-processing-header">
        <div className="az-processing-spinner"><Loader2 size={20} className="spin" /></div>
        <div>
          <div className="az-processing-title">Generating proposal…</div>
          <div className="az-processing-sub">This typically takes 15–30 seconds</div>
        </div>
      </div>

      <div className="az-checklist">
        {PROCESS_STEPS.map((step, i) => {
          const done    = i < activeStep;
          const current = i === activeStep;
          return (
            <div key={step} className={`az-check-item ${done ? "done" : current ? "active" : "pending"}`}>
              <div className="az-check-icon">
                {done
                  ? <CheckCircle2 size={16} />
                  : current
                    ? <Loader2 size={16} className="spin" />
                    : <Circle size={16} />}
              </div>
              <span className="az-check-label">{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Invalid domain state ─────────────────────────────────────────

function InvalidDomainState({ onReset }) {
  return (
    <div className="az-invalid-wrap">
      <div className="az-invalid-icon"><TriangleAlert size={32} /></div>
      <h2 className="az-invalid-title">Unsupported Document</h2>
      <p className="az-invalid-msg">
        The uploaded file does not appear to be an elevator-related RFP.
        Please upload a document that matches one of the following types:
      </p>
      <ul className="az-invalid-list">
        <li>Elevator tenders</li>
        <li>Elevator specifications</li>
        <li>Building lift requirements</li>
        <li>Elevator quotations</li>
        <li>Elevator RFPs</li>
      </ul>
      <button className="btn btn-primary" onClick={onReset}>
        <Upload size={14} /> Upload a Different Document
      </button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────

export default function AnalyzePage() {
  const [file,       setFile]       = useState(null);
  const [result,     setResult]     = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState("");
  const [activeStep, setActiveStep] = useState(-1);

  function handleFileSelect(f) {
    const name = f.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setError("Only PDF and DOCX files are accepted.");
      setFile(null);
      return;
    }
    setFile(f);
    setResult(null);
    setError("");
    setActiveStep(-1);
  }

  function handleReset() {
    setFile(null);
    setResult(null);
    setError("");
    setActiveStep(-1);
  }

  async function handleAnalyze() {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(null);
    setActiveStep(0);

    let step = 0;
    const ticker = setInterval(() => {
      step = Math.min(step + 1, PROCESS_STEPS.length - 1);
      setActiveStep(step);
    }, 1600);

    try {
      const data = await runAgentPipeline(file);
      clearInterval(ticker);
      setActiveStep(PROCESS_STEPS.length); // all done
      setResult(data);
      try { localStorage.setItem("elevate_last_result", JSON.stringify(data)); } catch (_) {}
    } catch (e) {
      clearInterval(ticker);
      setError(e.message || "An error occurred while processing the document.");
      setActiveStep(-1);
    } finally {
      setLoading(false);
    }
  }

  // Detect invalid domain
  const isInvalidDomain =
    result !== null &&
    result?.requirements?.basic_requirements?.is_valid_domain === false;

  return (
    <div className="az-page">

      {/* Always show upload section at top when no result, or as a compact strip after */}
      {!result && !loading && (
        <UploadSection
          file={file}
          loading={loading}
          onFileSelect={handleFileSelect}
          onAnalyze={handleAnalyze}
          error={error}
          onDismissError={() => setError("")}
        />
      )}

      {loading && (
        <div className="az-page-loading">
          <ProcessingChecklist activeStep={activeStep} />
        </div>
      )}

      {/* Invalid domain — show dedicated empty state */}
      {isInvalidDomain && (
        <InvalidDomainState onReset={handleReset} />
      )}

      {/* Valid result — render workflow */}
      {result && !isInvalidDomain && (
        <>
          {/* Compact top bar with option to start over */}
          <div className="az-result-topbar">
            <div className="az-result-file">
              <FileText size={13} />
              <span>{file?.name}</span>
            </div>
            <button className="btn btn-outline btn-sm" onClick={handleReset}>
              <Upload size={12} /> New Document
            </button>
          </div>

          <ProposalWorkflow result={result} />
        </>
      )}
    </div>
  );
}
