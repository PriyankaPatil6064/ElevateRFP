// components/PipelineStepper.jsx
import { Check, Loader2 } from "lucide-react";

const STEPS = [
  { key: "requirement_analysis",  label: "Requirement Analysis", sub: "Extract & structure requirements" },
  { key: "product_matching",      label: "Product Matching",     sub: "Semantic RAG search"              },
  { key: "compliance_validation", label: "Compliance Validation", sub: "Standards & regulatory check"    },
  { key: "risk_assessment",       label: "Risk Assessment",      sub: "Identify & score risks"            },
  { key: "pricing_estimation",    label: "Pricing Estimation",   sub: "Cost breakdown & scenarios"        },
  { key: "proposal_writing",      label: "Proposal Writing",     sub: "Generate proposal sections"       },
  { key: "evaluation",            label: "Evaluation",           sub: "Score quality & win probability"  },
];

export default function PipelineStepper({ active, statusText }) {
  // active: 0-7 (steps done or current), -1 = idle, 7 = all done
  return (
    <div className="pipeline-stepper">
      {statusText && active > -1 && active < 7 && (
        <div className="stepper-status">
          <Loader2 size={11} className="spin" />
          {statusText}
        </div>
      )}

      {STEPS.map((step, i) => {
        const done    = active > i;
        const current = active === i;
        return (
          <div
            key={step.key}
            className={`step-item ${done ? "done" : ""} ${current ? "current" : ""}`}
          >
            <div className="step-circle">
              {done    ? <Check size={12} strokeWidth={3} /> :
               current ? <Loader2 size={12} className="spin" /> :
               <span>{i + 1}</span>}
            </div>
            <div className="step-label">
              <span className="step-name">{step.label}</span>
              <span className="step-sub">{step.sub}</span>
            </div>
          </div>
        );
      })}

      {active === 7 && (
        <div className="stepper-complete">
          <Check size={13} />
          Pipeline complete
        </div>
      )}
    </div>
  );
}
