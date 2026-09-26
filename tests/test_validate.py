import pytest
from src.validate import (
    validate_timestamps, validate_locations, validate_distance_and_speed,
    validate_fares, validate_categorical_domains, compute_composite_validity
)

def test_valid_duration_not_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    assert not df.iloc[0]["_flag_negative_duration"]

def test_negative_duration_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    assert df.iloc[4]["_flag_negative_duration"]

def test_zero_duration_flagged(sample_trip_df):
    df = sample_trip_df.copy()
    df.loc[0, "tpep_dropoff_datetime"] = df.loc[0, "tpep_pickup_datetime"]
    df = validate_timestamps(df, "2026-07-01", "2026-08-01", 30, 86400)
    assert df.iloc[0]["_flag_negative_duration"]

def test_out_of_range_date_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    assert df.iloc[3]["_flag_date_out_of_range"]

def test_duration_too_short_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    assert df.iloc[8]["_flag_duration_too_short"]

def test_duration_too_long_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    assert df.iloc[9]["_flag_duration_too_long"]

def test_invalid_location_flagged(sample_trip_df):
    df = validate_locations(sample_trip_df, {1, 2, 3, 4, 5})
    assert df.iloc[10]["_flag_invalid_pu_location"]

def test_valid_location_not_flagged(sample_trip_df):
    df = validate_locations(sample_trip_df, {1, 2, 3, 4, 5})
    assert not df.iloc[0]["_flag_invalid_pu_location"]

def test_zero_distance_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    df = validate_distance_and_speed(df, 100.0)
    assert df.iloc[2]["_flag_zero_distance"]

def test_impossible_speed_flagged(sample_trip_df):
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    df = validate_distance_and_speed(df, 100.0)
    assert df.iloc[5]["_flag_impossible_speed"]

def test_negative_fare_flagged(sample_trip_df):
    df = validate_fares(sample_trip_df, 0.05)
    assert df.iloc[1]["_flag_negative_fare"]

def test_negative_total_flagged(sample_trip_df):
    df = validate_fares(sample_trip_df, 0.05)
    assert df.iloc[1]["_flag_negative_total"]

def test_invalid_vendor_flagged(sample_trip_df):
    df = validate_categorical_domains(sample_trip_df, {1, 2}, {1, 2, 3, 4, 5, 6})
    assert df.iloc[6]["_flag_invalid_vendor"]

def test_invalid_ratecode_flagged(sample_trip_df):
    df = validate_categorical_domains(sample_trip_df, {1, 2}, {1, 2, 3, 4, 5, 6})
    assert df.iloc[7]["_flag_invalid_ratecode"]

def test_composite_validity_all_valid(sample_trip_df):
    df = sample_trip_df.iloc[[0]].copy()
    df = validate_timestamps(df, "2026-07-01", "2026-08-01", 30, 86400)
    df = validate_locations(df, {1, 2})
    df = validate_distance_and_speed(df, 100.0)
    df = validate_fares(df, 0.05)
    df = validate_categorical_domains(df, {1, 2}, {1, 2, 3, 4, 5, 6})
    df = compute_composite_validity(df)
    assert df.iloc[0]["is_valid"]

def test_composite_validity_any_flag(sample_trip_df):
    df = sample_trip_df.iloc[[1]].copy()
    df = validate_timestamps(df, "2026-07-01", "2026-08-01", 30, 86400)
    df = validate_locations(df, {1, 2})
    df = validate_distance_and_speed(df, 100.0)
    df = validate_fares(df, 0.05)
    df = validate_categorical_domains(df, {1, 2}, {1, 2, 3, 4, 5, 6})
    df = compute_composite_validity(df)
    assert not df.iloc[0]["is_valid"]

def test_fare_sum_mismatch_excluded_from_validity(sample_trip_df):
    df = sample_trip_df.iloc[[0]].copy()
    df.loc[0, "total_amount"] += 10.0
    
    df = validate_timestamps(df, "2026-07-01", "2026-08-01", 30, 86400)
    df = validate_locations(df, {1, 2})
    df = validate_distance_and_speed(df, 100.0)
    df = validate_fares(df, 0.05)
    df = validate_categorical_domains(df, {1, 2}, {1, 2, 3, 4, 5, 6})
    df = compute_composite_validity(df)
    
    assert df.iloc[0]["_flag_fare_sum_mismatch"]
    assert df.iloc[0]["is_valid"]
