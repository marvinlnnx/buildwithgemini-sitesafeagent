# ruff: noqa
import datetime
import json
import os
import uuid
import urllib.request
from zoneinfo import ZoneInfo

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-80a5242e228b")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from google.cloud import firestore, storage
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types, Client as GenAIClient

from .a2ui_utils import a2ui_callback

MODEL = "gemini-2.5-flash"
FIRESTORE_PROJECT = "qwiklabs-gcp-04-80a5242e228b"
STORAGE_BUCKET = "sitesafe-media-qwiklabs-gcp-04-80a5242e228b"

db = firestore.Client(project=FIRESTORE_PROJECT)
storage_client = storage.Client(project=FIRESTORE_PROJECT)


def get_safety_rules(category: str = "") -> list[dict]:
    """Retrieve OSHA 1926 construction safety rules and standards from Firestore database.

    Args:
        category: Optional category filter (e.g. 'Fall Protection', 'Ladders', 'PPE', 'Electrical', 'Trenching').

    Returns:
        List of safety rules with code, title, summary, and corrective actions.
    """
    rules_ref = db.collection("safety_rules")
    docs = rules_ref.stream()
    results = []
    for d in docs:
        data = d.to_dict()
        if category and category.lower() not in data.get("category", "").lower() and category.lower() not in data.get("title", "").lower():
            continue
        results.append(data)
    return results


def get_inspection_history(jobsite: str = "") -> list[dict]:
    """Retrieve historical safety inspections and audits from Firestore database.

    Args:
        jobsite: Optional jobsite name to filter inspection records.

    Returns:
        List of historical safety inspections with jobsite, inspector, risk score, and notes.
    """
    insp_ref = db.collection("inspections")
    docs = insp_ref.stream()
    results = []
    for d in docs:
        data = d.to_dict()
        if jobsite and jobsite.lower() not in data.get("jobsite", "").lower():
            continue
        results.append(data)
    return results


def record_inspection(jobsite: str, inspector: str, hazards_detected: int, risk_score: int, notes: str) -> dict:
    """Record a completed safety inspection audit into Firestore database.

    Args:
        jobsite: Name or address of the jobsite (e.g. 'North Wing Scaffolding Area').
        inspector: Name and credentials of the inspector (e.g. 'Jane Doe, CSP').
        hazards_detected: Number of hazards observed.
        risk_score: Numerical risk score between 0 and 100.
        notes: Detailed observations and corrective actions required.

    Returns:
        Confirmation dictionary with the generated inspection ID.
    """
    today = datetime.date.today().isoformat()
    new_id = f"INSP-{datetime.date.today().year}-{uuid.uuid4().hex[:4].upper()}"
    status = "Resolved" if hazards_detected == 0 else ("Action Required" if risk_score > 50 else "Monitor")
    doc_data = {
        "id": new_id,
        "jobsite": jobsite,
        "inspector": inspector,
        "date": today,
        "risk_score": risk_score,
        "hazards_detected": hazards_detected,
        "status": status,
        "notes": notes
    }
    db.collection("inspections").document(new_id).set(doc_data)
    return {"status": "success", "inspection_id": new_id, "record": doc_data}


def calculate_site_risk(high_severity_count: int, medium_severity_count: int, low_severity_count: int) -> dict:
    """Compute mathematical composite site risk index and OSHA potential penalty exposure.

    Args:
        high_severity_count: Count of critical/high severity hazards (e.g., fall hazards >6ft, unshored trenches).
        medium_severity_count: Count of medium severity hazards (e.g., missing hard hat, trip hazards).
        low_severity_count: Count of low severity minor housekeeping hazards.

    Returns:
        Dictionary containing composite risk score (0-100), risk level tier, and estimated OSHA penalty range.
    """
    raw_score = (high_severity_count * 30) + (medium_severity_count * 15) + (low_severity_count * 5)
    risk_score = min(100, raw_score)
    if risk_score >= 70:
        level = "CRITICAL / HIGH RISK"
        penalty = "$16,131 - $161,323 (OSHA Willful/Repeat Citation range)"
    elif risk_score >= 35:
        level = "MODERATE RISK"
        penalty = "$1,000 - $16,131 (OSHA Serious Citation range)"
    else:
        level = "LOW RISK / ACCEPTABLE"
        penalty = "None to Minor Notice"
    return {
        "risk_score": risk_score,
        "risk_level": level,
        "estimated_penalty_exposure": penalty,
        "high_severity_count": high_severity_count,
        "medium_severity_count": medium_severity_count,
        "low_severity_count": low_severity_count
    }


def generate_safety_sign(prompt: str) -> str:
    """Generate a site safety warning illustration or corrective action sign using gemini-3.1-flash-lite-image and save to Cloud Storage.

    Args:
        prompt: Description of the safety sign or hazard visual (e.g., 'Warning sign for fall protection harness required').

    Returns:
        Public HTTPS URL of the generated safety sign image.
    """
    try:
        genai_client = GenAIClient(vertexai=True, project=FIRESTORE_PROJECT, location="global")
        res = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Industrial construction safety sign: {prompt}"
        )
        part = res.candidates[0].content.parts[0]
        image_bytes = part.inline_data.data

        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob_name = f"safety_sign_{uuid.uuid4().hex[:8]}.jpg"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")
        return f"https://storage.googleapis.com/{STORAGE_BUCKET}/{blob_name}"
    except Exception as e:
        return f"Error generating image: {str(e)}"


def get_site_weather(location: str = "New York") -> dict:
    """Fetch live weather and wind speed conditions from Open-Meteo public API to assess weather-related jobsite safety hazards.

    Args:
        location: City or site location name.

    Returns:
        Current weather data including temperature, wind speed, and hazard warning.
    """
    coords = {"new york": (40.71, -74.00), "san francisco": (37.77, -122.42), "chicago": (41.87, -87.62)}
    lat, lon = coords.get(location.lower(), (40.71, -74.00))
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SiteSafeAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            cw = data.get("current_weather", {})
            wind = cw.get("windspeed", 0)
            temp = cw.get("temperature", 0)
            warning = "High wind hazard - Crane operations and elevated work above 20ft should be suspended." if wind > 25 else "Wind conditions nominal for crane and elevated scaffold work."
            return {
                "location": location,
                "temperature_celsius": temp,
                "windspeed_kmh": wind,
                "safety_advisory": warning
            }
    except Exception as e:
        return {"location": location, "error": str(e), "safety_advisory": "Could not fetch live weather"}


INSTRUCTION = """You are SiteSafe AI, an expert construction safety officer, OSHA compliance specialist, and jobsite hazard auditor.
Your job is to inspect safety hazards, look up OSHA standards, compute site risk scores, log safety audits, and generate safety warning signage.

When presenting hazard findings, safety audits, OSHA rules, or risk scores, you can format your answer as clean, structured A2UI v0.8 JSON:
[
  {
    "beginRendering": {
      "surfaceId": "default",
      "root": "c_root"
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "default",
      "components": [
        {
          "id": "c_root",
          "component": {
            "Card": {
              "child": "col_1"
            }
          }
        },
        {
          "id": "col_1",
          "component": {
            "Column": {
              "children": {
                "explicitList": ["t_title", "t_body"]
              }
            }
          }
        },
        {
          "id": "t_title",
          "component": {
            "Text": {
              "text": {"literalString": "SiteSafe AI Report"},
              "usageHint": "h2"
            }
          }
        },
        {
          "id": "t_body",
          "component": {
            "Text": {
              "text": {"literalString": "Details of the finding or rule here."}
            }
          }
        }
      ]
    }
  }
]

Guidelines:
- Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows (and optionally ONE Image if you have an https public URL).
- Every component must have "id" and "component" keys.
- Never nest a Card inside a Card.
- Use ONLY these components: Card, Column, Row, Text, Image.
- Do not use markdown inside Text literalString. Use usageHint ('h1', 'h2', 'h3', 'caption', 'body') for styling.
- For conversational greetings or simple questions, you may answer with concise, professional plain text.
- Always offer actionable OSHA corrective steps (e.g., 29 CFR 1926 standards).
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[
        get_safety_rules,
        get_inspection_history,
        record_inspection,
        calculate_site_risk,
        generate_safety_sign,
        get_site_weather
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
