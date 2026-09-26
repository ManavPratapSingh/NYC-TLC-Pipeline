import pytest
import numpy as np
import pandas as pd
from src.clean import standardize_schema, handle_missing_values, derive_trip_metrics, clean_pipeline

def test_schema_standardization_types(sample_trip_df):
    df = standardize_schema(sample_trip_df)
    assert pd.api.types.is_datetime64_any_dtype(df["tpep_pickup_datetime"])
    assert df["VendorID"].dtype == "int32"
    assert df["fare_amount"].dtype == "float64"

def test_missing_value_imputation(sample_trip_df):
    df = sample_trip_df.copy()
    df.loc[0, "passenger_count"] = np.nan
    df = handle_missing_values(df)
    assert df.loc[0, "passenger_count"] == 1.0

def test_derived_duration_column(sample_trip_df):
    from src.validate import validate_timestamps
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    df = derive_trip_metrics(df)
    assert df.iloc[0]["trip_duration_mins"] == pytest.approx(15.0)

def test_derived_fare_per_mile(sample_trip_df):
    from src.validate import validate_timestamps
    df = validate_timestamps(sample_trip_df, "2026-07-01", "2026-08-01", 30, 86400)
    df = derive_trip_metrics(df)
    
    assert df.iloc[0]["fare_per_mile"] == pytest.approx(13.3 / 3.0)
    assert pd.isna(df.iloc[2]["fare_per_mile"])

def test_clean_pipeline_returns_tuple(sample_trip_df, sample_zone_df):
    result = clean_pipeline(sample_trip_df, sample_zone_df)
    assert isinstance(result, tuple)
    assert isinstance(result[0], pd.DataFrame)
    assert isinstance(result[1], dict)

def test_clean_pipeline_audit_dict(sample_trip_df, sample_zone_df):
    _, audit = clean_pipeline(sample_trip_df, sample_zone_df)
    assert "total_rows" in audit
    assert "valid_rows" in audit
    assert "invalid_rows" in audit
    assert "flag_counts" in audit
    assert "null_profile" in audit
