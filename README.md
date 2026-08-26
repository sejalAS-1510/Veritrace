# 🛡️ VeriTrace — Adversarial AI Sleeper Agent Fraud Detection System

**VeriTrace** is an adversarial AI surveillance and trajectory forensic system engineered to intercept GenAI-scripted synthetic identity fraud (**"sleeper agent" attacks**) across consumer lending and payments.

---

## 🎯 The Problem: GenAI "Sleeper Agent" Incubation
Fraud syndicates use automated LLM agents and scripts to manufacture synthetic credit identities that "incubate" over 6 months (24 weeks). During incubation:
1. They mimic model borrowers with **robotic spend linearity ($R^2 \approx 1.0$)**, hyper-regular logins, and zero missed payments.
2. At Week 24, they execute a coordinated **15x–30x terminal fraud strike (bust-out)**, maxing out credit limits before vanishing.
3. Traditional fraud filters only detect transaction anomalies at the strike moment — when the loss has already occurred.

---

## ⚡ The VeriTrace Solution
- **Incubation Trajectory Sentinel**: Computes spend monotonicity, $R^2$ fit linearity, login regularity, and variance metrics to flag synthetic behavior **weeks before bust-out** (e.g., Week 8–12).
- **Behavioral Cosine Similarity Graph**: Clusters identities whose behavioral vectors exhibit &ge; 0.90 similarity, exposing coordinated fraud rings generated from shared LLM prompt templates.
- **Live Replay & Adversarial Arms Race**: Simulates prompt adaptation waves vs Sentinel defensive model updates.

---

## 📁 Repository Structure

```text
VeriTrace/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                 # FastAPI app, CORS, REST endpoints
│   ├── forge/
│   │   ├── __init__.py
│   │   └── generator.py            # Rule-based synthetic 24-week timeline generator
│   ├── sentinel/
│   │   ├── __init__.py
│   │   ├── trajectory_model.py     # Feature extraction, R² linearity, risk scoring
│   │   └── similarity_graph.py     # NetworkX cosine similarity & fraud ring clustering
│   ├── requirements.txt            # FastAPI, uvicorn, numpy, pandas, scikit-learn, networkx
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveFeed.jsx        # Real-time synthetic generation & verdict table
│   │   │   ├── TimelineReplay.jsx  # Recharts 24-week spend & flag_week reference line
│   │   │   ├── ArmsRaceChart.jsx   # 10-round adversarial catch rate curve
│   │   │   └── SimilarityGraph.jsx # ForceGraph2D cosine similarity network
│   │   ├── api.js                  # Axios client for Sentinel API
│   │   ├── App.jsx                 # Dark dashboard with 4 tabs
│   │   ├── main.jsx
│   │   └── index.css               # Dark theme Tailwind styling
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── README.md
│
└── README.md                       # Project overview and run guide
```

---

## 🚀 Step-by-Step Run Instructions

### 1. Start the Backend (FastAPI on Port 8000)

Open a terminal and run:
```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```
> API available at: **http://localhost:8000**  
> Interactive Docs: **http://localhost:8000/docs**

---

### 2. Start the Frontend (React + Vite on Port 5173)

Open a second terminal and run:
```bash
cd frontend
npm install
npm run dev
```
> Frontend Dashboard available at: **http://localhost:5173**

---

## 🌐 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/forge/generate` | `POST` | Generates 24-week timeline, injects sleeper bust-out for ~50%, returns risk score & flag week |
| `/sentinel/history` | `GET` | Returns list of all evaluated identities and verdicts |
| `/sentinel/timeline/{id}` | `GET` | Returns weekly spend, logins, and forensic flags for an identity |
| `/sentinel/rounds` | `GET` | 10-round simulated catch rate modeling the adversarial arms race |
| `/sentinel/graph` | `GET` | NetworkX cosine similarity graph of account trajectories |
