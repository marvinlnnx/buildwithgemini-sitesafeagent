# SiteSafeAgent 🛡️: Intelligent Jobsite Safety Inspector

> **Build with Gemini: Track 3 (Build an Agent-First App)**
> Built using Google Agent Development Kit (ADK), Gemini 2.5 Flash, Vertex AI, Firestore, Cloud Storage, and Agent-to-Agent (A2A) protocol with A2UI.
>
> 🌐 **Live Public App:** [https://sitesafeagent-543815073011.northamerica-northeast2.run.app](https://sitesafeagent-543815073011.northamerica-northeast2.run.app)

---

## 📌 Executive Pitch

Safety hazards are easy to miss on busy, high-risk construction jobsites. **SiteSafeAgent** turns any smartphone or computer into an automated OSHA safety compliance auditor. Supervisors and workers can upload site photos to receive immediate OSHA 29 CFR 1926 violation breakdowns and downloadable PDF audit reports, or point a live camera and ask *"Is this safe?"* to get an instant spoken answer in real time.

---

## 🚀 Key Features & Modes

### 1. 📸 Photo Inspector Mode
- **Multi-Photo OSHA Audit**: Upload photos from any phone or browser. Gemini identifies visual hazards, rates severity (**Critical / High**, **Moderate**, or **Low**), cites the exact violated standard (e.g. *29 CFR 1926.501 Fall Protection*), and provides concrete remediation steps.
- **Exportable PDF Audit Report**: 1-click generation of a branded PDF report complete with jobsite ID, risk index dial, violation matrix, and inspector sign-off block.
- **Persistent Inspection Log**: Every audit is persisted directly to Google Cloud Firestore for compliance tracking and historical reporting.

### 2. 📹 Live Hazard Spotter Mode
- **Real-Time Video Stream**: Streams camera frames directly to Gemini.
- **Bidirectional Voice Assistance**: Workers tap the microphone and ask *"Is this safe?"* or *"Check the ladder angle"*. Gemini analyzes the live frame and replies by voice in real time with immediate safety guidance.
- **Built-in Simulation Feed**: Instant testing with pre-loaded hazard scenes even without physical camera hardware.

### 3. 💬 OSHA Agent (A2UI) Mode
- **Rich A2UI Card System**: Built on the Google A2UI v0.8 specification, displaying clean Cards, Columns, and visual layouts.
- **OSHA Standards Library**: Live database queries against construction standards in Firestore.
- **Risk Calculator Tool**: Computes site safety risk indices (0-100) and potential OSHA penalty exposure tiers.
- **Live Weather Advisory**: Queries live meteorological conditions (wind speed, temperature) to alert on elevated scaffolding or crane wind hazards.
- **Safety Sign Generator**: Uses `gemini-3.1-flash-lite-image` to generate jobsite safety signage and stores them in Cloud Storage.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Web Browser / Phone                  │
│   (Photo Inspector · Live Video · Voice · A2UI UI)     │
└───────────────────────────▲────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼────────────────────────────┐
│              FastAPI Frontend Proxy (:8080)            │
│   (frontend/main.py · static/index.html · static/demo) │
└─────────────▲────────────────────────────▲─────────────┘
              │ Local ADK / A2A            │
┌─────────────▼───────────────┐ ┌──────────▼─────────────┐
│    SiteSafe ADK Agent       │ │   Google Cloud Services│
│        (app/agent.py)       │ │                        │
│  - Gemini 2.5 Flash Model   │ │  - Cloud Firestore     │
│  - A2UI v0.8 Callback Engine│ │  - Cloud Storage Bucket│
│  - Tools & Risk Computations│ │  - Vertex AI GenAI     │
└─────────────────────────────┘ └────────────────────────┘
```

---

## ⏱️ 3-Minute Demo Flow

1. **Photo Inspector (1 min)**:
   - Open `http://localhost:8080`.
   - Click **Demo 1: Worker Without Harness (Fall Hazard)**.
   - Click **Analyze Hazards** to watch Gemini detect the unprotected edge, cite `29 CFR 1926.501(b)(1)`, and assign an 85+ Risk Score.
   - Click **Export PDF Report** to view and download the official safety audit report.
2. **Live Hazard Spotter (1 min)**:
   - Switch to the **Live Hazard Spotter** tab.
   - Click **Start Camera** (or **Simulate Video** for pre-loaded ladder inspection).
   - Click the red **Ask "Is this safe?"** button.
   - Listen to Gemini analyze the ladder angle and issue an instant spoken voice warning.
3. **OSHA Agent (1 min)**:
   - Switch to **OSHA Agent** tab.
   - Click **Fall Protection Rules** to view structured A2UI cards.
   - Click **Inspection History** to verify that our earlier photo audits were recorded in Firestore.

---

## 🛠️ Local Development & Testing

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Seed Firestore Database**:
   ```bash
   uv run python seed_firestore.py
   ```

3. **Run CLI Agent Inference**:
   ```bash
   agents-cli run "Summarize OSHA 1926.501 fall protection"
   ```

4. **Launch Web Application**:
   ```bash
   uv run python frontend/main.py
   ```
   Open your browser at **`http://localhost:8080`**.
