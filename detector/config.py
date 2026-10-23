"""Detector constants. Synthetic data — not Opendoor data.

Tuned only by editing this file. Current values were tuned on seed 42 (in-sample for seed-42 tests; see
DECISIONS D9/D11); Phase 5 re-tunes on seeds 1–5 and reports holdout seeds 6–10. Nothing here comes from the
generator: seasonality is separated by peer comparison, not by known seasonal parameters.
"""

WINDOW_WEEKS = 4
MIN_PEERS = {"market": 3, "band": 2}
MIN_SEGMENT_SAMPLE = 8  # per-segment sample floor for peer residuals (DECISIONS D6)
# Per-metric override of that floor for the detector's trigger panels only (DECISIONS D29); reported numbers keep D6.
SEGMENT_SAMPLE_FLOOR: dict[str, int] = {"reno_overrun_pct": 4}
# Shrinkage pseudo-count k per metric: a segment residual is scaled by n / (n + k) (DECISIONS D29). 0 = off.
SHRINK_K: dict[str, float] = {"reno_overrun_pct": 35.0}
HISTORY_WEEKS = 26  # portfolio check only; the drift baseline expands (DECISIONS D16)
BURN_IN_WEEKS = 8  # weeks excluded from baselines: the synthetic portfolio starts empty and ramps up
MIN_HISTORY_WEEKS = 12
EVAL_WEEKS = 8
Z_ALERT = 3.25
Z_CONSECUTIVE = 2
CUSUM_K = 0.75
CUSUM_H = 6.0
# Residuals come from overlapping WINDOW_WEEKS windows, so successive z are autocorrelated; CUSUM runs on
# z / sqrt(WINDOW_WEEKS) to keep its false-alarm rate near the independent-sample design (3% vs 29%).
CUSUM_SCALE = WINDOW_WEEKS ** 0.5
Z_EXPLAIN = 2.0
PORTFOLIO_Z = 4.0
PORTFOLIO_BASELINE_WEEKS = 8
FORWARD_WEEKS = 13
# Minimum robust scale per metric, so a quiet history can't produce huge z-scores (DECISIONS D7).
SIGMA_FLOOR = {"contract_rate": 0.01, "first_offer_rate": 0.01, "reno_overrun_pct": 0.01, "avg_spread_pct": 0.0005}
# User-given planning range for the resale shortfall behind an adverse-selection scenario estimate
# (low, mid, high). Not a generator parameter.
ADVERSE_SELECTION_SHORTFALL = (0.01, 0.02, 0.03)
IMPACT_TRAILING_WEEKS = 13
