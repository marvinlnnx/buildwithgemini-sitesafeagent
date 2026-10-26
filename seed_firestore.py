from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-04-80a5242e228b"
db = firestore.Client(project=FIRESTORE_PROJECT)

rules = [
    {
        "id": "1926.501",
        "code": "29 CFR 1926.501(b)(1)",
        "title": "Fall Protection - Unprotected Sides and Edges",
        "category": "Fall Protection",
        "severity": "High",
        "summary": "Each employee on a walking/working surface with an unprotected side or edge 6 feet or more above a lower level shall be protected by guardrail systems, safety net systems, or personal fall arrest systems.",
        "corrective_action": "Install compliant top rails and midrails, or require full-body harness with shock-absorbing lanyard tied off to 5,000-lb rated anchor."
    },
    {
        "id": "1926.1053",
        "code": "29 CFR 1926.1053(b)(1)",
        "title": "Ladders - Placement and Extension",
        "category": "Ladders",
        "severity": "High",
        "summary": "When portable ladders are used for access to an upper landing surface, side rails must extend at least 3 feet above the upper landing surface. Ladders must be placed at a 4:1 slope angle and secured at top or bottom.",
        "corrective_action": "Extend ladder rails 3 feet above landing, tie off top rungs, verify 75-degree angle (1 foot out for every 4 feet up), and inspect foot pads."
    },
    {
        "id": "1926.100",
        "code": "29 CFR 1926.100(a)",
        "title": "Head Protection - Hard Hats",
        "category": "PPE",
        "severity": "Medium",
        "summary": "Employees working in areas where there is a possible danger of head injury from impact, falling or flying objects, or electrical shock and burns shall be protected by protective helmets.",
        "corrective_action": "Immediately issue ANSI Z89.1 certified Type 1/2 hard hats to all personnel on site and enforce mandatory 100% hard hat zone."
    },
    {
        "id": "1926.403",
        "code": "29 CFR 1926.403(b)(2)",
        "title": "Electrical - Guarding and Wet Conditions",
        "category": "Electrical",
        "severity": "Critical",
        "summary": "Electrical equipment shall not be used in damp or wet locations unless identified for such use. All 120-volt temporary power must be protected by Ground-Fault Circuit-Interrupters (GFCI).",
        "corrective_action": "Remove exposed power cords from standing water, install GFCI pigtails at the distribution box, and tag damaged cords out of service."
    },
    {
        "id": "1926.652",
        "code": "29 CFR 1926.652(a)(1)",
        "title": "Excavations - Protective Systems",
        "category": "Trenching",
        "severity": "Critical",
        "summary": "Each employee in an excavation 5 feet or deeper shall be protected from cave-ins by an adequate protective system (sloping, benching, shoring, or trench shield).",
        "corrective_action": "Immediately evacuate un-shored trench; install hydraulic aluminum shoring or trench box before work resumes."
    }
]

inspections = [
    {
        "id": "INSP-2026-001",
        "jobsite": "Hudson Yards Commercial Tower",
        "inspector": "Sarah Chen, CSP",
        "date": "2026-10-25",
        "risk_score": 78,
        "hazards_detected": 3,
        "status": "Action Required",
        "notes": "Worker observed on 4th floor perimeter without tied-off harness. Extension ladder unsecured on gravel."
    },
    {
        "id": "INSP-2026-002",
        "jobsite": "Bayfront Transit Expansion",
        "inspector": "Marcus Vance, CIH",
        "date": "2026-10-26",
        "risk_score": 32,
        "hazards_detected": 1,
        "status": "Resolved",
        "notes": "Missing hard hat warning signage at gate 2. Corrected immediately on spot."
    }
]

for r in rules:
    db.collection("safety_rules").document(r["id"]).set(r)
    print(f"Seeded safety rule {r['id']}")

for insp in inspections:
    db.collection("inspections").document(insp["id"]).set(insp)
    print(f"Seeded inspection {insp['id']}")

print("Firestore seeding complete!")
