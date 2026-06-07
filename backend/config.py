from typing import Optional
# LLM Configuration
LLM_PROVIDER: str = "openai"  # openai, anthropic, local, gemini

OPENAI_API_KEY: Optional[str] = None
ANTHROPIC_API_KEY: Optional[str] = None
GEMINI_API_KEY: Optional[str] = None

LLM_MODEL: str = "gpt-4-turbo-preview"
LLM_TEMPERATURE: float = 0.1
LLM_MAX_TOKENS: int = 4000

# config.py – Central configuration for ElevateRFP backend

# ── Pricing constants (INR) ──────────────────────────────────────────────
INSTALL_RATE_PER_FLOOR = 65000   # INR per floor
LOGISTICS_COST         = 400000  # flat INR
PROFIT_MARGIN          = 0.15    # 15 %

# Minimum number of elevator-domain keywords required to accept a document
MIN_DOMAIN_KEYWORDS = 1

# Keywords that indicate a document is elevator/building related
DOMAIN_KEYWORDS = [
    "elevator", "lift", "floor", "floors", "storey", "stories", "levels",
    "capacity", "kg", "kilogram", "speed", "m/s", "hoistway", "shaft",
    "building", "construction", "rfp", "proposal", "tender", "specification",
    "passenger", "freight", "hydraulic", "traction", "machine room",
]

# ══════════════════════════════════════════════════════════════════════════
#  ELEVATOR PLATFORM CATALOG
# ══════════════════════════════════════════════════════════════════════════
#
#  Each entry represents a configurable **platform**, not a fixed elevator.
#  Engineering specifications (machine room, power supply, door type, ARD,
#  guide rails, pit depth, shaft size, control system, motor type, etc.)
#  are NOT stored here — they are derived later by the Technical
#  Configuration Agent after product selection.
#
#  Philosophy:
#      Customer requirements  →  Platform selection (this catalog)
#      →  Technical configuration  →  Pricing  →  Proposal
#
#  Backward-compatible shim keys (capacity, max_floors, speed, base_price)
#  are included so existing downstream agents continue to work unchanged.
# ══════════════════════════════════════════════════════════════════════════

PRODUCTS = [

    # ─────────────────────────────────────────────────────────────────────
    #  BASIC TIER — Low-rise residential & small commercial
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-100",
        "name": "ElevateBasic 100",
        "tier": "Basic",
        "description": (
            "Entry-level low-rise platform for residential apartments "
            "and small commercial buildings"
        ),
        "supported_building_types": ["Residential", "Commercial"],
        "supported_lift_types":     ["Passenger", "Hydraulic", "MRL"],
        "recommended_capacity_range": {"min": 408,  "max": 630},
        "recommended_floor_range":    {"min": 2,    "max": 10},
        "recommended_speed_range":    {"min": 0.5,  "max": 1.0},
        "starting_price":  2000000,
        "maximum_price":   3200000,
        "energy_efficiency_class": "B",
        "recommended_use_cases": [
            "Low-rise residential apartments (G+4 to G+10)",
            "Small office buildings",
            "Retail showrooms",
        ],
        "premium_features_available": [
            "ARD (Automatic Rescue Device)",
            "Braille Buttons",
            "LED Lighting",
            "Stainless Steel Finish",
        ],
        # Backward-compatible shim keys
        "capacity": 630, "max_floors": 10, "speed": 1.0, "base_price": 2000000,
    },

    {
        "id":   "ELV-110",
        "name": "ElevateBasic 110",
        "tier": "Basic",
        "description": (
            "Enhanced low-rise platform with higher capacity, ideal for "
            "mid-density residential and neighbourhood commercial"
        ),
        "supported_building_types": ["Residential", "Commercial", "Retail"],
        "supported_lift_types":     ["Passenger", "Hydraulic", "MRL"],
        "recommended_capacity_range": {"min": 544,  "max": 800},
        "recommended_floor_range":    {"min": 2,    "max": 12},
        "recommended_speed_range":    {"min": 0.6,  "max": 1.2},
        "starting_price":  2500000,
        "maximum_price":   3800000,
        "energy_efficiency_class": "B",
        "recommended_use_cases": [
            "Residential apartments up to 12 floors",
            "Neighbourhood commercial centres",
            "Community health clinics",
        ],
        "premium_features_available": [
            "ARD (Automatic Rescue Device)",
            "Braille Buttons",
            "LED Lighting",
            "Stainless Steel Finish",
            "Intercom System",
        ],
        # Backward-compatible shim keys
        "capacity": 800, "max_floors": 12, "speed": 1.2, "base_price": 2500000,
    },

    # ─────────────────────────────────────────────────────────────────────
    #  MID TIER — Mid-rise residential, commercial & hospitality
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-200",
        "name": "ElevateMid 200",
        "tier": "Mid",
        "description": (
            "Mid-rise platform for residential complexes and "
            "commercial office buildings"
        ),
        "supported_building_types": ["Residential", "Commercial", "Office"],
        "supported_lift_types":     ["Passenger", "MRL", "Traction"],
        "recommended_capacity_range": {"min": 680,  "max": 1000},
        "recommended_floor_range":    {"min": 5,    "max": 20},
        "recommended_speed_range":    {"min": 1.0,  "max": 1.6},
        "starting_price":  3800000,
        "maximum_price":   5500000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Mid-rise residential societies",
            "Small to medium commercial offices",
            "Mixed retail-office buildings",
        ],
        "premium_features_available": [
            "ARD (Automatic Rescue Device)",
            "Voice Announcement",
            "Touchless Controls",
            "IoT Monitoring",
            "CCTV Integration",
            "Braille Buttons",
            "LED Lighting",
        ],
        # Backward-compatible shim keys
        "capacity": 1000, "max_floors": 20, "speed": 1.6, "base_price": 3800000,
    },

    {
        "id":   "ELV-210",
        "name": "ElevateMid 210",
        "tier": "Mid",
        "description": (
            "Advanced mid-rise platform with extended floor range, "
            "suited for hotels and larger commercial spaces"
        ),
        "supported_building_types": ["Residential", "Commercial", "Hotel", "Office"],
        "supported_lift_types":     ["Passenger", "MRL", "Traction"],
        "recommended_capacity_range": {"min": 800,  "max": 1150},
        "recommended_floor_range":    {"min": 5,    "max": 25},
        "recommended_speed_range":    {"min": 1.0,  "max": 1.75},
        "starting_price":  4300000,
        "maximum_price":   6500000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Premium residential towers up to 25 floors",
            "Business hotels",
            "Corporate office campuses",
        ],
        "premium_features_available": [
            "Destination Control",
            "ARD (Automatic Rescue Device)",
            "Voice Announcement",
            "Touchless Controls",
            "IoT Monitoring",
            "CCTV Integration",
            "Braille Buttons",
            "LED Lighting",
        ],
        # Backward-compatible shim keys
        "capacity": 1150, "max_floors": 25, "speed": 1.75, "base_price": 4300000,
    },

    {
        "id":   "ELV-220",
        "name": "ElevateMid 220",
        "tier": "Mid",
        "description": (
            "Versatile mid-rise platform for commercial offices, "
            "hotels and residential complexes up to 28 floors"
        ),
        "supported_building_types": ["Residential", "Commercial", "Hotel", "Office"],
        "supported_lift_types":     ["Passenger", "MRL", "Traction"],
        "recommended_capacity_range": {"min": 800,  "max": 1250},
        "recommended_floor_range":    {"min": 5,    "max": 28},
        "recommended_speed_range":    {"min": 1.0,  "max": 2.0},
        "starting_price":  4800000,
        "maximum_price":   7500000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Mid-rise residential complexes",
            "Commercial office towers up to 28 floors",
            "Hotels and hospitality buildings",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Braille Buttons",
        ],
        # Backward-compatible shim keys
        "capacity": 1250, "max_floors": 28, "speed": 2.0, "base_price": 4800000,
    },

    # ─────────────────────────────────────────────────────────────────────
    #  HIGH TIER — High-rise corporate, hospital & mixed-use
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-300",
        "name": "ElevateHigh 300",
        "tier": "High",
        "description": (
            "High-performance platform for corporate towers, "
            "hospitals and large commercial buildings"
        ),
        "supported_building_types": ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Traction", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1000, "max": 1600},
        "recommended_floor_range":    {"min": 15,   "max": 40},
        "recommended_speed_range":    {"min": 1.5,  "max": 2.5},
        "starting_price":  6200000,
        "maximum_price":   9500000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Corporate office towers",
            "Large commercial buildings",
            "Hospitals requiring high-capacity lifts",
            "Luxury hotels",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Braille Buttons",
            "Car Fan with False Ceiling",
        ],
        # Backward-compatible shim keys
        "capacity": 1600, "max_floors": 40, "speed": 2.5, "base_price": 6200000,
    },

    {
        "id":   "ELV-310",
        "name": "ElevateHigh 310",
        "tier": "High",
        "description": (
            "Premium high-rise platform with higher speed and capacity "
            "for demanding commercial and institutional projects"
        ),
        "supported_building_types": ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Traction", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1200, "max": 1800},
        "recommended_floor_range":    {"min": 20,   "max": 45},
        "recommended_speed_range":    {"min": 2.0,  "max": 3.0},
        "starting_price":  7000000,
        "maximum_price":  11000000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Premium corporate headquarters",
            "Multi-speciality hospitals",
            "Convention and exhibition centres",
            "High-rise mixed-use developments",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 1800, "max_floors": 45, "speed": 3.0, "base_price": 7000000,
    },

    {
        "id":   "ELV-320",
        "name": "ElevateHigh 320",
        "tier": "High",
        "description": (
            "Top-of-range high-rise platform for 50-floor towers "
            "with maximum capacity and speed in its class"
        ),
        "supported_building_types": ["Commercial", "Office", "Hospital", "Hotel", "Mixed-Use", "Government"],
        "supported_lift_types":     ["Passenger", "Traction", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1360, "max": 2000},
        "recommended_floor_range":    {"min": 25,   "max": 50},
        "recommended_speed_range":    {"min": 2.0,  "max": 3.5},
        "starting_price":  7800000,
        "maximum_price":  12500000,
        "energy_efficiency_class": "A",
        "recommended_use_cases": [
            "Landmark commercial towers",
            "Flagship hospital campuses",
            "Government high-rise complexes",
            "Luxury mixed-use developments",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 2000, "max_floors": 50, "speed": 3.5, "base_price": 7800000,
    },

    # ─────────────────────────────────────────────────────────────────────
    #  SUPER TIER — Commercial towers & large institutional
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-400",
        "name": "ElevateSuper 400",
        "tier": "Super",
        "description": (
            "Ultra-high-performance platform for large commercial towers "
            "and institutional campuses up to 60 floors"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use", "Government", "Airport"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1600, "max": 2200},
        "recommended_floor_range":    {"min": 30,   "max": 60},
        "recommended_speed_range":    {"min": 2.5,  "max": 4.0},
        "starting_price": 10000000,
        "maximum_price":  15000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Major corporate towers (30–60 floors)",
            "International airport terminals",
            "Government landmark buildings",
            "Large institutional campuses",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 2200, "max_floors": 60, "speed": 4.0, "base_price": 10000000,
    },

    {
        "id":   "ELV-410",
        "name": "ElevateSuper 410",
        "tier": "Super",
        "description": (
            "High-capacity super-rise platform for premium towers "
            "and transit infrastructure up to 70 floors"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use", "Transit", "Airport"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1800, "max": 2500},
        "recommended_floor_range":    {"min": 35,   "max": 70},
        "recommended_speed_range":    {"min": 3.0,  "max": 4.5},
        "starting_price": 11200000,
        "maximum_price":  17500000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Premium corporate headquarters (35–70 floors)",
            "Metro and transit hubs",
            "International convention centres",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 2500, "max_floors": 70, "speed": 4.5, "base_price": 11200000,
    },

    {
        "id":   "ELV-420",
        "name": "ElevateSuper 420",
        "tier": "Super",
        "description": (
            "Flagship super-rise platform for 80-floor commercial "
            "skyscrapers with class-leading speed"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 2000, "max": 2800},
        "recommended_floor_range":    {"min": 40,   "max": 80},
        "recommended_speed_range":    {"min": 3.5,  "max": 5.0},
        "starting_price": 12500000,
        "maximum_price":  20000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Premium commercial skyscrapers (40–80 floors)",
            "Iconic mixed-use towers",
            "Financial district landmark buildings",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 2800, "max_floors": 80, "speed": 5.0, "base_price": 12500000,
    },

    # ─────────────────────────────────────────────────────────────────────
    #  ULTRA TIER — Skyscrapers & mega-tall buildings
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-500",
        "name": "ElevateUltra 500",
        "tier": "Ultra",
        "description": (
            "Ultra-high-rise platform for skyscrapers and mega-tall "
            "buildings up to 100 floors"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 2000, "max": 3000},
        "recommended_floor_range":    {"min": 50,   "max": 100},
        "recommended_speed_range":    {"min": 4.0,  "max": 6.0},
        "starting_price": 16500000,
        "maximum_price":  25000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Skyscrapers (50–100 floors)",
            "Iconic city-centre towers",
            "Ultra-luxury mixed-use developments",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Wind Sway Compensation",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 3000, "max_floors": 100, "speed": 6.0, "base_price": 16500000,
    },

    {
        "id":   "ELV-510",
        "name": "ElevateUltra 510",
        "tier": "Ultra",
        "description": (
            "Advanced ultra-high-rise platform for super-tall towers "
            "up to 120 floors with express zone capability"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 2500, "max": 3500},
        "recommended_floor_range":    {"min": 60,   "max": 120},
        "recommended_speed_range":    {"min": 5.0,  "max": 7.0},
        "starting_price": 20000000,
        "maximum_price":  30000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Super-tall commercial towers (60–120 floors)",
            "Express shuttle zones in mega-complexes",
            "Landmark skyline-defining developments",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Wind Sway Compensation",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 3500, "max_floors": 120, "speed": 7.0, "base_price": 20000000,
    },

    {
        "id":   "ELV-520",
        "name": "ElevateUltra 520",
        "tier": "Ultra",
        "description": (
            "Flagship ultra-high-rise platform for mega-tall "
            "skyscrapers up to 150 floors — the pinnacle of the range"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 3000, "max": 4000},
        "recommended_floor_range":    {"min": 80,   "max": 150},
        "recommended_speed_range":    {"min": 6.0,  "max": 8.0},
        "starting_price": 25000000,
        "maximum_price":  40000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Mega-tall skyscrapers (80–150 floors)",
            "World-class observation tower lifts",
            "Iconic supertall mixed-use towers",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Wind Sway Compensation",
            "Pressurised Cabin",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 4000, "max_floors": 150, "speed": 8.0, "base_price": 25000000,
    },

    # ─────────────────────────────────────────────────────────────────────
    #  SPECIALIZED PLATFORMS
    # ─────────────────────────────────────────────────────────────────────

    {
        "id":   "ELV-FRT1",
        "name": "ElevateFreight X",
        "tier": "Specialized",
        "description": (
            "Heavy-duty freight and goods platform for warehouses, "
            "factories and logistics centres"
        ),
        "supported_building_types": ["Industrial", "Commercial", "Warehouse"],
        "supported_lift_types":     ["Freight", "Goods"],
        "recommended_capacity_range": {"min": 2000, "max": 5000},
        "recommended_floor_range":    {"min": 2,    "max": 30},
        "recommended_speed_range":    {"min": 0.5,  "max": 1.0},
        "starting_price": 15000000,
        "maximum_price":  22500000,
        "energy_efficiency_class": "B",
        "recommended_use_cases": [
            "Warehouses and distribution centres",
            "Manufacturing plants",
            "Logistics and fulfilment centres",
            "Multi-storey parking structures",
        ],
        "premium_features_available": [
            "IoT Monitoring",
            "Overload Protection",
            "Heavy-Duty Door Operator",
            "Anti-Vandal Controls",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 5000, "max_floors": 30, "speed": 1.0, "base_price": 15000000,
    },

    {
        "id":   "ELV-HSP1",
        "name": "ElevateHyperLift",
        "tier": "Specialized",
        "description": (
            "Ultra-high-speed platform for observation towers, "
            "mega-tall express zones and record-breaking installations"
        ),
        "supported_building_types": ["Commercial", "Office", "Mixed-Use", "Transit"],
        "supported_lift_types":     ["Passenger", "Gearless Traction"],
        "recommended_capacity_range": {"min": 1600, "max": 2000},
        "recommended_floor_range":    {"min": 50,   "max": 200},
        "recommended_speed_range":    {"min": 6.0,  "max": 10.0},
        "starting_price": 41500000,
        "maximum_price":  65000000,
        "energy_efficiency_class": "A+",
        "recommended_use_cases": [
            "Observation tower express lifts",
            "Mega-tall express shuttle zones",
            "Record-breaking supertall installations",
        ],
        "premium_features_available": [
            "Destination Control",
            "Touchless Controls",
            "IoT Monitoring",
            "Voice Announcement",
            "Regenerative Drive",
            "ARD (Automatic Rescue Device)",
            "CCTV Integration",
            "Access Control System",
            "Biometric Access",
            "Earthquake Sensor",
            "Wind Sway Compensation",
            "Pressurised Cabin",
            "Atmospheric Pressure Compensation",
            "Braille Buttons",
            "Car Fan with False Ceiling",
            "Emergency Intercom",
        ],
        # Backward-compatible shim keys
        "capacity": 2000, "max_floors": 200, "speed": 10.0, "base_price": 41500000,
    },
]
