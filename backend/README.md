# VeriTrace Backend — Sleeper Agent & Synthetic Identity Fraud Sentinel

VeriTrace is an adversarial AI detection engine designed to detect GenAI-incubated synthetic identities ("sleeper agents") before they execute massive bust-out strikes.

## Features
- **Forge Generator (`forge/generator.py`)**: Generates 24-week incubation timelines for both organic human consumers and GenAI sleeper agents.
- **Sentinel Trajectory Engine (`sentinel/trajectory_model.py`)**: Computes spend smoothness ($R^2$ linearity), spend monotonicity, login regularity, and variance metrics to flag synthetic behavior early (weeks before bust-out).
- **Similarity Graph Engine (`sentinel/similarity_graph.py`)**: NetworkX cosine similarity engine that clusters accounts sharing prompt templates into coordinated fraud rings.
- **FastAPI Endpoints (`api/main.py`)**:
  - `POST /forge/generate`: Generate single identity timeline and evaluate risk
  - `GET /sentinel/history`: List all evaluated identities and verdicts
  - `GET /sentinel/timeline/{id}`: Detailed spend & login timeline for visual replay
  - `GET /sentinel/rounds`: Adversarial arms race round-by-round catch rate
  - `GET /sentinel/graph`: Network graph of identities and fraud ring clusters

## Quickstart

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the FastAPI Server
```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000) and interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs).
