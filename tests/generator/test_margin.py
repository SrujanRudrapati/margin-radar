import pandas as pd
import pytest

from generator.metrics import contribution_margin_usd, sold_cohort_cm


def _quarter_cm(homes, year, quarter):
    sold = homes[homes["resale_date"].notna()]
    q = sold[(sold["resale_date"].dt.year == year) & (sold["resale_date"].dt.quarter == quarter)]
    return contribution_margin_usd(q).sum() / q["resale_price"].sum()


def test_contribution_margin_formula_hand_example():
    home = pd.DataFrame({
        "resale_price": [400_000.0], "offer_price": [360_000.0], "fee_usd": [18_000.0],
        "reno_actual_usd": [12_000.0], "holding_cost_usd": [5_000.0], "selling_cost_usd": [12_000.0],
    })
    # 400k - (360k - 18k) - 12k - 5k - 12k = 29k
    assert contribution_margin_usd(home).iloc[0] == pytest.approx(29_000.0)


def test_overall_margin_between_4_and_6_pct(control):
    sold = control.homes[control.homes["resale_date"].notna()]
    cm = contribution_margin_usd(sold).sum() / sold["resale_price"].sum()
    assert 0.04 <= cm <= 0.06


def test_average_sale_near_375k(control):
    sold = control.homes[control.homes["resale_date"].notna()]
    assert 350_000 <= sold["resale_price"].mean() <= 400_000


def test_average_hold_near_120_days(control):
    sold = control.homes[control.homes["resale_date"].notna()]
    assert 105 <= sold["hold_days"].mean() <= 135


def test_q2_to_q3_margin_dip_about_500_bps(control):
    dip_bps = (_quarter_cm(control.homes, 2025, 2) - _quarter_cm(control.homes, 2025, 3)) * 1e4
    assert 425 <= dip_bps <= 575


def test_sold_cohort_cm_by_week_shape(control):
    weekly = sold_cohort_cm(control.homes)
    assert list(weekly.columns) == ["resale_week", "n_sold", "resale_usd", "cm_usd", "cm_pct"]
    assert weekly["resale_week"].is_monotonic_increasing
    assert (weekly["n_sold"] > 0).all()
