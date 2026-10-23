import pandas as pd


def _weekly_offers(homes):
    return homes.groupby(homes["offer_date"].dt.to_period("W-SUN")).size()


def test_spring_offer_peak(control):
    weekly = _weekly_offers(control.homes)
    idx = weekly.index.start_time
    spring = weekly[(idx >= "2025-03-01") & (idx < "2025-06-01")].mean()
    winter = weekly[(idx >= "2025-11-01") & (idx < "2026-02-01")].mean()
    assert spring >= 1.15 * winter


def test_spring_listings_get_offers_faster_than_fall(control):
    h = control.homes.dropna(subset=["days_to_first_offer"])
    month = h["list_date"].dt.month
    assert h.loc[month.isin([3, 4, 5]), "days_to_first_offer"].mean() < \
        h.loc[month.isin([9, 10, 11]), "days_to_first_offer"].mean()


def test_no_seasonality_in_spread(control):
    # Pricing policy is flat; seasonality must come from the market, not from us.
    h = control.homes
    by_q = h.groupby(h["offer_date"].dt.quarter)["spread_pct"].mean()
    assert by_q.max() - by_q.min() < 0.002
