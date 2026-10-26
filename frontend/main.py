"""SiteSafe AI FastAPI Server & Proxy.

Features:
- Browser talks to this server (same origin, no CORS, no cloud creds on device).
- Supports Track 3 A2A proxy to deployed Agent Engine (when AGENT_ENGINE_RESOURCE_NAME is set)
  or directly executes the local ADK Agent with A2UI callback support.
- POST /api/analyze-photo for Multi-Photo Safety Inspection (OSHA citations, severity, fixes, Firestore audit).
- WebSocket /ws/live for Real-Time Multimodal Hazard Spotter (video frames + instant voice answers).
- Serves the mobile-friendly frontend and demo assets from static/.
"""

import asyncio
import base64
import datetime
import io
import json
import os
import uuid

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-80a5242e228b")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

import google.auth
import google.auth.transport.requests
import httpx
from PIL import Image
from fastapi import FastAPI, File, Form, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-80a5242e228b")
RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")

# Initialize Firestore and Vertex AI GenAI clients
db = firestore.Client(project=PROJECT_ID)
genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")

app = FastAPI(title="SiteSafe AI API")

# Setup credentials for A2A proxy if deployed
_creds = None
try:
    _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
except Exception:
    pass


def _auth_headers() -> dict[str, str]:
    if _creds:
        _creds.refresh(google.auth.transport.requests.Request())
        return {
            "Authorization": f"Bearer {_creds.token}",
            "Content-Type": "application/json",
        }
    return {"Content-Type": "application/json"}


@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "project_id": PROJECT_ID,
        "deployed_mode": bool(RESOURCE),
        "resource": RESOURCE or "local_mode",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


# ---------------------------------------------------------------------------
# 1. PHOTO INSPECTOR: Multi-photo OSHA analysis
# ---------------------------------------------------------------------------
@app.post("/api/analyze-photo")
async def analyze_photo(
    file: UploadFile = File(None),
    image_data: str = Form(None),
    jobsite: str = Form("Site Alpha"),
    inspector: str = Form("Site Safety Officer")
):
    try:
        image_bytes = None
        if file:
            image_bytes = await file.read()
        elif image_data:
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
        else:
            return JSONResponse(status_code=400, content={"error": "No image provided"})

        img = Image.open(io.BytesIO(image_bytes))

        prompt = (
            "You are a certified OSHA Construction Safety Compliance Officer (29 CFR 1926). "
            "Carefully analyze this jobsite photograph for safety violations, hazards, and OSHA compliance risks. "
            "Return a JSON object with this exact structure:\n"
            "{\n"
            '  "overall_risk_score": 85,\n'
            '  "overall_assessment": "Summary assessment of overall jobsite safety level",\n'
            '  "hazards": [\n'
            "    {\n"
            '      "title": "Short title of hazard",\n'
            '      "severity": "High" or "Medium" or "Low",\n'
            '      "osha_rule": "Specific OSHA standard e.g. 29 CFR 1926.501(b)(1)",\n'
            '      "description": "Specific visual observation of the hazard",\n'
            '      "suggested_fix": "Concrete corrective action required immediately"\n'
            "    }\n"
            "  ],\n"
            '  "summary": "Detailed inspector commentary and high-level takeaway",\n'
            '  "corrective_actions_list": ["Action item 1", "Action item 2"]\n'
            "}"
        )

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        result = json.loads(response.text)

        # Record in Firestore inspections collection for audit compliance
        insp_id = f"INSP-{datetime.date.today().year}-{uuid.uuid4().hex[:4].upper()}"
        doc_data = {
            "id": insp_id,
            "jobsite": jobsite,
            "inspector": inspector,
            "date": datetime.date.today().isoformat(),
            "risk_score": result.get("overall_risk_score", 50),
            "hazards_detected": len(result.get("hazards", [])),
            "status": "Action Required" if result.get("overall_risk_score", 0) > 40 else "Compliant",
            "notes": result.get("summary", "")[:500]
        }
        try:
            db.collection("inspections").document(insp_id).set(doc_data)
            result["inspection_id"] = insp_id
        except Exception as e:
            result["inspection_id"] = insp_id
            result["db_warning"] = str(e)

        return result
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": f"{type(exc).__name__}: {str(exc)}"})


# ---------------------------------------------------------------------------
# 2. LIVE HAZARD SPOTTER: Real-time Camera & Mic WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    last_frame_bytes = None

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            mtype = msg.get("type")

            if mtype == "frame":
                # Received video frame from camera
                b64 = msg.get("image", "")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                last_frame_bytes = base64.b64decode(b64)
                await websocket.send_text(json.dumps({"type": "frame_ack"}))

            elif mtype == "query":
                # User asked a question e.g. "Is this safe?"
                query_text = msg.get("text", "Is this safe?")
                if not last_frame_bytes:
                    await websocket.send_text(json.dumps({
                        "type": "answer",
                        "text": "Please point the camera at the area you want me to inspect.",
                        "speech": "Please point the camera at the area you want me to inspect."
                    }))
                    continue

                img = Image.open(io.BytesIO(last_frame_bytes))
                live_prompt = (
                    f"The site worker is pointing a live camera and asking: '{query_text}'.\n"
                    "Act as an instant real-time site safety inspector. "
                    "Analyze the video frame. In 1-2 concise, punchy spoken sentences, answer whether it is safe or not. "
                    "Cite any immediate hazard or OSHA rule (e.g. ladder angle, fall protection, hard hat). "
                    "If safe, confirm it. If hazardous, give an urgent, clear warning."
                )

                response = genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[img, live_prompt]
                )
                spoken_reply = response.text.strip()

                await websocket.send_text(json.dumps({
                    "type": "answer",
                    "text": spoken_reply,
                    "speech": spoken_reply
                }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 3. CHAT PROXY: A2A deployed agent or local ADK agent with A2UI cards
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat_proxy(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    user_id = body.get("userId", "default-user")

    # If AGENT_ENGINE_RESOURCE_NAME is configured, route via A2A
    if RESOURCE:
        try:
            from a2a.client import ClientFactory, ClientConfig
            from a2a.types import Message, Role, TextPart, TransportProtocol
            
            loc = RESOURCE.split("/locations/")[1].split("/")[0]
            a2a_base = f"https://{loc}-aiplatform.googleapis.com/reasoningEngines/v1/{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(f"{a2a_base}/.well-known/agent-card.json", headers=_auth_headers())
                card_data = resp.json()
            
            # Send message over A2A
            headers = _auth_headers()
            async with httpx.AsyncClient(timeout=60.0) as client:
                rpc_resp = await client.post(
                    f"{a2a_base}/tasks/send",
                    headers=headers,
                    json={
                        "message": {
                            "role": "user",
                            "parts": [{"text": user_message}]
                        }
                    }
                )
                res_data = rpc_resp.json()
                return res_data
        except Exception as exc:
            return JSONResponse(content={"parts": [{"kind": "text", "text": f"Agent Platform Error: {exc}"}]})

    # Otherwise: Local ADK agent invocation
    try:
        import sys
        sys.path.insert(0, os.path.abspath("."))
        from app.agent import root_agent

        # Call model directly through runner / agent
        # Run root_agent with tools
        from google.adk.runners import Runner
        from app.app_utils import services
        from app.agent import app as adk_app

        runner = Runner(
            app=adk_app,
            session_service=services.get_session_service(),
            artifact_service=services.get_artifact_service(),
            auto_create_session=True,
        )

        session = await runner.session_service.create_session(
            app_name=adk_app.name,
            user_id=user_id,
        )

        from google.genai import types as genai_types
        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=user_message)]
        )

        output_parts = []
        async for event in runner.run_async(
            session_id=session.id,
            user_id=user_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for p in event.content.parts:
                    if p.text:
                        output_parts.append({"kind": "text", "text": p.text})
                    elif p.inline_data:
                        # Could be A2UI data part
                        try:
                            raw = p.inline_data.data.decode("utf-8")
                            if "<a2a_datapart_json>" in raw:
                                inner = raw.split("<a2a_datapart_json>")[1].split("</a2a_datapart_json>")[0]
                                parsed = json.loads(inner)
                                output_parts.append({"kind": "a2ui", "data": parsed.get("data", parsed)})
                        except Exception:
                            pass

        if not output_parts:
            output_parts = [{"kind": "text", "text": "Inspection agent completed inquiry."}]

        return {"parts": output_parts}

    except Exception as exc:
        return JSONResponse(content={"parts": [{"kind": "text", "text": f"Error: {str(exc)}"}]})


# Serve static web frontend
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
