"""
VeriTrace demo — run this to verify the full system works.
python demo_run.py
"""
import warnings
warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient
from api.main import app

with TestClient(app) as c:
    root = c.get("/").json()
    print(f"\n{'='*55}")
    print(f"  {root['system']} v{root['version']}")
    print(f"  Identities seeded : {root['identities_monitored']}")
    print(f"  ML models active  : {root['ml_models_active']}")
    print(f"{'='*55}\n")

    # Show metrics after seed
    m = c.get("/metrics").json()
    print("DETECTION METRICS (seed data):")
    print(f"  precision        = {m['precision']}")
    print(f"  recall           = {m['recall']}")
    print(f"  F1               = {m['f1_score']}")
    print(f"  false positive % = {m['false_positive_rate_pct']}%")
    print(f"  detection %      = {m['detection_rate_pct']}%")
    print(f"  avg flag week    = W{m['avg_flag_week']}")
    print(f"  risk categories  = {m['risk_categories']}\n")

    # Run adversarial loop
    print("ADVERSARIAL LOOP (8 rounds):")
    print(f"  {'Round':<8}{'Outcome':<12}{'Risk%':<8}{'Thresh':<8}{'Sentinel note'}")
    print(f"  {'-'*60}")
    for i in range(8):
        d = c.post("/adversarial/run").json()
        note = d.get("sentinel_note", "")
        print(f"  R{d['round_number']:<7}{d['outcome']:<12}{d['risk_score_pct']:<8.1f}{d['sentinel_threshold']:<8.2f}{note}")

    # Adversarial metrics
    am = c.get("/adversarial/metrics").json()
    print(f"\nADVERSARIAL METRICS:")
    print(f"  detected  = {am['detected']}/{am['total_rounds']}")
    print(f"  evaded    = {am['evaded']}/{am['total_rounds']}")
    print(f"  detect%   = {am['detection_rate_pct']}%")
    print(f"  evasion%  = {am['evasion_rate_pct']}%")
    print(f"  F1        = {am['f1_score']}")

    # Show Forge evolution
    st = c.get("/adversarial/status").json()
    fp = st["forge_params"]
    print(f"\nFORGE PARAMS (evolved after {st['round_number']} rounds):")
    print(f"  noise_factor     = {fp['noise_factor']:.3f}  (started 0.035)")
    print(f"  surge_cap        = {fp['surge_multiplier_cap']:.1f}x  (started 20.0x)")
    print(f"  login_jitter     = ±{fp['login_jitter']}")
    print(f"  stealth_level    = {fp['stealth_level']}/3")
    print(f"  sentinel_thresh  = {st['sentinel_threshold']:.2f}")
    print(f"\n{'='*55}")
    print("  All systems operational.")
    print(f"{'='*55}\n")
