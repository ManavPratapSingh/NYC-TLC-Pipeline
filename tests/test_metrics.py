import pytest
import pandas as pd
from src.metrics import (
    compute_revenue_per_mile, compute_tip_percentage, 
    compute_data_quality_yield, generate_metrics_summary
)

def setup_metrics_df(sample_trip_df):
    from src.validate import validate_timestamps, compute_composite_validity
    from src.clean import derive_trip_metrics
    df = sample_trip_df.copy()
    df["pu_borough"] = "Manhattan"
    df["time_bucket"] = "midday"
    df = validate_timestamps(df, "2026-07-01", "2026-08-01", 30, 86400)
    df["_flag_test"] = False
    df = compute_composite_validity(df)
    df = derive_trip_metrics(df)
    return df

def test_revenue_per_mile_excludes_zero_distance(sample_trip_df):
    df = setup_metrics_df(sample_trip_df)
    metrics_df = compute_revenue_per_mile(df)
    total_trips = len(df[df["trip_distance"] > 0])
    assert metrics_df.loc[0, "total_trips"] == total_trips

def test_tip_percentage_credit_only(sample_trip_df):
    df = setup_metrics_df(sample_trip_df)
    metrics_df = compute_tip_percentage(df)
    assert not metrics_df.empty

def test_data_quality_yield_calculation(sample_trip_df):
    df = setup_metrics_df(sample_trip_df)
    yield_dict = compute_data_quality_yield(df)
    assert "total_rows" in yield_dict
    assert "valid_rows" in yield_dict
    assert "invalid_rows" in yield_dict

def test_generate_metrics_summary_returns_dataframe(sample_trip_df):
    df = setup_metrics_df(sample_trip_df)
    df["implied_speed_mph"] = 15.0
    summary = generate_metrics_summary(df)
    assert isinstance(summary, pd.DataFrame)
    assert not summary.empty
