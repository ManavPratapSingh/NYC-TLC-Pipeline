import pytest
import pandas as pd
from src.transform import enrich_with_zones, classify_trip_type, bucket_time_of_day, add_day_of_week

def test_zone_enrichment_adds_columns(sample_trip_df, sample_zone_df):
    df = enrich_with_zones(sample_trip_df, sample_zone_df)
    for col in ["pu_borough", "pu_zone", "pu_service_zone", "do_borough", "do_zone", "do_service_zone"]:
        assert col in df.columns

def test_zone_enrichment_fills_unknown(sample_trip_df, sample_zone_df):
    df = sample_trip_df.copy()
    df.loc[0, "PULocationID"] = 999
    df = enrich_with_zones(df, sample_zone_df)
    assert df.loc[0, "pu_borough"] == "Unknown"

def test_airport_trip_classification(sample_trip_df, sample_zone_df):
    df = sample_trip_df.copy()
    df.loc[0, "PULocationID"] = 3
    df.loc[0, "DOLocationID"] = 1
    df = enrich_with_zones(df, sample_zone_df)
    df = classify_trip_type(df)
    assert df.loc[0, "is_airport_trip"]

def test_cross_borough_classification(sample_trip_df, sample_zone_df):
    df = sample_trip_df.copy()
    df.loc[0, "PULocationID"] = 1
    df.loc[0, "DOLocationID"] = 3
    df = enrich_with_zones(df, sample_zone_df)
    df = classify_trip_type(df)
    assert df.loc[0, "is_cross_borough"]

def test_within_zone_classification(sample_trip_df, sample_zone_df):
    df = sample_trip_df.copy()
    df.loc[0, "PULocationID"] = 1
    df.loc[0, "DOLocationID"] = 1
    df = enrich_with_zones(df, sample_zone_df)
    df = classify_trip_type(df)
    assert df.loc[0, "is_within_zone"]

def test_time_bucket_night(sample_trip_df):
    df = sample_trip_df.copy()
    df.loc[0, "tpep_pickup_datetime"] = pd.Timestamp("2026-07-01 22:00:00")
    df = bucket_time_of_day(df)
    assert df.loc[0, "time_bucket"] == "night"

def test_time_bucket_morning_rush(sample_trip_df):
    df = sample_trip_df.copy()
    df.loc[0, "tpep_pickup_datetime"] = pd.Timestamp("2026-07-01 09:00:00")
    df = bucket_time_of_day(df)
    assert df.loc[0, "time_bucket"] == "morning_rush"

def test_day_of_week_added(sample_trip_df):
    df = add_day_of_week(sample_trip_df)
    assert "day_of_week" in df.columns
    assert "is_weekend" in df.columns
