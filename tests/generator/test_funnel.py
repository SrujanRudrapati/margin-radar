import pandas as pd

from generator.config import FEE_PCT, cutoff_date

STAGES = [
    "offer_date", "contract_date", "close_date", "assessment_date", "reno_start_date",
    "reno_complete_date", "list_date", "first_buyer_offer_date", "resale_date",
]
OUTCOMES = {"seller_declined", "fell_through", "company_declined", "closed", "open"}  # open = unresolved at cutoff


def test_outcomes_include_fall_through_and_company_declined(control):
    h = control.homes
    assert set(h["outcome"]) == OUTCOMES
    contracts = h[h["contract_date"].notna()]
    shares = contracts["outcome"].value_counts(normalize=True)
    assert shares["fell_through"] >= 0.02
    assert shares["company_declined"] >= 0.02
    assert 0.25 <= h["contract_date"].notna().mean() <= 0.45


def test_cancelled_contracts_never_close(control):
    h = control.homes
    cancelled = h[h["outcome"].isin(["fell_through", "company_declined"])]
    assert cancelled["cancel_date"].notna().all()
    assert cancelled["close_date"].isna().all()
    assert (cancelled["cancel_date"] >= cancelled["contract_date"]).all()
    declined = h[h["outcome"] == "seller_declined"]
    assert declined[["contract_date", "close_date"]].isna().all().all()


def test_stage_timestamps_are_ordered(control):
    sold = control.homes[control.homes["resale_date"].notna()]
    assert len(sold) > 1_000
    for earlier, later in zip(STAGES, STAGES[1:]):
        assert (sold[later] >= sold[earlier]).all(), (earlier, later)


def test_no_event_after_cutoff(control):
    h = control.homes
    cutoff = pd.Timestamp(cutoff_date())
    for col in STAGES + ["cancel_date"]:
        assert (h[col].dropna() <= cutoff).all(), col
    assert (control.price_cuts["cut_date"] <= cutoff).all()


def test_later_stage_null_when_earlier_null(control):
    h = control.homes
    for earlier, later in zip(STAGES, STAGES[1:]):
        assert h.loc[h[earlier].isna(), later].isna().all(), (earlier, later)


def test_fee_is_five_percent_of_offer(control):
    closed = control.homes[control.homes["outcome"] == "closed"]
    assert FEE_PCT == 0.05
    assert ((closed["fee_usd"] - 0.05 * closed["offer_price"]).abs() < 0.01).all()


def test_required_fields_present(control):
    required = {
        "spread_pct", "model_valuation", "resale_price", "days_to_first_offer", "showings",
        "price_cut_count", "price_cut_depth_pct", "reno_estimate_usd", "reno_actual_usd",
        "inspection_type", "holding_cost_usd", "hold_days", "market", "band", "product",
    }
    assert required <= set(control.homes.columns)
    assert set(control.homes["inspection_type"].dropna()) == {"seller_led", "in_person"}


def test_seller_led_inspection_has_noisier_reno_estimates(control):
    h = control.homes.dropna(subset=["reno_actual_usd"])
    ratio = h["reno_actual_usd"] / h["reno_estimate_usd"]
    by_type = ratio.groupby(h["inspection_type"]).std()
    assert by_type["seller_led"] > 1.5 * by_type["in_person"]


def test_price_cuts_table_matches_summary(control):
    h = control.homes.set_index("home_id")
    cuts = control.price_cuts
    per_home = cuts.groupby("home_id").agg(n=("cut_pct", "size"), depth=("cut_pct", "sum"))
    listed = h[h["list_date"].notna()]
    n = per_home["n"].reindex(listed.index, fill_value=0)
    assert (n == listed["price_cut_count"]).all()
    joined = cuts.join(h[["list_date", "first_buyer_offer_date"]], on="home_id")
    assert (joined["cut_date"] > joined["list_date"]).all()
    has_offer = joined["first_buyer_offer_date"].notna()
    assert (joined.loc[has_offer, "cut_date"] < joined.loc[has_offer, "first_buyer_offer_date"]).all()
