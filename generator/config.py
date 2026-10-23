"""Generator constants. Synthetic data — not Opendoor data.

Calibration targets (from the user's Phase 1 spec and CLAUDE.md):
~20k offers over 78 weeks, ~$375K avg sale, 5% fee, ~120-day hold,
overall contribution margin 4–6%, spring volume peak, ~500 bps Q2→Q3 margin dip.
"""
from datetime import date, timedelta
from math import inf

START_DATE = date(2025, 1, 6)  # Monday; week 0
N_WEEKS = 78

MARKETS = ("M01", "M02", "M03", "M04", "M05", "M06")
MARKET_WEIGHTS = (0.22, 0.18, 0.17, 0.16, 0.14, 0.13)
MARKET_MEDIAN_VALUATION = (345_000, 360_000, 370_000, 350_000, 365_000, 340_000)
VALUATION_LOG_SD = 0.33

BANDS = {"B1": (0, 300_000), "B2": (300_000, 450_000), "B3": (450_000, inf)}
PRODUCTS = ("cash", "CNML")
PRODUCT_WEIGHTS = (0.75, 0.25)
SEGMENTS = tuple(f"{m}-{b}-{p}" for m in MARKETS for b in BANDS for p in PRODUCTS)

BASE_WEEKLY_OFFERS = 256  # x 78 weeks ≈ 20k offers
VOLUME_SEASON_AMPLITUDE = 0.15  # offers peak mid-April
VOLUME_PEAK_WEEK_OF_YEAR = 16

# Pricing: offer = model_valuation * (1 - spread) - reno_estimate
SPREAD_MEAN = 0.066
SPREAD_SD = 0.008
RENO_SHARE_BY_BAND = {"B1": 0.055, "B2": 0.04, "B3": 0.03}  # reno estimate / valuation
RENO_SHARE_LOG_SD = 0.30
FEE_PCT = 0.05

# Funnel conversion
BASE_ACCEPT_RATE = 0.36
ACCEPT_SPREAD_SENSITIVITY = 25.0  # p *= exp(-k * (spread - SPREAD_MEAN))
MAX_ACCEPT_RATE = 0.95
OFFER_EXPIRY_DAYS = 7
IN_PERSON_SHARE = 0.35
COMPANY_DECLINE_RATE = {"in_person": 0.06, "seller_led": 0.03}
FALL_THROUGH_RATE = 0.07

# Renovation: actual / estimate ~ lognormal(mu, sd) by inspection type
RENO_OVERRUN_LOG = {"seller_led": (0.04, 0.18), "in_person": (0.0, 0.07)}
RENO_DAYS_SHAPE, RENO_DAYS_SCALE = 4.0, 10.0

# Resale
DTFO_SHAPE, DTFO_SCALE = 2.0, 16.0  # days to first buyer offer, before seasonality
DTFO_SEASON_AMPLITUDE = 0.2  # slowest in October, fastest in April
CUT_EVERY_DAYS = 21  # a price cut every 21 days without a buyer offer
CUT_DEPTH_RANGE = (0.01, 0.02)
MAX_CUTS = 12
CUT_PASS_THROUGH = 0.75  # share of list-price cuts that reach the realized price
LIST_MARKUP = 0.02
RESALE_NOISE_LOG_SD = 0.035
SHOWINGS_PER_DAY = 0.35  # showings before first offer, at normal demand
# Realized price vs (seasonally naive) model valuation, by resale month.
PRICE_SEASON_BY_MONTH = {
    1: 0.000, 2: 0.005, 3: 0.015, 4: 0.020, 5: 0.025, 6: 0.015,
    7: -0.020, 8: -0.030, 9: -0.030, 10: -0.015, 11: -0.005, 12: 0.000,
}

# Costs (contribution margin excludes financing)
HOLDING_COST_PER_DAY_PCT = 0.00012  # of offer price: tax, insurance, utilities, HOA
SELLING_COST_PCT = 0.03  # of resale price

# Day-offset ranges (inclusive low, exclusive high) between stages
LAG_DAYS = {
    "contract": (1, 8),
    "cancel": (5, 21),
    "close": (14, 31),
    "assessment": (1, 6),
    "reno_start": (1, 6),
    "list": (3, 11),
    "resale_close": (25, 41),
}


def cutoff_date(cutoff_week: int = N_WEEKS) -> date:
    """Last day covered by the data."""
    return START_DATE + timedelta(days=7 * cutoff_week - 1)
