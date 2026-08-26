# VeriTrace Backend — Sleeper Agent & Synthetic Identity Fraud Sentinel

Adversarial AI detection engine: Forge (red team) vs Sentinel (blue team).

---

## Architecture

```
backend/
├── api/
│   ├── main.py           # FastAPI app, all routes, startup seed
│   └── adversarial.py    # Adversarial loop engine (run/reset/feedback/metrics)
├── forge/
│   ├── generator.py      # generate_timeline(), generate_timeline_adversarial()
│   ├── mutation.py       # mutate_params() — Forge learns from Sentinel feedback
│   └── __init__.py
├── sentinel/
│   ├── trajectory_model.py  # extract_features(), transaction_anomaly_score(), score_trajectory()
│   ├── similarity_graph.py  # build_similarity_graph() — fraud ring detection
│   └── __init__.py
└── requirements.txt
```

---

## Quickstart

```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

---

## Full API Reference

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check, stats, seeded identity count |

### Forge (Attack Generator)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/forge/generate` | Generate one identity (sleeper/benign/random) |
| POST | `/forge/batch` | Generate a batch with a built-in fraud ring cluster |

**POST /forge/generate body:**
```json
{ "identity_type": "sleeper", "weeks": 24, "ring_id": null }
```

### Sentinel (Defender)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sentinel/analyze` | Score an externally-supplied timeline |
| GET | `/sentinel/history` | All evaluated identities, newest first |
| GET | `/sentinel/timeline/{id}` | Full timeline + all Sentinel verdict fields |
| GET | `/sentinel/graph` | Cosine-similarity fraud-ring graph |

**GET /sentinel/history query params:** `limit`, `type_filter`, `flagged_only`  
**GET /sentinel/graph query params:** `threshold` (0.50–1.0, default 0.88)

### Accounts / Attacks (project-spec aliases)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts` | All identities (alias for /sentinel/history) |
| GET | `/accounts/{id}` | Single identity (alias for /sentinel/timeline/{id}) |
| GET | `/attacks` | Only sleeper-type identities, by risk score |
| GET | `/metrics` | Aggregate precision/recall/F1/FP-rate across all identities |

### Adversarial Loop (Member 3 core)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/adversarial/run` | One full round: Forge→Sentinel→Feedback→Mutate |
| POST | `/adversarial/reset` | Reset session, restore default Forge params |
| POST | `/adversarial/feedback` | Inject external Sentinel feedback into Forge |
| GET | `/adversarial/rounds` | Live round history (falls back to demo data) |
| GET | `/adversarial/status` | Current Forge params + session stats |
| GET | `/adversarial/metrics` | Adversarial precision/recall/F1/evasion rate |

**POST /adversarial/run** — the key demo endpoint. Does:
1. Read current (mutated) Forge parameters
2. Generate adversarial sleeper identity
3. Run Sentinel trajectory + anomaly analysis
4. Record detected/evaded outcome
5. Mutate Forge params based on which signals gave it away
6. Return full round record including risk_breakdown, mutation_description

**POST /adversarial/feedback body:**
```json
{
  "detection_features": {
    "spend_smoothness": 0.95,
    "spend_monotonicity": 0.90,
    "login_regularity": 0.75,
    "variance_score": 0.10,
    "bust_out_ratio": 0.80,
    "device_change_rate": 0.01
  },
  "was_detected": true,
  "notes": "Optional annotation"
}
```

---

## Detection Logic

Sentinel uses **two independent layers** — Forge must beat both to evade:

**Layer 1 — Trajectory (60% weight)**
- Spend linearity R² (smoothness)
- Spend monotonicity (fraction non-decreasing)
- Login regularity (inverse std-dev)
- Bust-out ratio (final spend vs incubation mean)
- Coefficient of variation (organic noise level)
- Device change rate signal

**Layer 2 — Transaction Anomaly (40% weight)**
- Z-score of final transaction vs account's own history
- Uses effective sigma (min 20% of mean) so Forge can reduce this via variance inflation

**Threshold: 0.55** — calibrated so benign accounts (max score ~0.41) never trigger, default sleepers (min score ~0.87) always trigger, and maximally-mutated attacks (~0.50 mean) produce realistic evasion.

---

## Forge Mutation Parameters

| Parameter | Default | Mutates when... |
|-----------|---------|-----------------|
| `noise_factor` | 0.035 | smoothness > 0.75 |
| `dip_probability` | 0.04 | smoothness > 0.75 or monotonicity > 0.80 |
| `dip_magnitude` | 0.15 | smoothness > 0.75 |
| `login_jitter` | 1 | login_regularity > 0.70 |
| `ramp_rate_variance` | 0.05 | monotonicity > 0.80 |
| `surge_multiplier_cap` | 20.0 | bust_out_ratio > 0.60 |
| `strike_week_offset` | 0 | round >= 3 |
| `base_spend_offset` | 0.0 | round >= 4 |
| `stealth_level` | 1 | escalates every 3 rounds |
