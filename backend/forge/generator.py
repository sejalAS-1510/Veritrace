"""
VeriTrace Forge — Identity & Timeline Generator
Member 1 owns the identity/timeline generation logic.
Member 3 owns generate_timeline_adversarial and generate_batch (adversarial loop).

Public API used by api/main.py and api/adversarial.py:
    generate_timeline(identity_type, weeks, seed, ring_id) -> dict
    generate_timeline_adversarial(weeks, ring_id, **mutation_kwargs) -> dict
    generate_batch(count, sleeper_ratio) -> list[dict]
"""

import random
import uuid
from typing import Any, Dict, List, Optional

import numpy as np


# ─── Adversarial sleeper timeline (mutation-parameterised) ───────────────────

def generate_timeline_adversarial(
    weeks: int = 24,
    ring_id: Optional[str] = None,
    noise_factor: float = 0.035,
    dip_probability: float = 0.04,
    dip_magnitude: float = 0.15,
    login_jitter: int = 1,
    ramp_rate_variance: float = 0.05,
    strike_week_offset: int = 0,
    base_spend_offset: float = 0.0,
    surge_multiplier_cap: float = 20.0,
    **kwargs,  # absorb any extra mutation params gracefully
) -> Dict[str, Any]:
    """
    Generates a sleeper identity timeline controlled by Forge mutation params.
    Called each round by api/adversarial.py → POST /adversarial/run.

    The parameters are tuned by forge/mutation.py based on Sentinel feedback,
    making the attack progressively harder to detect over rounds.
    """
    identity_id = f"VT-ADV-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    if ring_id:
        base_spend = 120.0 + (hash(ring_id) % 50) + base_spend_offset
        ramp_rate = 14.0 + ((hash(ring_id) >> 2) % 6)
        base_login = 5
    else:
        base_spend = float(np.random.uniform(90.0, 180.0)) + base_spend_offset
        base_spend = max(50.0, base_spend)
        ramp_rate = float(np.random.uniform(10.0, 22.0))
        base_login = int(np.random.choice([4, 5, 6]))

    # Apply ramp variance
    ramp_std = ramp_rate * max(0.0, ramp_rate_variance)
    ramp_rate = float(np.random.normal(ramp_rate, max(0.1, ramp_std)))
    ramp_rate = max(5.0, ramp_rate)

    strike_week = max(4, min(weeks, weeks + strike_week_offset))

    # Switch to log-curve baseline after heavy mutation (noise_factor > 0.12)
    # so linear R² drops dramatically, making the trajectory harder to detect
    use_nonlinear = noise_factor > 0.12

    for w in range(1, weeks + 1):
        if w < strike_week:
            # Incubation phase
            if use_nonlinear:
                t_frac = (w - 1) / max(1, strike_week - 2)
                baseline = base_spend + ramp_rate * (strike_week - 2) * np.log1p(t_frac * 2.718) / np.log1p(2.718)
            else:
                baseline = base_spend + (w - 1) * ramp_rate

            noise = float(np.random.normal(0, max(1.0, baseline * noise_factor)))
            spend = max(20.0, baseline + noise)

            if random.random() < dip_probability:
                spend *= (1.0 - dip_magnitude * random.uniform(0.5, 1.5))
            spend = round(float(spend), 2)

            jitter = int(np.random.randint(-login_jitter, login_jitter + 1)) if login_jitter > 0 else 0
            login_count = max(1, int(base_login + jitter))

            new_device = bool(random.random() < 0.03)
            location_change = bool(random.random() < 0.02)
            bill_paid_on_time = True
            fraud_strike = False
        else:
            # Fraud strike (bust-out)
            pre_strike_avg = base_spend + (strike_week - 1) * ramp_rate
            lo = max(2.0, surge_multiplier_cap * 0.5)
            hi = max(lo + 0.5, surge_multiplier_cap)
            surge_mult = float(np.random.uniform(lo, hi))
            spend = round(
                pre_strike_avg * surge_mult + float(np.random.normal(0, pre_strike_avg * 0.2)),
                2,
            )
            spend = max(pre_strike_avg * lo, spend)

            login_count = int(np.random.randint(18, 36))
            new_device = True
            location_change = True
            bill_paid_on_time = False
            fraud_strike = True

        timeline.append({
            "week": w,
            "spend": float(spend),
            "login_count": int(login_count),
            "new_device": new_device,
            "location_change": location_change,
            "bill_paid_on_time": bill_paid_on_time,
            "fraud_strike": fraud_strike,
        })

    return {
        "id": identity_id,
        "type": "sleeper",
        "ring_id": ring_id,
        "timeline": timeline,
        "weeks_count": weeks,
    }


# ─── Standard timeline (sleeper or benign) ───────────────────────────────────

def generate_timeline(
    identity_type: Optional[str] = None,
    weeks: int = 24,
    seed: Optional[int] = None,
    ring_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Generates a 24-week behavioral timeline.
    - sleeper: robotic linear ramp + bust-out at week 24
    - benign:  organic log-normal variance, no fraud strike
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    if identity_type is None:
        identity_type = "sleeper" if random.random() < 0.5 else "benign"

    if identity_type == "sleeper":
        # Use the adversarial generator with default (level 1) params
        raw = generate_timeline_adversarial(weeks=weeks, ring_id=ring_id)
        # Rename to use clean VT- prefix for non-adversarial seeding
        raw["id"] = f"VT-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
        return raw

    # Benign: organic human behavior
    identity_id = f"VT-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    baseline_spend = float(np.random.uniform(220.0, 650.0))
    volatility = float(np.random.uniform(0.20, 0.45))

    for w in range(1, weeks + 1):
        random_factor = float(np.random.lognormal(mean=0, sigma=volatility))
        cycle = 1.0 + 0.15 * np.sin(w * 2 * np.pi / 4.3)
        spend = max(15.0, round(baseline_spend * random_factor * cycle, 2))

        login_count = max(0, int(np.random.poisson(lam=5.5) + np.random.randint(-1, 3)))
        new_device = bool(random.random() < 0.08)
        location_change = bool(random.random() < 0.09)
        bill_paid_on_time = bool(random.random() > 0.08)
        fraud_strike = False

        timeline.append({
            "week": w,
            "spend": float(spend),
            "login_count": int(login_count),
            "new_device": new_device,
            "location_change": location_change,
            "bill_paid_on_time": bill_paid_on_time,
            "fraud_strike": fraud_strike,
        })

    return {
        "id": identity_id,
        "type": "benign",
        "ring_id": ring_id,
        "timeline": timeline,
        "weeks_count": weeks,
    }


# ─── Batch generator ─────────────────────────────────────────────────────────

def generate_batch(
    count: int = 10,
    sleeper_ratio: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Generates a batch of identities with a seeded fraud ring cluster.
    Always creates 3-4 sleepers sharing the same ring_id so the
    similarity graph has visible clusters from startup.
    """
    identities: List[Dict[str, Any]] = []

    ring_size = min(4, max(3, int(count * 0.35)))
    ring_tag = f"RING-{uuid.uuid4().hex[:4].upper()}"

    for _ in range(ring_size):
        identities.append(generate_timeline(identity_type="sleeper", ring_id=ring_tag))

    remaining = count - ring_size
    for _ in range(remaining):
        itype = "sleeper" if random.random() < sleeper_ratio else "benign"
        identities.append(generate_timeline(identity_type=itype))

    return identities
