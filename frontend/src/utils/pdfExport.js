/**
 * pdfExport.js
 * Generates a professional elevator quotation PDF document.
 * 14 sections — A4 portrait — blue accent (#2563EB).
 * Pure client-side: jsPDF + jspdf-autotable.
 * No backend calls. No markdown. No AI terminology.
 */

import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

// ── Design tokens ──────────────────────────────────────────────────────────
const BLUE      = [37, 99, 235];     // #2563EB
const BLUE_LIGHT= [239, 246, 255];   // #EFF6FF
const DARK      = [17, 24, 39];      // #111827
const GRAY      = [107, 114, 128];   // #6B7280
const LIGHT     = [249, 250, 251];   // #F9FAFB
const WHITE     = [255, 255, 255];
const SUCCESS   = [22, 163, 74];     // #16A34A
const WARNING   = [217, 119, 6];     // #D97706
const DANGER    = [220, 38, 38];     // #DC2626
const BORDER    = [229, 231, 235];   // #E5E7EB

const PAGE_W    = 210;
const PAGE_H    = 297;
const MARGIN    = 18;
const CONTENT_W = PAGE_W - MARGIN * 2;

// ── Helpers ────────────────────────────────────────────────────────────────

function formatINR(amount) {
  const num = Number(amount);
  if (!amount || isNaN(num)) return "—";
  return "\u20B9" + num.toLocaleString("en-IN");
}

function today() {
  return new Date().toLocaleDateString("en-IN", {
    day: "2-digit", month: "long", year: "numeric",
  });
}

function validity() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toLocaleDateString("en-IN", {
    day: "2-digit", month: "long", year: "numeric",
  });
}

function refNo() {
  const y  = new Date().getFullYear();
  const rn = Math.floor(Math.random() * 900 + 100);
  return `ELV-${y}-${rn}`;
}

function safeText(val, fallback = "—") {
  if (val === null || val === undefined || val === "") return fallback;
  return String(val);
}

function gradeColor(grade) {
  return grade === "A" ? SUCCESS : grade === "B" ? BLUE : grade === "C" ? WARNING : DANGER;
}

// ── Layout primitives ──────────────────────────────────────────────────────

class PDFBuilder {
  constructor() {
    this.doc   = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    this.page  = 1;
    this.total = 0; // filled after all pages added
    this.y     = MARGIN;
    this.ref   = refNo();
  }

  // ── Cursor ──────────────────────────────────────────────────────────────

  addY(delta) { this.y += delta; }

  needPage(needed = 20) {
    if (this.y + needed > PAGE_H - 22) {
      this.newPage();
      return true;
    }
    return false;
  }

  newPage() {
    this.doc.addPage();
    this.page++;
    this.y = MARGIN + 12;
    this._drawRunningHeader();
    this._drawFooter();
  }

  // ── Typography ──────────────────────────────────────────────────────────

  font(style = "normal", size = 10, color = DARK) {
    this.doc.setFont("helvetica", style);
    this.doc.setFontSize(size);
    this.doc.setTextColor(...color);
  }

  text(str, x, y, opts = {}) {
    this.doc.text(String(str), x, y, opts);
  }

  // ── Shapes ──────────────────────────────────────────────────────────────

  rect(x, y, w, h, fill = WHITE, radius = 0) {
    this.doc.setFillColor(...fill);
    if (radius > 0) {
      this.doc.roundedRect(x, y, w, h, radius, radius, "F");
    } else {
      this.doc.rect(x, y, w, h, "F");
    }
  }

  line(x1, y1, x2, y2, color = BORDER, width = 0.3) {
    this.doc.setDrawColor(...color);
    this.doc.setLineWidth(width);
    this.doc.line(x1, y1, x2, y2);
  }

  // ── Section heading ─────────────────────────────────────────────────────

  sectionHeading(title, num) {
    this.needPage(24);
    // Blue left rule
    this.doc.setFillColor(...BLUE);
    this.doc.rect(MARGIN, this.y, 3, 7, "F");
    // Number
    this.font("bold", 7, BLUE);
    this.text(`${num < 10 ? "0" + num : num}`, MARGIN + 5, this.y + 5);
    // Title
    this.font("bold", 13, DARK);
    this.text(title, MARGIN + 14, this.y + 5.5);
    this.y += 13;
    // Divider
    this.line(MARGIN, this.y, MARGIN + CONTENT_W, this.y, BORDER, 0.3);
    this.y += 5;
  }

  // ── Key-value row ────────────────────────────────────────────────────────

  kvRow(label, value, y, x = MARGIN) {
    this.font("normal", 8.5, GRAY);
    this.text(label, x, y);
    this.font("bold", 8.5, DARK);
    this.text(safeText(value), x + 52, y);
  }

  // ── Running header (pages 2+) ─────────────────────────────────────────

  _drawRunningHeader() {
    this.doc.setFillColor(...BLUE);
    this.doc.rect(0, 0, PAGE_W, 8, "F");
    this.font("bold", 7, WHITE);
    this.text("ElevateRFP Solutions", MARGIN, 5.5);
    this.font("normal", 7, WHITE);
    this.text("CONFIDENTIAL — ELEVATOR PLATFORM QUOTATION", PAGE_W - MARGIN, 5.5, { align: "right" });
  }

  // ── Footer (all pages) ───────────────────────────────────────────────────

  _drawFooter() {
    const fY = PAGE_H - 10;
    this.doc.setFillColor(...LIGHT);
    this.doc.rect(0, fY - 3, PAGE_W, 13, "F");
    this.line(0, fY - 3, PAGE_W, fY - 3, BORDER, 0.3);
    this.font("normal", 7, GRAY);
    this.text("ElevateRFP Solutions  ·  Sales Department  ·  support@elevaterfp.com", MARGIN, fY + 3);
    this.font("normal", 7, GRAY);
    this.text(`Page ${this.page}`, PAGE_W - MARGIN, fY + 3, { align: "right" });
  }

  // ── autotable wrapper ───────────────────────────────────────────────────

  table(head, body, opts = {}) {
    autoTable(this.doc, {
      startY: this.y,
      head,
      body,
      margin: { left: MARGIN, right: MARGIN },
      styles: {
        fontSize: 8.5,
        cellPadding: { top: 3, bottom: 3, left: 4, right: 4 },
        textColor: DARK,
        lineColor: BORDER,
        lineWidth: 0.2,
      },
      headStyles: {
        fillColor: BLUE,
        textColor: WHITE,
        fontStyle: "bold",
        fontSize: 8,
      },
      alternateRowStyles: { fillColor: LIGHT },
      ...opts,
    });
    this.y = this.doc.lastAutoTable.finalY + 6;
  }

  // ── Bullet list ──────────────────────────────────────────────────────────

  bulletList(items, indent = MARGIN + 4) {
    items.forEach(item => {
      this.needPage(8);
      this.doc.setFillColor(...BLUE);
      this.doc.circle(indent, this.y - 1.2, 1, "F");
      this.font("normal", 8.5, DARK);
      const lines = this.doc.splitTextToSize(String(item), CONTENT_W - 8);
      lines.forEach((line, i) => {
        this.text(line, indent + 4, this.y + i * 4.5);
      });
      this.y += lines.length * 4.5 + 2;
    });
  }

  // ── Checklist row ────────────────────────────────────────────────────────

  checkRow(label, ok = true) {
    this.needPage(7);
    const col = ok ? SUCCESS : GRAY;
    this.doc.setFillColor(...col);
    this.doc.circle(MARGIN + 3, this.y - 1.2, 1.5, "F");
    this.font("normal", 8.5, ok ? DARK : GRAY);
    this.text(label, MARGIN + 8, this.y);
    this.y += 6;
  }

  // ── Status badge ─────────────────────────────────────────────────────────

  badge(label, x, y, color = BLUE) {
    const w = this.doc.getTextWidth(label) + 6;
    this.doc.setFillColor(...color);
    this.doc.roundedRect(x, y - 3.5, w, 5, 1.5, 1.5, "F");
    this.font("bold", 6.5, WHITE);
    this.text(label, x + 3, y);
  }
}

// ══════════════════════════════════════════════════════════════════════════
//  DATA EXTRACTORS
// ══════════════════════════════════════════════════════════════════════════

function getPrimary(result) {
  const recs    = result?.product_matches?.recommendations || {};
  const primary = recs.primary_recommendation || {};
  const meta    = primary.product?.metadata || primary.product || {};
  return { primary, meta, recs };
}

function getPricingBreakdown(result) {
  const pricing    = result?.pricing || {};
  const breakdown  = pricing.pricing_breakdown || {};
  const scenarios  = pricing.pricing_scenarios || {};
  const rec        = scenarios.most_likely || {};
  return { breakdown, scenarios, rec };
}

function getTechItems(result) {
  return result?.risk_assessment?.technical_configuration || [];
}

function getCompliance(result) {
  const c = result?.compliance_results || {};
  return {
    safety:       c.safety_features       || [],
    access:       c.accessibility_features || [],
    energy:       c.energy_efficiency      || [],
    fire:         c.fire_safety            || [],
    standards:    c.standards_compliance   || [],
  };
}

function getProposal(result) {
  return result?.proposal?.sections || {};
}

function getEval(result) {
  return result?.evaluation || {};
}

// ══════════════════════════════════════════════════════════════════════════
//  SECTION RENDERERS
// ══════════════════════════════════════════════════════════════════════════

// ── 01 — Cover Page ───────────────────────────────────────────────────────

function drawCover(b, result) {
  const { meta } = getPrimary(result);
  const projName = result?.requirements?.basic_requirements?.project_name
                || meta.model
                || "Elevator Platform";
  const platformLine = meta.model ? `${meta.model} — ${meta.tier || ""} Tier` : "Recommended Platform";

  // Blue left sidebar
  b.doc.setFillColor(...BLUE);
  b.doc.rect(0, 0, 8, PAGE_H, "F");

  // Top accent bar
  b.doc.setFillColor(...BLUE);
  b.doc.rect(8, 0, PAGE_W, 2, "F");

  // ElevateRFP brand
  b.font("bold", 22, BLUE);
  b.text("ElevateRFP", MARGIN + 8, 32);
  b.font("normal", 11, GRAY);
  b.text("Solutions", MARGIN + 8, 40);

  // Divider
  b.line(MARGIN + 8, 48, MARGIN + 8 + 60, 48, BLUE, 0.8);

  // Main heading
  b.font("bold", 20, DARK);
  b.text("ELEVATOR PLATFORM", MARGIN + 8, 66);
  b.font("bold", 20, BLUE);
  b.text("QUOTATION", MARGIN + 8, 78);

  // Prepared for block
  b.doc.setFillColor(...BLUE_LIGHT);
  b.doc.roundedRect(MARGIN + 8, 92, CONTENT_W - 8, 40, 3, 3, "F");
  b.font("normal", 8, GRAY);
  b.text("PREPARED FOR", MARGIN + 14, 102);
  b.font("bold", 13, DARK);
  const projLines = b.doc.splitTextToSize(projName, CONTENT_W - 20);
  projLines.slice(0, 2).forEach((ln, i) => b.text(ln, MARGIN + 14, 110 + i * 7));

  // Info grid
  const infoY = 145;
  b.doc.setFillColor(...LIGHT);
  b.doc.roundedRect(MARGIN + 8, infoY, CONTENT_W - 8, 54, 3, 3, "F");
  b.line(MARGIN + 8, infoY, MARGIN + 8 + CONTENT_W - 8, infoY, BLUE, 0.5);

  const infoItems = [
    ["Date",       today()],
    ["Reference",  b.ref],
    ["Valid Until", validity()],
    ["Platform",   platformLine],
  ];
  infoItems.forEach(([label, val], i) => {
    const ry = infoY + 10 + i * 11;
    b.font("normal", 8, GRAY);
    b.text(label, MARGIN + 14, ry);
    b.font("bold", 8.5, DARK);
    b.text(safeText(val), MARGIN + 58, ry);
  });

  // Bottom contact card
  b.doc.setFillColor(...BLUE);
  b.doc.rect(MARGIN + 8, 218, CONTENT_W - 8, 40, "F");
  b.font("bold", 9, WHITE);
  b.text("ElevateRFP Solutions", MARGIN + 14, 230);
  b.font("normal", 8, WHITE);
  b.text("Sales Department", MARGIN + 14, 238);
  b.text("support@elevaterfp.com", MARGIN + 14, 246);

  b._drawFooter();
}

// ── 02 — Executive Summary ────────────────────────────────────────────────

function drawExecutiveSummary(b, result) {
  b.newPage();
  b.sectionHeading("Executive Summary", 2);

  const sections = getProposal(result);
  const execSec  = sections["executive_summary"] || sections["Executive Summary"] || {};
  let   text     = execSec.content || "";

  // Fallback from proposal text
  if (!text) {
    const { meta } = getPrimary(result);
    text = `ElevateRFP Solutions is pleased to present this elevator platform quotation. `
         + `Based on our assessment of your project requirements, we recommend the `
         + `${meta.model || "selected platform"} (${meta.tier || ""} tier), `
         + `which provides the optimal balance of performance, safety, and cost efficiency. `
         + `This quotation covers supply, installation, commissioning, and a comprehensive warranty. `
         + `All pricing is in Indian Rupees and is indicative, subject to final site survey.`;
  }

  // Strip markdown if any crept in
  text = text.replace(/[#*_`>]/g, "").replace(/\n{3,}/g, "\n\n").trim();

  const lines = b.doc.splitTextToSize(text, CONTENT_W);
  b.font("normal", 9.5, DARK);
  lines.slice(0, 40).forEach(ln => {
    b.needPage(7);
    b.text(ln, MARGIN, b.y);
    b.y += 5.5;
  });
  b.y += 4;
}

// ── 03 — Recommended Platform ─────────────────────────────────────────────

function drawRecommendedPlatform(b, result) {
  b.sectionHeading("Recommended Platform", 3);

  const { primary, meta } = getPrimary(result);
  const covPct = Math.round((primary.product?.coverage_score || primary.coverage_score || 0) * 100);

  // Platform card
  b.needPage(50);
  b.doc.setFillColor(...BLUE);
  b.doc.roundedRect(MARGIN, b.y, CONTENT_W, 14, 2, 2, "F");
  b.font("bold", 11, WHITE);
  b.text(safeText(meta.model, "Platform Selected"), MARGIN + 6, b.y + 9);
  b.font("normal", 8, WHITE);
  b.text(`${meta.tier || ""} Tier  ·  ${covPct}% Requirements Coverage`, PAGE_W - MARGIN - 6, b.y + 9, { align: "right" });
  b.y += 18;

  // Specs table
  b.table(
    [["Specification", "Value"]],
    [
      ["Model",              safeText(meta.model)],
      ["Platform Tier",      safeText(meta.tier)],
      ["Load Capacity",      meta.capacity_kg ? `${meta.capacity_kg} kg` : "—"],
      ["Maximum Floors",     meta.max_floors  ? `${meta.max_floors} floors` : "—"],
      ["Rated Speed",        meta.speed_ms    ? `${meta.speed_ms} m/s` : "—"],
      ["Requirement Coverage", `${covPct}%`],
    ],
    {
      columnStyles: {
        0: { cellWidth: 65, fontStyle: "bold", fillColor: LIGHT },
        1: { cellWidth: CONTENT_W - 65 },
      },
    }
  );

  // Description
  if (meta.description) {
    b.needPage(16);
    b.font("italic", 8.5, GRAY);
    const descLines = b.doc.splitTextToSize(meta.description, CONTENT_W);
    descLines.slice(0, 6).forEach(ln => { b.text(ln, MARGIN, b.y); b.y += 5; });
    b.y += 3;
  }

  // Use cases
  const useCases = meta.recommended_use_cases || [];
  if (useCases.length > 0) {
    b.needPage(16);
    b.font("bold", 9, DARK);
    b.text("Suitable Applications", MARGIN, b.y); b.y += 6;
    b.bulletList(useCases.slice(0, 6));
  }
  b.y += 4;
}

// ── 04 — Technical Configuration ─────────────────────────────────────────

function drawTechnicalConfiguration(b, result) {
  b.sectionHeading("Technical Configuration", 4);

  const items = getTechItems(result);
  if (items.length === 0) {
    b.font("italic", 8.5, GRAY);
    b.text("Technical configuration not available.", MARGIN, b.y);
    b.y += 10;
    return;
  }

  const GROUPS = [
    { label: "Drive System",      cats: ["drive_system", "electrical"] },
    { label: "Safety Features",   cats: ["safety"] },
    { label: "Accessibility",     cats: ["accessibility", "passenger_interface"] },
    { label: "Monitoring & Control", cats: ["monitoring", "controls"] },
    { label: "Energy Efficiency", cats: ["energy"] },
    { label: "Doors",             cats: ["doors"] },
  ];

  GROUPS.forEach(group => {
    const rows = items.filter(it => group.cats.includes(it.category));
    if (rows.length === 0) return;

    b.needPage(20 + rows.length * 8);

    // Group sub-heading
    b.doc.setFillColor(...BLUE_LIGHT);
    b.doc.rect(MARGIN, b.y, CONTENT_W, 7, "F");
    b.font("bold", 8.5, BLUE);
    b.text(group.label, MARGIN + 4, b.y + 4.8);
    b.y += 10;

    b.table(
      [["Feature", "Value", "Status"]],
      rows.map(it => [
        safeText(it.feature),
        safeText(it.value),
        safeText(it.applicability),
      ]),
      {
        columnStyles: {
          0: { cellWidth: 75 },
          1: { cellWidth: 65 },
          2: { cellWidth: CONTENT_W - 140 },
        },
        styles: { fontSize: 8 },
        headStyles: { fillColor: DARK },
      }
    );
    b.y += 2;
  });
}

// ── 05 — Included Features ───────────────────────────────────────────────

function drawIncludedFeatures(b, result) {
  b.sectionHeading("Included Features", 5);

  const compliance = getCompliance(result);
  const allFeatures = [
    ...compliance.safety,
    ...compliance.access,
    ...compliance.energy,
    ...compliance.fire,
  ];

  const KNOWN = [
    "Automatic Rescue Device (ARD)", "Emergency Alarm", "Overload Sensor",
    "Braille Buttons", "Voice Announcement", "Handrail", "Mirror in Car", "Wheelchair Accessible",
    "Fire Service Mode", "Intercom System", "CCTV Monitoring",
    "IoT Remote Monitoring", "Regenerative Drive", "LED Lighting",
  ];

  // Two-column layout
  const col1 = [], col2 = [];
  KNOWN.forEach((name, i) => {
    const found  = allFeatures.find(f => (f.feature || "").toLowerCase().includes(name.toLowerCase().split(" ")[0]));
    const status = found?.status || "—";
    const ok     = status === "Compliant" || status === "Recommended";
    const row    = { name, ok };
    if (i % 2 === 0) col1.push(row); else col2.push(row);
  });

  const maxLen = Math.max(col1.length, col2.length);
  b.needPage(maxLen * 7 + 10);

  for (let i = 0; i < maxLen; i++) {
    const r1 = col1[i], r2 = col2[i];
    b.needPage(7);

    if (r1) {
      const col = r1.ok ? SUCCESS : GRAY;
      b.doc.setFillColor(...col);
      b.doc.circle(MARGIN + 3, b.y - 1.2, 1.5, "F");
      b.font("normal", 8.5, r1.ok ? DARK : GRAY);
      b.text(r1.name, MARGIN + 8, b.y);
    }
    if (r2) {
      const col = r2.ok ? SUCCESS : GRAY;
      const cx  = MARGIN + CONTENT_W / 2 + 3;
      b.doc.setFillColor(...col);
      b.doc.circle(cx, b.y - 1.2, 1.5, "F");
      b.font("normal", 8.5, r2.ok ? DARK : GRAY);
      b.text(r2.name, cx + 5, b.y);
    }
    b.y += 6.5;
  }
  b.y += 6;
}

// ── 06 — Pricing Summary ─────────────────────────────────────────────────

function drawPricing(b, result) {
  b.sectionHeading("Pricing Summary", 6);

  const { breakdown, rec } = getPricingBreakdown(result);

  // Recommended scenario highlight
  if (rec.total_price) {
    b.needPage(20);
    b.doc.setFillColor(...BLUE);
    b.doc.roundedRect(MARGIN, b.y, CONTENT_W, 16, 2, 2, "F");
    b.font("normal", 8, WHITE);
    b.text("Recommended Scenario — Total Quotation Value", MARGIN + 6, b.y + 6);
    b.font("bold", 14, WHITE);
    b.text(formatINR(rec.total_price), MARGIN + 6, b.y + 13);
    b.y += 22;
  }

  // Line items
  const components = breakdown.components || {};
  const LABELS = {
    base_product_cost:  "Platform Cost",
    installation_cost:  "Installation & Commissioning",
    customization_cost: "Optional Features & Customisation",
    compliance_cost:    "Logistics & Handling",
    risk_adjustment:    "Contingency Margin",
  };

  const rows = Object.entries(components)
    .filter(([, v]) => v > 0)
    .map(([key, val]) => [LABELS[key] || key.replace(/_/g, " "), formatINR(val)]);

  if (breakdown.tax_amount > 0) {
    rows.push([`GST (${breakdown.tax_rate ? `${(breakdown.tax_rate * 100).toFixed(0)}%` : "18%"})`, formatINR(breakdown.tax_amount)]);
  }

  if (rows.length > 0) {
    b.table(
      [["Description", "Amount (INR)"]],
      rows,
      {
        columnStyles: {
          0: { cellWidth: CONTENT_W - 50 },
          1: { cellWidth: 50, halign: "right", fontStyle: "bold" },
        },
        foot: [[{ content: "Total Quotation Value (Inclusive of GST)", styles: { fontStyle: "bold", fillColor: DARK, textColor: WHITE } }, { content: formatINR(breakdown.total_price || rec.total_price), styles: { fontStyle: "bold", halign: "right", fillColor: DARK, textColor: WHITE } }]],
        showFoot: "lastPage",
      }
    );
  }

  b.needPage(16);
  b.font("italic", 7.5, GRAY);
  b.text("All amounts in Indian Rupees (INR). Indicative estimate — subject to site survey and detailed engineering.", MARGIN, b.y);
  b.y += 8;
}

// ── 07 — Delivery Schedule ───────────────────────────────────────────────

function drawDelivery(b, result) {
  b.sectionHeading("Delivery Schedule", 7);

  const sections = getProposal(result);
  const sec      = sections["implementation_plan"] || sections["Delivery Schedule"] || {};
  const text     = sec.content || "";

  if (text) {
    const cleaned = text.replace(/[#*_`>]/g, "").trim();
    const rows    = cleaned.split("\n").filter(l => l.trim()).slice(0, 12).map(l => [l.trim()]);
    if (rows.length > 0) {
      b.table([["Schedule"]], rows, { columnStyles: { 0: { cellWidth: CONTENT_W } } });
      return;
    }
  }

  // Fallback standard schedule
  b.table(
    [["Phase", "Activity", "Timeline"]],
    [
      ["1", "Order Confirmation & Design Finalisation", "Week 1–2"],
      ["2", "Procurement & Manufacturing",              "Week 3–8"],
      ["3", "Delivery to Site",                         "Week 9–10"],
      ["4", "Installation & Civil Interface",           "Week 11–14"],
      ["5", "Testing, Commissioning & Handover",        "Week 15–16"],
    ],
    {
      columnStyles: {
        0: { cellWidth: 12, halign: "center" },
        1: { cellWidth: CONTENT_W - 62 },
        2: { cellWidth: 50, halign: "right" },
      },
    }
  );
}

// ── 08 — Warranty ───────────────────────────────────────────────────────

function drawWarranty(b, result) {
  b.sectionHeading("Warranty", 8);

  const sections = getProposal(result);
  const sec      = sections["warranty"] || {};
  const text     = (sec.content || "").replace(/[#*_`>]/g, "").trim();

  if (text) {
    const lines = b.doc.splitTextToSize(text, CONTENT_W);
    b.font("normal", 8.5, DARK);
    lines.slice(0, 30).forEach(ln => { b.needPage(7); b.text(ln, MARGIN, b.y); b.y += 5.5; });
    b.y += 4;
    return;
  }

  b.table(
    [["Item", "Coverage"]],
    [
      ["Warranty Period",        "24 months from date of commissioning"],
      ["Coverage",               "All manufacturing defects, electrical components, control systems"],
      ["Labour",                 "Included during warranty period"],
      ["Response Time",          "Within 24 hours for critical failures"],
      ["Spare Parts",            "Genuine OEM parts guaranteed"],
    ],
    { columnStyles: { 0: { cellWidth: 55, fontStyle: "bold", fillColor: LIGHT }, 1: { cellWidth: CONTENT_W - 55 } } }
  );
}

// ── 09 — Annual Maintenance ──────────────────────────────────────────────

function drawAMC(b, result) {
  b.sectionHeading("Annual Maintenance Contract (AMC)", 9);

  const sections = getProposal(result);
  const sec      = sections["amc"] || {};
  const text     = (sec.content || "").replace(/[#*_`>]/g, "").trim();

  if (text) {
    const lines = b.doc.splitTextToSize(text, CONTENT_W);
    b.font("normal", 8.5, DARK);
    lines.slice(0, 30).forEach(ln => { b.needPage(7); b.text(ln, MARGIN, b.y); b.y += 5.5; });
    b.y += 4;
    return;
  }

  b.table(
    [["Service", "Details"]],
    [
      ["Preventive Maintenance",  "Monthly inspection and lubrication"],
      ["Breakdown Calls",         "Unlimited, 24 × 7 × 365"],
      ["Response Time",           "Within 4 hours"],
      ["Spare Parts",             "Consumables included; major components at cost"],
      ["AMC Commencement",        "After warranty expiry"],
    ],
    { columnStyles: { 0: { cellWidth: 60, fontStyle: "bold", fillColor: LIGHT }, 1: { cellWidth: CONTENT_W - 60 } } }
  );
}

// ── 10 — Payment Terms ───────────────────────────────────────────────────

function drawPaymentTerms(b) {
  b.sectionHeading("Payment Terms", 10);

  b.table(
    [["Milestone", "Percentage", "Trigger"]],
    [
      ["Advance Payment",            "30%", "On order confirmation and contract signing"],
      ["Progress Payment",           "60%", "On delivery of equipment to site"],
      ["Final Payment",              "10%", "On commissioning and handover"],
    ],
    {
      columnStyles: {
        0: { cellWidth: 55, fontStyle: "bold" },
        1: { cellWidth: 28, halign: "center", fontStyle: "bold" },
        2: { cellWidth: CONTENT_W - 83 },
      },
    }
  );

  b.needPage(12);
  b.font("italic", 7.5, GRAY);
  b.text("All payments by cheque / NEFT / RTGS in favour of ElevateRFP Solutions. GST applicable as per prevailing rates.", MARGIN, b.y);
  b.y += 8;
}

// ── 11 — Engineering Exclusions ─────────────────────────────────────────

function drawExclusions(b, result) {
  b.sectionHeading("Engineering Exclusions", 11);

  const sections  = getProposal(result);
  const sec       = sections["engineering_exclusions"] || {};
  const text      = (sec.content || "").replace(/[#*_`>]/g, "").trim();

  let items = [];
  if (text) {
    items = text.split("\n").map(l => l.replace(/^[-•*]\s*/, "").trim()).filter(Boolean).slice(0, 16);
  }

  if (items.length === 0) {
    items = [
      "Civil construction: shaft, pit, machine room, headroom, and structural modifications",
      "Electrical supply upgrades, dedicated feeder lines, and DB panels beyond elevator board",
      "Building permits, statutory approvals, and government inspection fees",
      "False ceiling, flooring, and interior decoration at each landing",
      "Hoistway lighting and permanent lighting fixtures in the pit and overhead",
      "Any structural steel or concrete work required for equipment support",
    ];
  }

  b.bulletList(items);
}

// ── 12 — Standards & Safety ──────────────────────────────────────────────

function drawStandards(b, result) {
  b.sectionHeading("Standards & Safety", 12);

  const { standards } = getCompliance(result);

  const FALLBACK = [
    { standard_name: "IS 14665",    status: "Compliant",    reference: "Indian Standard for Electric Passenger and Goods Lifts" },
    { standard_name: "IS 15785",    status: "Compliant",    reference: "Indian Standard for Safety of Lifts" },
    { standard_name: "EN 81-20/50", status: "Recommended",  reference: "European Safety Standard for Lifts" },
    { standard_name: "ASME A17.1",  status: "Recommended",  reference: "Safety Code for Elevators and Escalators" },
    { standard_name: "ISO 25745",   status: "Compliant",    reference: "Energy Performance of Lifts" },
  ];

  const rows = (standards.length > 0 ? standards : FALLBACK).map(s => [
    safeText(s.standard_name),
    safeText(s.status),
    safeText(s.rationale || s.reference || "—"),
  ]);

  b.table(
    [["Standard", "Status", "Scope"]],
    rows,
    {
      columnStyles: {
        0: { cellWidth: 32, fontStyle: "bold" },
        1: { cellWidth: 28, halign: "center" },
        2: { cellWidth: CONTENT_W - 60 },
      },
      bodyStyles: {},
      didParseCell: function(data) {
        if (data.column.index === 1) {
          const val = data.cell.raw;
          if (val === "Compliant")   data.cell.styles.textColor = SUCCESS;
          if (val === "Recommended") data.cell.styles.textColor = WARNING;
        }
      },
    }
  );

  b.needPage(16);
  b.font("italic", 7.5, GRAY);
  b.text(
    '"Designed in accordance with" indicates the product meets the cited standard\'s design requirements. ' +
    '"Recommended under" indicates the standard is applicable and the product follows its guidance. ' +
    'Statutory certification requires inspection by a registered authority.',
    MARGIN, b.y, { maxWidth: CONTENT_W }
  );
  b.y += 14;
}

// ── 13 — Final Evaluation ────────────────────────────────────────────────

function drawFinalEvaluation(b, result) {
  b.sectionHeading("Final Evaluation", 13);

  const ev        = getEval(result);
  const grade     = ev.grade || "—";
  const winProb   = ev.win_probability || {};
  const probStr   = winProb.percentage || (winProb.probability ? `${Math.round(winProb.probability * 100)}%` : "—");
  const weighted  = Math.round(ev.weighted_score || 0);
  const strengths = ev.strengths      || [];
  const gaps      = ev.critical_gaps  || [];
  const scores    = ev.dimension_scores || {};

  const GRADE_DESC = {
    A: "Excellent Proposal — Strong competitive position",
    B: "Strong Proposal — Well-suited to requirements",
    C: "Moderate Proposal — Improvements recommended",
    D: "Needs Improvement — Review critical areas",
  };

  const DIM_LABELS = {
    requirement_coverage:    "Requirement Coverage",
    standards_compliance:    "Standards Compliance",
    technical_completeness:  "Technical Completeness",
    proposal_completeness:   "Proposal Completeness",
    pricing_competitiveness: "Pricing Competitiveness",
  };

  // Grade + win prob header card
  b.needPage(30);
  b.doc.setFillColor(...BLUE_LIGHT);
  b.doc.roundedRect(MARGIN, b.y, CONTENT_W, 24, 2, 2, "F");

  // Grade box
  b.doc.setFillColor(...gradeColor(grade));
  b.doc.roundedRect(MARGIN + 4, b.y + 4, 22, 16, 2, 2, "F");
  b.font("bold", 16, WHITE);
  b.text(safeText(grade), MARGIN + 4 + 11, b.y + 14.5, { align: "center" });

  b.font("bold", 9.5, DARK);
  b.text(GRADE_DESC[grade] || "Evaluation complete", MARGIN + 30, b.y + 9);
  if (weighted > 0) {
    b.font("normal", 8, GRAY);
    b.text(`Overall score: ${weighted}/100`, MARGIN + 30, b.y + 15.5);
  }

  // Win probability
  b.font("normal", 7.5, GRAY);
  b.text("Estimated Win Probability", PAGE_W - MARGIN - 36, b.y + 9, { align: "center" });
  b.font("bold", 13, SUCCESS);
  b.text(safeText(probStr), PAGE_W - MARGIN - 36, b.y + 18, { align: "center" });
  b.y += 30;

  // Dimension scores table
  if (Object.keys(scores).length > 0) {
    const dimRows = Object.entries(scores).map(([dim, info]) => {
      const pct = Math.round((info.score || 0) * 100);
      return [DIM_LABELS[dim] || dim.replace(/_/g, " "), `${pct} / 100`, info.weight ? `${Math.round(info.weight * 100)}%` : "—"];
    });
    b.table(
      [["Evaluation Dimension", "Score", "Weight"]],
      dimRows,
      {
        columnStyles: {
          0: { cellWidth: CONTENT_W - 50 },
          1: { cellWidth: 25, halign: "center", fontStyle: "bold" },
          2: { cellWidth: 25, halign: "center" },
        },
      }
    );
  }

  // Strengths
  if (strengths.length > 0) {
    b.needPage(14 + strengths.length * 6);
    b.font("bold", 9, DARK);
    b.text("Strengths", MARGIN, b.y); b.y += 6;
    strengths.slice(0, 6).forEach(s => {
      b.doc.setFillColor(...SUCCESS);
      b.doc.circle(MARGIN + 3, b.y - 1.2, 1.5, "F");
      b.font("normal", 8.5, DARK);
      b.text(String(s), MARGIN + 8, b.y); b.y += 6;
    });
    b.y += 4;
  }

  // Improvement areas
  if (gaps.length > 0) {
    b.needPage(14 + gaps.length * 6);
    b.font("bold", 9, DARK);
    b.text("Improvement Areas", MARGIN, b.y); b.y += 6;
    gaps.slice(0, 6).forEach(g => {
      const label = typeof g === "string" ? g : g.description || g.gap || "";
      b.doc.setFillColor(...WARNING);
      b.doc.circle(MARGIN + 3, b.y - 1.2, 1.5, "F");
      b.font("normal", 8.5, DARK);
      b.text(String(label), MARGIN + 8, b.y); b.y += 6;
    });
    b.y += 4;
  }
}

// ── 14 — Contact Information ─────────────────────────────────────────────

function drawContact(b) {
  b.sectionHeading("Contact Information", 14);

  b.needPage(36);
  b.doc.setFillColor(...BLUE);
  b.doc.roundedRect(MARGIN, b.y, CONTENT_W, 32, 3, 3, "F");
  b.font("bold", 12, WHITE);
  b.text("ElevateRFP Solutions", MARGIN + 8, b.y + 10);
  b.font("normal", 9, WHITE);
  b.text("Sales Department", MARGIN + 8, b.y + 18);
  b.text("support@elevaterfp.com", MARGIN + 8, b.y + 25);
  b.font("normal", 8, WHITE);
  b.text("This quotation is valid for 30 days from the date of issue.", PAGE_W - MARGIN - 8, b.y + 18, { align: "right" });
  b.text(`Reference: ${b.ref}`, PAGE_W - MARGIN - 8, b.y + 25, { align: "right" });
  b.y += 40;
}

// ══════════════════════════════════════════════════════════════════════════
//  MAIN EXPORT FUNCTION
// ══════════════════════════════════════════════════════════════════════════

export function generateProposalPDF(result) {
  const b = new PDFBuilder();

  // ── Page 1: Cover ──────────────────────────────────────────────────────
  drawCover(b, result);

  // ── Page 2+: Content sections ─────────────────────────────────────────
  drawExecutiveSummary(b, result);
  drawRecommendedPlatform(b, result);
  drawTechnicalConfiguration(b, result);
  drawIncludedFeatures(b, result);
  drawPricing(b, result);
  drawDelivery(b, result);
  drawWarranty(b, result);
  drawAMC(b, result);
  drawPaymentTerms(b);
  drawExclusions(b, result);
  drawStandards(b, result);
  drawFinalEvaluation(b, result);
  drawContact(b);

  // ── Build filename ─────────────────────────────────────────────────────
  const { meta } = getPrimary(result);
  const slug = (meta.model || "ElevateRFP_Proposal")
    .replace(/\s+/g, "_")
    .replace(/[^a-zA-Z0-9_-]/g, "");

  const dateStr = new Date().toISOString().slice(0, 10);
  const filename = `${slug}_Quotation_${dateStr}.pdf`;

  b.doc.save(filename);
}
