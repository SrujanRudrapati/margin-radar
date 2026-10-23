"""Contribution margin on sold homes (excludes financing, per the CONTEXT profit formula)."""
import pandas as pd

from generator.config import START_DATE


def week_index(dates: pd.Series) -> pd.Series:
    return (dates - pd.Timestamp(START_DATE)).dt.days // 7


def contribution_margin_usd(homes: pd.DataFrame) -> pd.Series:
    cash_paid = homes["offer_price"] - homes["fee_usd"]
    return (
        homes["resale_price"] - cash_paid - homes["reno_actual_usd"]
        - homes["holding_cost_usd"] - homes["selling_cost_usd"]
    )


def sold_cohort_cm(homes: pd.DataFrame) -> pd.DataFrame:
    """Contribution margin of homes sold in each week."""
    sold = homes[homes["resale_date"].notna()]
    frame = pd.DataFrame({
        "resale_week": week_index(sold["resale_date"]).astype(int),
        "resale_usd": sold["resale_price"],
        "cm_usd": contribution_margin_usd(sold),
    })
    weekly = (
        frame.groupby("resale_week")
        .agg(n_sold=("cm_usd", "size"), resale_usd=("resale_usd", "sum"), cm_usd=("cm_usd", "sum"))
        .reset_index()
    )
    return weekly.assign(cm_pct=weekly["cm_usd"] / weekly["resale_usd"])
