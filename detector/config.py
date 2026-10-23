"""Detector constants. Synthetic data — not Opendoor data.

Tuned only on seeds 1–5 (Phase 5), and only by editing this file. Nothing here comes from the
generator: seasonality is separated by peer comparison, not by known seasonal parameters.
"""

WINDOW_WEEKS = 4
MIN_PEERS = {"market": 3, "band": 2}
MIN_SEGMENT_SAMPLE = 8  # per-segment sample floor for peer residuals (DECISIONS D6)
HISTORY_WEEKS = 16
MIN_HISTORY_WEEKS = 8
EVAL_WEEKS = 8
Z_ALERT = 3.0
Z_CONSECUTIVE = 2
CUSUM_K = 0.5
CUSUM_H = 5.0
Z_EXPLAIN = 2.0
PORTFOLIO_Z = 4.0
PORTFOLIO_BASELINE_WEEKS = 8
FORWARD_WEEKS = 13
# Minimum robust scale per metric, so a quiet history can't produce huge z-scores (DECISIONS D7).
SIGMA_FLOOR = {"contract_rate": 0.01, "first_offer_rate": 0.01, "reno_overrun_pct": 0.01, "avg_spread_pct": 0.0005}
