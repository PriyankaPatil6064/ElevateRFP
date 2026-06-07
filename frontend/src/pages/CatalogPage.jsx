// pages/CatalogPage.jsx
// Platform catalog — table layout grouped by tier. No cards, no $ prices, no e-commerce.
// Data sourced from backend config.py PRODUCTS list (INR prices, real ranges).

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";

// All prices from config.py starting_price (already INR)
const PRODUCTS = [
  // Basic
  {
    id: "ELV-100", name: "ElevateBasic 100", tier: "Basic",
    buildingTypes: ["Residential", "Commercial"],
    capacity: { min: 408,  max: 630  }, floors: { min: 2,  max: 10  }, speed: { min: 0.5, max: 1.0  },
    startingPrice: 2000000,
    useCases: ["Low-rise residential apartments (G+4 to G+10)", "Small office buildings", "Retail showrooms"],
  },
  {
    id: "ELV-110", name: "ElevateBasic 110", tier: "Basic",
    buildingTypes: ["Residential", "Commercial", "Retail"],
    capacity: { min: 544,  max: 800  }, floors: { min: 2,  max: 12  }, speed: { min: 0.6, max: 1.2  },
    startingPrice: 2500000,
    useCases: ["Residential apartments up to 12 floors", "Neighbourhood commercial centres", "Community health clinics"],
  },
  // Mid
  {
    id: "ELV-200", name: "ElevateMid 200", tier: "Mid",
    buildingTypes: ["Residential", "Commercial", "Office"],
    capacity: { min: 680,  max: 1000 }, floors: { min: 5,  max: 20  }, speed: { min: 1.0, max: 1.6  },
    startingPrice: 3800000,
    useCases: ["Mid-rise residential societies", "Small to medium commercial offices", "Mixed retail-office buildings"],
  },
  {
    id: "ELV-210", name: "ElevateMid 210", tier: "Mid",
    buildingTypes: ["Residential", "Commercial", "Hotel", "Office"],
    capacity: { min: 800,  max: 1150 }, floors: { min: 5,  max: 25  }, speed: { min: 1.0, max: 1.75 },
    startingPrice: 4300000,
    useCases: ["Premium residential towers up to 25 floors", "Business hotels", "Corporate office campuses"],
  },
  {
    id: "ELV-220", name: "ElevateMid 220", tier: "Mid",
    buildingTypes: ["Residential", "Commercial", "Hotel", "Office"],
    capacity: { min: 800,  max: 1250 }, floors: { min: 5,  max: 28  }, speed: { min: 1.0, max: 2.0  },
    startingPrice: 4800000,
    useCases: ["Mid-rise residential complexes", "Commercial office towers up to 28 floors", "Hotels and hospitality buildings"],
  },
  // High
  {
    id: "ELV-300", name: "ElevateHigh 300", tier: "High",
    buildingTypes: ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use"],
    capacity: { min: 1000, max: 1600 }, floors: { min: 15, max: 40  }, speed: { min: 1.5, max: 2.5  },
    startingPrice: 6200000,
    useCases: ["Corporate office towers", "Large commercial buildings", "Hospitals requiring high-capacity lifts", "Luxury hotels"],
  },
  {
    id: "ELV-310", name: "ElevateHigh 310", tier: "High",
    buildingTypes: ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use"],
    capacity: { min: 1200, max: 1800 }, floors: { min: 20, max: 45  }, speed: { min: 2.0, max: 3.0  },
    startingPrice: 7000000,
    useCases: ["Premium corporate headquarters", "Multi-speciality hospitals", "Convention and exhibition centres"],
  },
  {
    id: "ELV-320", name: "ElevateHigh 320", tier: "High",
    buildingTypes: ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use", "Government"],
    capacity: { min: 1360, max: 2000 }, floors: { min: 25, max: 50  }, speed: { min: 2.0, max: 3.5  },
    startingPrice: 7800000,
    useCases: ["Landmark commercial towers", "Flagship hospital campuses", "Government high-rise complexes"],
  },
  // Super
  {
    id: "ELV-400", name: "ElevateSuper 400", tier: "Super",
    buildingTypes: ["Commercial", "Office", "Mixed-Use", "Government", "Airport"],
    capacity: { min: 1600, max: 2200 }, floors: { min: 30, max: 60  }, speed: { min: 2.5, max: 4.0  },
    startingPrice: 10000000,
    useCases: ["Major corporate towers (30–60 floors)", "International airport terminals", "Government landmark buildings"],
  },
  {
    id: "ELV-410", name: "ElevateSuper 410", tier: "Super",
    buildingTypes: ["Commercial", "Office", "Mixed-Use", "Transit", "Airport"],
    capacity: { min: 1800, max: 2500 }, floors: { min: 35, max: 70  }, speed: { min: 3.0, max: 4.5  },
    startingPrice: 11200000,
    useCases: ["Premium corporate headquarters (35–70 floors)", "Metro and transit hubs", "International convention centres"],
  },
  {
    id: "ELV-420", name: "ElevateSuper 420", tier: "Super",
    buildingTypes: ["Commercial", "Office", "Mixed-Use"],
    capacity: { min: 2000, max: 2800 }, floors: { min: 40, max: 80  }, speed: { min: 3.5, max: 5.0  },
    startingPrice: 12500000,
    useCases: ["Premium commercial skyscrapers (40–80 floors)", "Iconic mixed-use towers", "Financial district landmark buildings"],
  },
  // Ultra
  {
    id: "ELV-500", name: "ElevateUltra 500", tier: "Ultra",
    buildingTypes: ["Commercial", "Office", "Mixed-Use"],
    capacity: { min: 2000, max: 3000 }, floors: { min: 50, max: 100 }, speed: { min: 4.0, max: 6.0  },
    startingPrice: 16500000,
    useCases: ["Skyscrapers (50–100 floors)", "Iconic city-centre towers", "Ultra-luxury mixed-use developments"],
  },
  {
    id: "ELV-510", name: "ElevateUltra 510", tier: "Ultra",
    buildingTypes: ["Commercial", "Office", "Mixed-Use"],
    capacity: { min: 2500, max: 3500 }, floors: { min: 60, max: 120 }, speed: { min: 5.0, max: 7.0  },
    startingPrice: 20000000,
    useCases: ["Super-tall commercial towers (60–120 floors)", "Express shuttle zones in mega-complexes"],
  },
  {
    id: "ELV-520", name: "ElevateUltra 520", tier: "Ultra",
    buildingTypes: ["Commercial", "Office", "Mixed-Use"],
    capacity: { min: 3000, max: 4000 }, floors: { min: 80, max: 150 }, speed: { min: 6.0, max: 8.0  },
    startingPrice: 25000000,
    useCases: ["Mega-tall skyscrapers (80–150 floors)", "World-class observation tower lifts"],
  },
  // Specialized
  {
    id: "ELV-FRT1", name: "ElevateFreight X", tier: "Specialized",
    buildingTypes: ["Industrial", "Commercial", "Warehouse"],
    capacity: { min: 2000, max: 5000 }, floors: { min: 2,  max: 30  }, speed: { min: 0.5, max: 1.0  },
    startingPrice: 15000000,
    useCases: ["Warehouses and distribution centres", "Manufacturing plants", "Logistics and fulfilment centres"],
  },
  {
    id: "ELV-HSP1", name: "ElevateHyperLift", tier: "Specialized",
    buildingTypes: ["Commercial", "Office", "Mixed-Use", "Transit"],
    capacity: { min: 1600, max: 2000 }, floors: { min: 50, max: 200 }, speed: { min: 6.0, max: 10.0 },
    startingPrice: 41500000,
    useCases: ["Observation tower express lifts", "Mega-tall express shuttle zones", "Record-breaking supertall installations"],
  },
];

const TIERS = ["All", "Basic", "Mid", "High", "Super", "Ultra", "Specialized"];

function formatINR(amount) {
  return `₹${Number(amount).toLocaleString("en-IN")}`;
}

function range(r) {
  return `${r.min} – ${r.max}`;
}

function TierSection({ tier, products }) {
  const [expanded, setExpanded] = useState({});

  function toggle(id) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <div className="cat-tier-group">
      <div className="cat-tier-label">{tier}</div>
      <table className="cat-table">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Building Types</th>
            <th>Capacity (kg)</th>
            <th>Floors</th>
            <th>Speed (m/s)</th>
            <th>Starting Price</th>
            <th style={{ width: 28 }} />
          </tr>
        </thead>
        <tbody>
          {products.map(p => (
            <>
              <tr key={p.id} className="cat-row" onClick={() => toggle(p.id)}>
                <td>
                  <div className="cat-platform-name">{p.name}</div>
                  <div className="cat-platform-id">{p.id}</div>
                </td>
                <td className="cat-building-types">
                  {p.buildingTypes.join(", ")}
                </td>
                <td>{range(p.capacity)}</td>
                <td>{range(p.floors)}</td>
                <td>{range(p.speed)}</td>
                <td className="cat-price">{formatINR(p.startingPrice)}</td>
                <td>
                  <button className="cat-expand-btn" onClick={e => { e.stopPropagation(); toggle(p.id); }}>
                    {expanded[p.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </td>
              </tr>
              {expanded[p.id] && (
                <tr key={`${p.id}-exp`} className="cat-expanded-row">
                  <td colSpan={7}>
                    <div className="cat-use-cases">
                      <span className="cat-use-cases-label">Suitable for:</span>
                      {p.useCases.map((u, i) => (
                        <span key={i} className="cat-use-case-chip">{u}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CatalogPage() {
  const [activeTier, setActiveTier] = useState("All");

  const displayed = TIERS.slice(1).filter(
    t => activeTier === "All" || activeTier === t
  );

  const countFor = t =>
    t === "All"
      ? PRODUCTS.length
      : PRODUCTS.filter(p => p.tier === t).length;

  return (
    <div className="cat-page">
      <div className="cat-page-header">
        <h1 className="cat-page-title">Platform Catalog</h1>
        <p className="cat-page-sub">
          {PRODUCTS.length} elevator platforms across 6 tiers — from low-rise residential
          to ultra-high-rise skyscrapers. The system selects from this catalog based on
          your RFP requirements.
        </p>
      </div>

      {/* Tier filter pills */}
      <div className="cat-filters">
        {TIERS.map(t => (
          <button
            key={t}
            className={`cat-filter-btn ${activeTier === t ? "active" : ""}`}
            onClick={() => setActiveTier(t)}
          >
            {t}
            <span className="cat-filter-count">{countFor(t)}</span>
          </button>
        ))}
      </div>

      {/* Tier-grouped tables */}
      <div className="cat-body">
        {displayed.map(tier => (
          <TierSection
            key={tier}
            tier={tier}
            products={PRODUCTS.filter(p => p.tier === tier)}
          />
        ))}
      </div>

      {/* Footnote */}
      <div className="cat-footnote">
        <Info size={13} style={{ flexShrink: 0, color: "var(--accent)" }} />
        <span>
          Starting prices are indicative. Final quotation is calculated per RFP requirements and
          includes installation, customisation, and applicable taxes.
          All amounts in Indian Rupees (INR).
        </span>
      </div>
    </div>
  );
}
