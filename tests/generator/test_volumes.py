from generator.config import BANDS, MARKETS, N_WEEKS, PRODUCTS, SEGMENTS
from generator.simulate import simulate


def test_segments_are_markets_x_bands_x_products():
    assert len(MARKETS) == 6 and len(BANDS) == 3 and PRODUCTS == ("cash", "CNML")
    assert len(SEGMENTS) == 36
    assert "M02-B2-cash" in SEGMENTS


def test_about_20k_offers_over_78_weeks(control):
    homes = control.homes
    assert N_WEEKS == 78
    assert 18_000 <= len(homes) <= 22_000
    assert homes["offer_week"].min() == 0 and homes["offer_week"].max() == N_WEEKS - 1


def test_every_segment_has_offers(control):
    counts = control.homes["segment"].value_counts()
    assert set(counts.index) == set(SEGMENTS)
    assert counts.min() >= 50


def test_same_seed_is_deterministic():
    a, b = simulate(7), simulate(7)
    assert a.homes.equals(b.homes)
    assert a.price_cuts.equals(b.price_cuts)


def test_different_seed_differs():
    assert not simulate(7).homes.equals(simulate(8).homes)
