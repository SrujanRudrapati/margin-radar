"""Detector constants. Synthetic data — not Opendoor data.

Tuned only on seeds 1–5 (Phase 5), and only by editing this file. Nothing here comes from the
generator: seasonality is separated by peer comparison, not by known seasonal parameters.
"""

WINDOW_WEEKS = 4
MIN_PEERS = {"market": 3, "band": 2}
MIN_SEGMENT_SAMPLE = 8  # per-segment sample floor for peer residuals (DECISIONS D6)
HISTORY_WEEKS = 26
MIN_HISTORY_WEEKS = 8
EVAL_WEEKS = 8
Z_ALERT = 3.25
Z_CONSECUTIVE = 2
CUSUM_K = 0.5
CUSUM_H = 8.0
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
