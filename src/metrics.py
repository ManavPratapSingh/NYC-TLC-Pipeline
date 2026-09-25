import pandas as pd
import logging

logger = logging.getLogger(__name__)

def compute_revenue_per_mile(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue per mile by pickup borough."""
    df_filtered = df[df["trip_distance"] > 0]
    if df_filtered.empty or "fare_per_mile" not in df_filtered.columns:
        return pd.DataFrame()
    return df_filtered.groupby("pu_borough").agg(
        mean_fare_per_mile=("fare_per_mile", "mean"),
        median_fare_per_mile=("fare_per_mile", "median"),
        total_trips=("fare_per_mile", "count")
    ).reset_index()

def compute_avg_trip_speed(df: pd.DataFrame) -> pd.DataFrame:
    """Average speed by pickup borough and time_bucket."""
    df_filtered = df[(df["trip_duration_secs"] > 0) & (df["trip_distance"] > 0)]
    if df_filtered.empty or "implied_speed_mph" not in df_filtered.columns:
        return pd.DataFrame()
    return df_filtered.groupby(["pu_borough", "time_bucket"]).agg(
        mean_implied_speed_mph=("implied_speed_mph", "mean")
    ).reset_index()

def compute_tip_percentage(df: pd.DataFrame) -> pd.DataFrame:
    """Tip % for credit card payments only."""
    df_filtered = df[(df["payment_type"] == 1) & (df["fare_amount"] > 0)].copy()
    if df_filtered.empty:
        return pd.DataFrame()
    df_filtered["tip_pct"] = (df_filtered["tip_amount"] / df_filtered["fare_amount"]) * 100
    return df_filtered.groupby("pu_borough").agg(
        mean_tip_pct=("tip_pct", "mean"),
        median_tip_pct=("tip_pct", "median")
    ).reset_index()

def compute_congestion_burden(df: pd.DataFrame) -> pd.DataFrame:
    """Congestion fees as % of total fare by pickup borough."""
    df_filtered = df[df["total_amount"] > 0].copy()
    if df_filtered.empty:
        return pd.DataFrame()
    cong = df_filtered.get("congestion_surcharge", pd.Series(0, index=df_filtered.index)).fillna(0)
    cbd = df_filtered.get("cbd_congestion_fee", pd.Series(0, index=df_filtered.index)).fillna(0)
    df_filtered["congestion_pct"] = ((cong + cbd) / df_filtered["total_amount"]) * 100
    return df_filtered.groupby("pu_borough").agg(
        mean_congestion_pct=("congestion_pct", "mean")
    ).reset_index()

def compute_data_quality_yield(df_full: pd.DataFrame) -> dict:
    """Compute audit metrics on the FULL dataset."""
    total = len(df_full)
    valid = int(df_full["is_valid"].sum()) if "is_valid" in df_full.columns else total
    invalid = total - valid
    yield_pct = (valid / total * 100) if total > 0 else 0.0
    
    flag_cols = [c for c in df_full.columns if c.startswith("_flag_")]
    flag_breakdown = {col: int(df_full[col].sum()) for col in flag_cols}
    
    return {
        "total_rows": total,
        "valid_rows": valid,
        "invalid_rows": invalid,
        "yield_pct": yield_pct,
        "flag_breakdown": flag_breakdown
    }

def generate_metrics_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 4 operational KPIs and combine into a single wide summary DataFrame."""
    rpm = compute_revenue_per_mile(df)
    spd = compute_avg_trip_speed(df)
    tip = compute_tip_percentage(df)
    cgb = compute_congestion_burden(df)
    
    if rpm.empty:
        return pd.DataFrame()
        
    summary = rpm.copy()
    
    if not tip.empty:
        summary = pd.merge(summary, tip, on="pu_borough", how="left")
    if not cgb.empty:
        summary = pd.merge(summary, cgb, on="pu_borough", how="left")
        
    if not spd.empty:
        spd_pivot = spd.pivot(index="pu_borough", columns="time_bucket", values="mean_implied_speed_mph").reset_index()
        spd_pivot.columns = ["pu_borough"] + [f"speed_{c}" for c in spd_pivot.columns if c != "pu_borough"]
        summary = pd.merge(summary, spd_pivot, on="pu_borough", how="left")
        
    return summary
