import random
import uuid
import numpy as np
from typing import Dict, Any, List, Optional

def generate_timeline(
    identity_type: Optional[str] = None,
    weeks: int = 24,
    seed: Optional[int] = None,
    ring_id: Optional[str] = None,
    template_idx: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generates a 6-month (24-week) behavioral timeline for an identity.
    
    Types:
    - 'sleeper': Synthetic identity designed by GenAI agent script. Exhibits robotic
                 monotonic spend ramp-up, hyper-regular logins, 100% on-time bills,
                 and culminates in a massive terminal fraud strike (bust-out).
    - 'benign': Real organic human consumer behavior with natural variance, dips,
                sporadic logins, seasonal fluctuations, and no terminal bust-out.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    if identity_type is None:
        identity_type = "sleeper" if random.random() < 0.5 else "benign"

    identity_id = f"VT-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    if identity_type == "sleeper":
        # Sleeper identity: Scripted incubation trajectory
        # If ring_id is provided or chosen, lock in base parameters so ring members share high similarity
        if ring_id:
            # Common ring archetype based on ring hash
            base_spend = 120.0 + (hash(ring_id) % 50)
            ramp_rate = 14.0 + ((hash(ring_id) >> 2) % 6)
            base_login = 5
        else:
            base_spend = float(np.random.uniform(90.0, 180.0))
            ramp_rate = float(np.random.uniform(10.0, 22.0))
            base_login = int(np.random.choice([4, 5, 6]))

        # The fraud strike occurs in the final weeks (week 23 or 24)
        strike_week = weeks if weeks <= 24 else 24

        for w in range(1, weeks + 1):
            if w < strike_week:
                # Incubation phase: Uncanny linearity / monotonic spend ramp
                # Very low Gaussian noise (~2-5% std dev)
                noise = np.random.normal(0, base_spend * 0.035)
                spend = max(20.0, round(base_spend + (w - 1) * ramp_rate + noise, 2))
                
                # Hyper-regular logins (nearly constant, 0 or 1 variance)
                login_jitter = np.random.choice([-1, 0, 1], p=[0.1, 0.8, 0.1])
                login_count = max(1, int(base_login + login_jitter))
                
                # Almost never change device or location during trust-building incubation
                new_device = bool(random.random() < 0.03)
                location_change = bool(random.random() < 0.02)
                bill_paid_on_time = True  # Scripted perfect credit building
                fraud_strike = False
            else:
                # FRAUD STRIKE (Bust-out Event):
                # Massive surge (10x-30x average spend), maxing out lines, rapid off-ramping
                pre_strike_avg = base_spend + (strike_week - 1) * ramp_rate
                surge_multiplier = float(np.random.uniform(12.0, 25.0))
                spend = round(pre_strike_avg * surge_multiplier + np.random.normal(500, 100), 2)
                
                # Sudden burst of activity or account takeover signatures
                login_count = int(np.random.randint(18, 36))
                new_device = True
                location_change = True
                bill_paid_on_time = False  # Account abandoned / bust-out
                fraud_strike = True

            timeline.append({
                "week": w,
                "spend": float(spend),
                "login_count": int(login_count),
                "new_device": new_device,
                "location_change": location_change,
                "bill_paid_on_time": bill_paid_on_time,
                "fraud_strike": fraud_strike
            })

    else:
        # Benign human consumer: Natural variance, lifestyle fluctuations
        baseline_spend = float(np.random.uniform(220.0, 650.0))
        volatility = float(np.random.uniform(0.20, 0.45))
        
        for w in range(1, weeks + 1):
            # Human spend has natural log-normal variance, dips, occasional weekend/holiday spikes
            random_factor = np.random.lognormal(mean=0, sigma=volatility)
            # Add minor seasonal/monthly cycle
            cycle = 1.0 + 0.15 * np.sin(w * 2 * np.pi / 4.3)
            spend = max(15.0, round(baseline_spend * random_factor * cycle, 2))
            
            # Sporadic logins (Poisson-like dispersion from 1 to 14)
            login_count = max(0, int(np.random.poisson(lam=5.5) + np.random.randint(-1, 3)))
            
            # Natural human device changes & travel
            new_device = bool(random.random() < 0.08)
            location_change = bool(random.random() < 0.09)
            
            # Realistic occasional late payment (e.g. forgotten bill or vacation)
            bill_paid_on_time = bool(random.random() > 0.08)
            fraud_strike = False

            timeline.append({
                "week": w,
                "spend": float(spend),
                "login_count": int(login_count),
                "new_device": new_device,
                "location_change": location_change,
                "bill_paid_on_time": bill_paid_on_time,
                "fraud_strike": fraud_strike
            })

    return {
        "id": identity_id,
        "type": identity_type,
        "ring_id": ring_id,
        "timeline": timeline,
        "weeks_count": weeks
    }

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
) -> Dict[str, Any]:
    """
    Generates a sleeper identity timeline using mutated Forge parameters.
    Used by the adversarial loop to create progressively harder-to-detect attacks.

    Parameters are controlled by forge/mutation.py which reads Sentinel feedback
    and adjusts noise, dip patterns, login jitter etc. to evade detection.
    """
    identity_id = f"VT-ADV-{random.randint(1000, 9999)}-{uuid.uuid4().hex[:4].upper()}"
    timeline: List[Dict[str, Any]] = []

    base_spend = float(np.random.uniform(90.0, 180.0)) + base_spend_offset
    base_spend = max(50.0, base_spend)

    base_ramp = float(np.random.uniform(10.0, 22.0))
    ramp_std = base_ramp * ramp_rate_variance
    ramp_rate = float(np.random.normal(base_ramp, max(0.1, ramp_std)))
    ramp_rate = max(5.0, ramp_rate)

    base_login = int(np.random.choice([4, 5, 6]))
    strike_week = max(20, min(weeks, weeks + strike_week_offset))

    # Pre-compute a non-linear baseline to break R² even before noise is added
    # At higher noise_factor values (from mutation), switch to a log-curve baseline
    use_nonlinear = noise_factor > 0.12
    for w in range(1, weeks + 1):
        if w < strike_week:
            # ── Incubation phase with mutation-controlled noise ───────────────
            # Non-linear baseline: after enough mutation, switch to log-curve
            # so linear R² drops dramatically
            if use_nonlinear:
                # Log-curved spend: fast early growth, then plateau → breaks linearity
                t_frac = (w - 1) / max(1, strike_week - 2)
                baseline = base_spend + ramp_rate * (strike_week - 2) * np.log1p(t_frac * 2.718) / np.log1p(2.718)
            else:
                baseline = base_spend + (w - 1) * ramp_rate

            noise = np.random.normal(0, baseline * noise_factor)
            spend = max(20.0, round(float(baseline) + noise, 2))

            # Apply spending dip with mutation-controlled probability
            if random.random() < dip_probability:
                spend = max(15.0, round(spend * (1.0 - dip_magnitude * random.uniform(0.5, 1.5)), 2))

            # Login with mutation-controlled jitter
            jitter = int(np.random.choice(
                range(-login_jitter, login_jitter + 1),
                p=None  # uniform over the range
            ))
            login_count = max(1, base_login + jitter)

            new_device = bool(random.random() < 0.03)
            location_change = bool(random.random() < 0.02)
            bill_paid_on_time = True
            fraud_strike = False
        else:
            # ── Fraud strike ──────────────────────────────────────────────────
            pre_strike_avg = base_spend + (strike_week - 1) * ramp_rate
            # surge_multiplier_cap controls how many times bigger than the
            # pre-strike average the bust-out spend is.
            # At low caps (4–6x) the final spend blends closer to account history
            # and the z-score drops, reducing transaction_anomaly signal.
            lo = max(2.0, surge_multiplier_cap * 0.5)
            hi = max(lo + 0.5, surge_multiplier_cap)
            surge_multiplier = float(np.random.uniform(lo, hi))
            spend = round(pre_strike_avg * surge_multiplier + np.random.normal(0, pre_strike_avg * 0.2), 2)
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


def generate_batch(count: int = 10, sleeper_ratio: float = 0.5) -> List[Dict[str, Any]]:
    """Generates a batch of identities with a realistic mix including a fraud ring cluster."""
    identities = []
    
    # Generate 1 designated fraud ring cluster of 3-4 sleeper identities sharing a prompt template
    ring_size = min(4, max(3, int(count * 0.35)))
    ring_tag = f"RING-{uuid.uuid4().hex[:4].upper()}"
    
    for _ in range(ring_size):
        identities.append(generate_timeline(identity_type="sleeper", ring_id=ring_tag))
        
    remaining = count - ring_size
    for _ in range(remaining):
        itype = "sleeper" if random.random() < sleeper_ratio else "benign"
        identities.append(generate_timeline(identity_type=itype))
        
    return identities
