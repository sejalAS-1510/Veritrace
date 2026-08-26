"""Quick demo run — shows the full arms race narrative in the console."""
from fastapi.testclient import TestClient
from api.main import app

with TestClient(app) as c:
    root = c.get("/").json()
    print(f"Server: {root['system']} v{root['version']}")
    print(f"Seeded: {root['identities_monitored']} identities on startup\n")

    print("ADVERSARIAL DEMO (6 rounds):")
    print("-" * 70)
    for i in range(6):
        d = c.post("/adversarial/run").json()
        bar = "#" * int(d["risk_score_pct"] / 5)
        sym = "EVADED !!!" if d["outcome"] == "EVADED" else "DETECTED "
        note = f"  [{d['sentinel_note']}]" if d.get("sentinel_note") else ""
        traj = d["risk_breakdown"]["trajectory_risk"]
        tx   = d["risk_breakdown"]["transaction_anomaly"]
        print(f"  R{d['round_number']}: {sym}  risk={d['risk_score_pct']:5.1f}%  "
              f"traj={traj:.2f}  tx={tx:.2f}  thresh={d['sentinel_threshold']:.2f}{note}")
        if d["outcome"] == "DETECTED":
            print(f"       Forge → {d['mutation_description']}")
        elif d.get("sentinel_note"):
            print(f"       Sentinel → {d['sentinel_note']}")
    print("-" * 70)

    m = c.get("/metrics").json()
    print(f"\nMETRICS (all identities in store):")
    print(f"  precision={m['precision']}  recall={m['recall']}  f1={m['f1_score']}")
    print(f"  FP_rate={m['false_positive_rate_pct']}%  detection={m['detection_rate_pct']}%  evasion={m['evasion_rate_pct']}%")
    print(f"  avg_flag_week={m['avg_flag_week']}  sleeper_risk={m['avg_risk_sleeper']}  benign_max={m['max_risk_benign']}")

    adv = c.get("/adversarial/metrics").json()
    print(f"\nADVERSARIAL METRICS (loop only):")
    print(f"  rounds={adv['total_rounds']}  detected={adv['detected']}  evaded={adv['evaded']}")
    print(f"  detection_rate={adv['detection_rate_pct']}%  evasion_rate={adv['evasion_rate_pct']}%")
    print(f"  avg_flag_week={adv['avg_flag_week']}")

    status = c.get("/adversarial/status").json()
    fp = status["forge_params"]
    print(f"\nFORGE PARAMS after {status['round_number']} rounds:")
    print(f"  noise={fp['noise_factor']:.3f}  dip_prob={fp['dip_probability']:.2f}  jitter={fp['login_jitter']}  "
          f"surge_cap={fp['surge_multiplier_cap']:.1f}x  stealth={fp['stealth_level']}")
    print(f"  sentinel_threshold={status['sentinel_threshold']:.2f}")
