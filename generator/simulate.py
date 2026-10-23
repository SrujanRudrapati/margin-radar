"""Home-level funnel simulation. Synthetic data — not Opendoor data.

Funnel: offer → contract → close → assessment → renovation → list → price cuts → resale.
All randomness is drawn up front in a fixed order, so a run with scenarios and a control
run with the same seed share every draw: homes outside a scenario's scope are identical.
Day offsets are floats relative to START_DATE; NaN means "not happened by the cutoff".
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from generator import config as C
from generator.scenarios import Scenario, effect_multiplier

STAGES = (
    "contract", "close", "assessment", "reno_start", "reno_complete",
    "list", "first_buyer_offer", "resale",
)


@dataclass(frozen=True)
class SimOutput:
    homes: pd.DataFrame
    price_cuts: pd.DataFrame


def simulate(seed: int, scenarios: Sequence[Scenario] = (), cutoff_week: int = C.N_WEEKS) -> SimOutput:
    draws = _draw(np.random.default_rng(seed))
    homes = _offers(draws)
    days = _funnel(draws, homes, scenarios)
    days |= _renovation_and_listing(draws, days)
    resale = _resale(draws, homes, days, scenarios)
    days |= resale.pop("days")
    cutoff_day = 7 * cutoff_week - 1
    censored = _censor(days, cutoff_day)
    cut_days = censored["list"][:, None] + C.CUT_EVERY_DAYS * np.arange(1, C.MAX_CUTS + 1)
    cut_mask = (np.arange(1, C.MAX_CUTS + 1) <= resale["n_cuts"][:, None]) & (cut_days <= cutoff_day)
    frame = _assemble(draws, homes, resale, censored, days, cutoff_day, cut_mask)
    cuts = _price_cuts(frame["home_id"].to_numpy(), cut_days, cut_mask, draws["cut_depths"])
    keep = frame["offer_week"] < cutoff_week
    kept_cuts = cuts[cuts["home_id"].isin(frame.loc[keep, "home_id"])]
    return SimOutput(frame[keep].reset_index(drop=True), kept_cuts.reset_index(drop=True))


def _draw(rng: np.random.Generator) -> dict[str, np.ndarray]:
    weeks = np.arange(C.N_WEEKS)
    woy = np.array([(C.START_DATE + timedelta(weeks=int(w))).isocalendar().week for w in weeks])
    season = 1 + C.VOLUME_SEASON_AMPLITUDE * np.cos(2 * np.pi * (woy - C.VOLUME_PEAK_WEEK_OF_YEAR) / 52)
    offer_week = np.repeat(weeks, rng.poisson(C.BASE_WEEKLY_OFFERS * season))
    n = len(offer_week)
    draws = {
        "offer_week": offer_week,
        "offer_day": offer_week * 7 + rng.integers(0, 7, n),
        "market_idx": rng.choice(len(C.MARKETS), n, p=C.MARKET_WEIGHTS),
        "product_idx": rng.choice(len(C.PRODUCTS), n, p=C.PRODUCT_WEIGHTS),
        "valuation_z": rng.standard_normal(n),
        "spread": np.clip(rng.normal(C.SPREAD_MEAN, C.SPREAD_SD, n), 0.03, 0.10),
        "reno_share_z": rng.standard_normal(n),
    }
    for name in ("u_accept", "u_inspect", "u_decline", "u_fall"):
        draws[name] = rng.random(n)
    for stage, (lo, hi) in C.LAG_DAYS.items():
        draws[f"lag_{stage}"] = rng.integers(lo, hi, n)
    draws |= {
        "reno_days": rng.gamma(C.RENO_DAYS_SHAPE, C.RENO_DAYS_SCALE, n),
        "reno_z": rng.standard_normal(n),
        "dtfo_base": rng.gamma(C.DTFO_SHAPE, C.DTFO_SCALE, n),
        "showing_noise": rng.gamma(4.0, 0.25, n),
        "value_noise": np.exp(C.RESALE_NOISE_LOG_SD * rng.standard_normal(n)),
        "cut_depths": rng.uniform(*C.CUT_DEPTH_RANGE, (n, C.MAX_CUTS)),
    }
    return draws


def _offers(d: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    medians = np.array(C.MARKET_MEDIAN_VALUATION, dtype=float)[d["market_idx"]]
    valuation = np.round(medians * np.exp(C.VALUATION_LOG_SD * d["valuation_z"]), -2)
    band_names = list(C.BANDS)
    band = np.select([valuation < hi for _, hi in C.BANDS.values()], band_names, default=band_names[-1])
    share = np.vectorize(C.RENO_SHARE_BY_BAND.get)(band)
    sd = C.RENO_SHARE_LOG_SD
    reno_estimate = np.round(valuation * share * np.exp(sd * d["reno_share_z"] - sd**2 / 2), 2)
    offer_price = np.round(valuation * (1 - d["spread"]) - reno_estimate, 2)
    return {
        "market": np.array(C.MARKETS)[d["market_idx"]],
        "band": band,
        "product": np.array(C.PRODUCTS)[d["product_idx"]],
        "model_valuation": valuation,
        "reno_estimate_usd": reno_estimate,
        "offer_price": offer_price,
    }


def _funnel(d: dict[str, np.ndarray], h: dict[str, np.ndarray], sc: Sequence[Scenario]) -> dict[str, np.ndarray]:
    p_accept = C.BASE_ACCEPT_RATE * np.exp(-C.ACCEPT_SPREAD_SENSITIVITY * (d["spread"] - C.SPREAD_MEAN))
    p_accept *= effect_multiplier(sc, "conversion", h["market"], h["band"], d["offer_week"])
    accepted = d["u_accept"] < np.minimum(p_accept, C.MAX_ACCEPT_RATE)
    in_person = d["u_inspect"] < C.IN_PERSON_SHARE
    decline_rate = np.where(in_person, C.COMPANY_DECLINE_RATE["in_person"], C.COMPANY_DECLINE_RATE["seller_led"])
    company_declined = accepted & (d["u_decline"] < decline_rate)
    fell_through = accepted & ~company_declined & (d["u_fall"] < C.FALL_THROUGH_RATE)
    closes = accepted & ~company_declined & ~fell_through
    contract = np.where(accepted, d["offer_day"] + d["lag_contract"], np.nan)
    outcome = np.select([closes, company_declined, fell_through], ["closed", "company_declined", "fell_through"],
                        default="seller_declined")
    return {
        "offer": d["offer_day"].astype(float),
        "contract": contract,
        "cancel": np.where(company_declined | fell_through, contract + d["lag_cancel"], np.nan),
        "close": np.where(closes, contract + d["lag_close"], np.nan),
        "_outcome": outcome,
        "_in_person": in_person,
    }


def _renovation_and_listing(d: dict[str, np.ndarray], days: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    assessment = days["close"] + d["lag_assessment"]
    reno_start = assessment + d["lag_reno_start"]
    reno_complete = reno_start + np.round(d["reno_days"])
    return {
        "assessment": assessment,
        "reno_start": reno_start,
        "reno_complete": reno_complete,
        "list": reno_complete + d["lag_list"],
    }


def _resale(d: dict[str, np.ndarray], h: dict[str, np.ndarray], days: dict[str, np.ndarray],
            sc: Sequence[Scenario]) -> dict:
    week = lambda day: np.floor(day / 7)  # noqa: E731 — NaN-preserving week index
    list_month = _month(days["list"])
    dtfo_normal = d["dtfo_base"] * (1 + C.DTFO_SEASON_AMPLITUDE * np.cos(2 * np.pi * (list_month - 10) / 12))
    dtfo_mult = effect_multiplier(sc, "days_to_first_offer", h["market"], h["band"], week(days["list"]))
    dtfo = np.maximum(1, np.round(dtfo_normal * dtfo_mult))
    first_offer = days["list"] + dtfo
    resale = first_offer + d["lag_resale_close"]
    n_cuts = np.minimum(np.floor((dtfo - 1) / C.CUT_EVERY_DAYS), C.MAX_CUTS).astype(int)
    total_cut = np.take_along_axis(np.cumsum(d["cut_depths"], axis=1), np.maximum(n_cuts - 1, 0)[:, None], 1)[:, 0]
    total_cut = np.where(n_cuts > 0, total_cut, 0.0)
    season = np.vectorize(C.PRICE_SEASON_BY_MONTH.get)(_month(resale))
    value_mult = effect_multiplier(sc, "resale_vs_model", h["market"], h["band"], d["offer_week"])
    true_value = h["model_valuation"] * (1 + season) * d["value_noise"] * value_mult
    return {
        "days": {"first_buyer_offer": first_offer, "resale": resale},
        "dtfo": dtfo,
        "showings": np.round(dtfo_normal * C.SHOWINGS_PER_DAY * d["showing_noise"]),
        "n_cuts": n_cuts,
        "resale_price": np.round(true_value * (1 - C.CUT_PASS_THROUGH * total_cut), 2),
        "reno_mult": effect_multiplier(sc, "reno_overrun", h["market"], h["band"], week(days["reno_start"])),
    }


def _month(day: np.ndarray) -> np.ndarray:
    dates = pd.Timestamp(C.START_DATE) + pd.to_timedelta(np.nan_to_num(day), unit="D")
    return np.asarray(dates.month)


def _censor(days: dict[str, np.ndarray], cutoff_day: int) -> dict[str, np.ndarray]:
    out = {"offer": days["offer"]}
    valid = np.ones(len(days["offer"]), dtype=bool)
    for stage in STAGES:
        valid = valid & (days[stage] <= cutoff_day)
        out[stage] = np.where(valid, days[stage], np.nan)
    out["cancel"] = np.where(days["cancel"] <= cutoff_day, days["cancel"], np.nan)
    return out


def _dates(day: np.ndarray) -> pd.Series:
    return pd.Series(pd.Timestamp(C.START_DATE) + pd.to_timedelta(day, unit="D"))


def _assemble(d: dict, h: dict, r: dict, cen: dict, raw: dict, cutoff_day: int, cut_mask: np.ndarray) -> pd.DataFrame:
    n = len(d["offer_day"])
    has = {stage: ~np.isnan(cen[stage]) for stage in STAGES}
    in_person = raw["_in_person"]
    mu, sd = (np.where(in_person, C.RENO_OVERRUN_LOG["in_person"][i], C.RENO_OVERRUN_LOG["seller_led"][i])
              for i in (0, 1))
    reno_actual = np.round(h["reno_estimate_usd"] * np.exp(mu + sd * d["reno_z"]) * r["reno_mult"], 2)
    outcome = raw["_outcome"]
    resolved = np.select([outcome == "closed", np.isin(outcome, ["fell_through", "company_declined"])],
                         [raw["close"], raw["cancel"]], default=raw["offer"] + C.OFFER_EXPIRY_DAYS)
    sold = has["resale"]
    resale_price = np.where(sold, r["resale_price"], np.nan)
    hold_days = cen["resale"] - cen["close"]
    listed = has["list"]
    return pd.DataFrame({
        "home_id": [f"H{i:06d}" for i in range(n)],
        "market": h["market"], "band": h["band"], "product": h["product"],
        "segment": [f"{m}-{b}-{p}" for m, b, p in zip(h["market"], h["band"], h["product"])],
        "offer_week": d["offer_week"],
        "offer_date": _dates(cen["offer"]),
        "model_valuation": h["model_valuation"],
        "spread_pct": d["spread"],
        "reno_estimate_usd": h["reno_estimate_usd"],
        "offer_price": h["offer_price"],
        "outcome": np.where(resolved <= cutoff_day, outcome, "open"),
        "inspection_type": pd.Series(np.where(in_person, "in_person", "seller_led")).where(has["contract"]),
        "contract_date": _dates(cen["contract"]),
        "cancel_date": _dates(cen["cancel"]),
        "close_date": _dates(cen["close"]),
        "fee_usd": np.where(has["close"], np.round(C.FEE_PCT * h["offer_price"], 2), np.nan),
        "assessment_date": _dates(cen["assessment"]),
        "reno_start_date": _dates(cen["reno_start"]),
        "reno_complete_date": _dates(cen["reno_complete"]),
        "reno_actual_usd": np.where(has["reno_complete"], reno_actual, np.nan),
        "list_date": _dates(cen["list"]),
        "list_price": np.where(listed, np.round(h["model_valuation"] * (1 + C.LIST_MARKUP), -2), np.nan),
        "first_buyer_offer_date": _dates(cen["first_buyer_offer"]),
        "days_to_first_offer": pd.array(np.where(has["first_buyer_offer"], r["dtfo"], np.nan)).astype("Int64"),
        "showings": pd.array(np.where(has["first_buyer_offer"], r["showings"], np.nan)).astype("Int64"),
        "price_cut_count": pd.array(np.where(listed, cut_mask.sum(1), np.nan)).astype("Int64"),
        "price_cut_depth_pct": np.where(listed, (d["cut_depths"] * cut_mask).sum(1), np.nan),
        "resale_date": _dates(cen["resale"]),
        "resale_price": resale_price,
        "hold_days": pd.array(hold_days).astype("Int64"),
        "holding_cost_usd": np.round(C.HOLDING_COST_PER_DAY_PCT * h["offer_price"] * hold_days, 2),
        "selling_cost_usd": np.round(C.SELLING_COST_PCT * resale_price, 2),
    })


def _price_cuts(home_id: np.ndarray, cut_days: np.ndarray, cut_mask: np.ndarray,
                depths: np.ndarray) -> pd.DataFrame:
    rows, cols = np.nonzero(cut_mask)
    return pd.DataFrame({
        "home_id": home_id[rows],
        "cut_number": cols + 1,
        "cut_date": _dates(cut_days[rows, cols]),
        "cut_pct": depths[rows, cols],
    })
