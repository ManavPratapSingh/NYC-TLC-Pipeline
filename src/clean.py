"""Cleaning module — schema standardization, missing value handling, and pipeline orchestration."""

import pandas as pd
import numpy as np
import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    EXPECTED_DATE_MIN, EXPECTED_DATE_MAX,
    MIN_TRIP_DURATION_SECS, MAX_TRIP_DURATION_SECS,
    MAX_SPEED_MPH, VALID_VENDOR_IDS, VALID_RATECODE_IDS,
    FARE_SUM_TOLERANCE,
)
from src.validate import (
    profile_nulls,
    validate_timestamps,
    validate_locations,
    validate_distance_and_speed,
    validate_fares,
    validate_categorical_domains,
    compute_composite_validity,
)

logger = logging.getLogger(__name__)


def standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns to proper types.

    - Timestamps to datetime64[us]
    - VendorID, PULocationID, DOLocationID to int32
    - payment_type to int64
    - All monetary columns to float64
    - store_and_fwd_flag to string

    Args:
        df: Raw DataFrame.

    Returns:
        Copy with standardized types.
    """
    df = df.copy()

    # Timestamps
    for col in ["tpep_pickup_datetime", "tpep_dropoff_datetime"]:
        df[col] = pd.to_datetime(df[col])

    # Integer columns (safe for non-null columns)
    for col in ["VendorID", "PULocationID", "DOLocationID"]:
        df[col] = df[col].astype("int32")

    df["payment_type"] = df["payment_type"].astype("int64")

    # Monetary columns to float64
    monetary = [
        "fare_amount", "extra", "mta_tax", "tip_amount",
        "tolls_amount", "improvement_surcharge", "total_amount",
        "congestion_surcharge", "Airport_fee", "cbd_congestion_fee",
    ]
    for col in monetary:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # store_and_fwd_flag to string
    if "store_and_fwd_flag" in df.columns:
        df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype(str)

    logger.info("Schema standardized")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Impute missing values with logging.

    Imputation rules:
        - passenger_count: fill NaN with 1.0 (median)
        - RatecodeID: fill NaN with 1.0 (mode / standard rate)
        - congestion_surcharge: fill NaN with 0.0
        - Airport_fee: fill NaN with 0.0
        - store_and_fwd_flag: fill NaN / 'nan' with 'N'

    Args:
        df: DataFrame with potential nulls.

    Returns:
        DataFrame with imputed values.
    """
    df = df.copy()

    imputation_map = {
        "passenger_count": 1.0,
        "RatecodeID": 1.0,
        "congestion_surcharge": 0.0,
        "Airport_fee": 0.0,
    }

    for col, fill_val in imputation_map.items():
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                df[col] = df[col].fillna(fill_val)
                logger.info(f"Imputed {null_count:,} nulls in '{col}' with {fill_val}")

    # store_and_fwd_flag: handle both NaN and string 'nan'
    if "store_and_fwd_flag" in df.columns:
        mask = df["store_and_fwd_flag"].isin([None, "nan", "None", "<NA>"]) | df[
            "store_and_fwd_flag"
        ].isna()
        count = mask.sum()
        if count > 0:
            df.loc[mask, "store_and_fwd_flag"] = "N"
            logger.info(f"Imputed {count:,} nulls in 'store_and_fwd_flag' with 'N'")

    return df


def derive_trip_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns for downstream analysis.

    Adds:
        - trip_duration_mins: trip_duration_secs / 60
        - fare_per_mile: total_amount / trip_distance (NaN where distance <= 0)

    Args:
        df: DataFrame with trip_duration_secs and trip_distance.

    Returns:
        DataFrame with added derived columns.
    """
    df = df.copy()

    if "trip_duration_secs" in df.columns:
        df["trip_duration_mins"] = df["trip_duration_secs"] / 60.0

    df["fare_per_mile"] = np.where(
        df["trip_distance"] > 0,
        df["total_amount"] / df["trip_distance"],
        np.nan,
    )

    logger.info("Derived trip metrics computed (trip_duration_mins, fare_per_mile)")
    return df


def clean_pipeline(
    df: pd.DataFrame, zone_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Full cleaning orchestration.

    Pipeline stages:
        1. standardize_schema
        2. handle_missing_values
        3. validate_timestamps
        4. validate_locations
        5. validate_distance_and_speed
        6. validate_fares
        7. validate_categorical_domains
        8. compute_composite_validity
        9. derive_trip_metrics

    Args:
        df: Raw trip DataFrame.
        zone_df: Zone lookup DataFrame (for valid location IDs).

    Returns:
        Tuple of (cleaned_df, audit_dict) where audit_dict has counts per flag.
    """
    logger.info(f"Starting clean pipeline on {len(df):,} rows")

    # 1. Null profiling (informational only)
    null_profile = profile_nulls(df)
    logger.info(f"Null profile summary:\n{null_profile[null_profile['null_count'] > 0].to_string()}")

    # 2. Schema standardization
    df = standardize_schema(df)

    # 3. Missing value handling
    df = handle_missing_values(df)

    # 4. Timestamp validation
    df = validate_timestamps(
        df, EXPECTED_DATE_MIN, EXPECTED_DATE_MAX,
        MIN_TRIP_DURATION_SECS, MAX_TRIP_DURATION_SECS,
    )

    # 5. Location validation
    valid_location_ids = set(zone_df["LocationID"].unique())
    df = validate_locations(df, valid_location_ids)

    # 6. Distance & speed validation
    df = validate_distance_and_speed(df, MAX_SPEED_MPH)

    # 7. Fare validation
    df = validate_fares(df, FARE_SUM_TOLERANCE)

    # 8. Categorical domain validation
    df = validate_categorical_domains(df, VALID_VENDOR_IDS, VALID_RATECODE_IDS)

    # 9. Composite validity
    df = compute_composite_validity(df)

    # 10. Derive trip metrics
    df = derive_trip_metrics(df)

    # Build audit dict
    flag_cols = [c for c in df.columns if c.startswith("_flag_")]
    audit = {
        "total_rows": len(df),
        "valid_rows": int(df["is_valid"].sum()),
        "invalid_rows": int((~df["is_valid"]).sum()),
        "flag_counts": {col: int(df[col].sum()) for col in flag_cols},
        "null_profile": null_profile.to_dict(orient="records"),
    }

    logger.info(
        f"Clean pipeline complete: {audit['valid_rows']:,} valid / "
        f"{audit['invalid_rows']:,} invalid out of {audit['total_rows']:,}"
    )
    return df, audit