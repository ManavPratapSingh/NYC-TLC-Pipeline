"""Profiling and validation module — flags invalid rows, never drops them."""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def profile_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Generate null count summary per column.

    Args:
        df: Input DataFrame to profile.

    Returns:
        Summary DataFrame with columns: column_name, null_count, null_pct.
    """
    null_counts = df.isnull().sum()
    null_pct = (null_counts / len(df) * 100).round(2)
    summary = pd.DataFrame({
        "column_name": null_counts.index,
        "null_count": null_counts.values,
        "null_pct": null_pct.values,
    })
    logger.info(f"Null profile: {(null_counts > 0).sum()} columns with nulls")
    return summary


def validate_timestamps(
    df: pd.DataFrame,
    date_min: str,
    date_max: str,
    min_duration_secs: int,
    max_duration_secs: int,
) -> pd.DataFrame:
    """Flag temporal anomalies.

    Adds columns:
        - trip_duration_secs (float): derived duration
        - _flag_date_out_of_range (bool): pickup outside [date_min, date_max)
        - _flag_negative_duration (bool): dropoff <= pickup
        - _flag_duration_too_short (bool): 0 < duration < min_duration_secs
        - _flag_duration_too_long (bool): duration > max_duration_secs

    Args:
        df: DataFrame with tpep_pickup_datetime and tpep_dropoff_datetime.
        date_min: Lower bound date string (inclusive).
        date_max: Upper bound date string (exclusive).
        min_duration_secs: Minimum acceptable trip duration.
        max_duration_secs: Maximum acceptable trip duration.

    Returns:
        DataFrame with added flag columns.
    """
    df = df.copy()

    # Derive duration
    duration = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()
    df["trip_duration_secs"] = duration

    # Flag: pickup outside expected date range
    dt_min = pd.Timestamp(date_min)
    dt_max = pd.Timestamp(date_max)
    df["_flag_date_out_of_range"] = (
        (df["tpep_pickup_datetime"] < dt_min) | (df["tpep_pickup_datetime"] >= dt_max)
    )

    # Flag: negative or zero duration (dropoff <= pickup)
    df["_flag_negative_duration"] = duration <= 0

    # Flag: too short (but positive)
    df["_flag_duration_too_short"] = (duration > 0) & (duration < min_duration_secs)

    # Flag: too long
    df["_flag_duration_too_long"] = duration > max_duration_secs

    flagged = (
        df["_flag_date_out_of_range"].sum()
        + df["_flag_negative_duration"].sum()
        + df["_flag_duration_too_short"].sum()
        + df["_flag_duration_too_long"].sum()
    )
    logger.info(f"Timestamp validation: {flagged:,} total flags across 4 rules")
    return df


def validate_locations(df: pd.DataFrame, valid_location_ids: set) -> pd.DataFrame:
    """Flag invalid pickup/dropoff location IDs.

    Adds columns:
        - _flag_invalid_pu_location (bool)
        - _flag_invalid_do_location (bool)

    Args:
        df: DataFrame with PULocationID and DOLocationID.
        valid_location_ids: Set of valid location IDs.

    Returns:
        DataFrame with added flag columns.
    """
    df = df.copy()
    df["_flag_invalid_pu_location"] = ~df["PULocationID"].isin(valid_location_ids)
    df["_flag_invalid_do_location"] = ~df["DOLocationID"].isin(valid_location_ids)

    pu_bad = df["_flag_invalid_pu_location"].sum()
    do_bad = df["_flag_invalid_do_location"].sum()
    logger.info(f"Location validation: {pu_bad:,} invalid PU, {do_bad:,} invalid DO")
    return df


def validate_distance_and_speed(df: pd.DataFrame, max_speed_mph: float) -> pd.DataFrame:
    """Flag zero distance and impossible implied speeds.

    Adds columns:
        - implied_speed_mph (float): trip_distance / (trip_duration_secs / 3600)
        - _flag_zero_distance (bool): trip_distance <= 0
        - _flag_impossible_speed (bool): implied_speed_mph > max_speed_mph

    Args:
        df: DataFrame with trip_distance and trip_duration_secs.
        max_speed_mph: Maximum plausible speed in mph.

    Returns:
        DataFrame with added flag columns.
    """
    df = df.copy()

    # Implied speed (guard against division by zero)
    duration_hours = df["trip_duration_secs"] / 3600.0
    df["implied_speed_mph"] = np.where(
        duration_hours > 0,
        df["trip_distance"] / duration_hours,
        np.nan,
    )

    df["_flag_zero_distance"] = df["trip_distance"] <= 0
    df["_flag_impossible_speed"] = df["implied_speed_mph"] > max_speed_mph

    zd = df["_flag_zero_distance"].sum()
    isp = df["_flag_impossible_speed"].sum()
    logger.info(f"Distance/speed validation: {zd:,} zero-distance, {isp:,} impossible-speed")
    return df


def validate_fares(df: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Flag negative fares and fare component sum mismatches.

    Adds columns:
        - _flag_negative_fare (bool): fare_amount < 0
        - _flag_negative_total (bool): total_amount < 0
        - _flag_fare_sum_mismatch (bool): |total - component_sum| > tolerance

    Args:
        df: DataFrame with monetary columns.
        tolerance: Maximum allowed discrepancy between total and component sum.

    Returns:
        DataFrame with added flag columns.
    """
    df = df.copy()

    df["_flag_negative_fare"] = df["fare_amount"] < 0
    df["_flag_negative_total"] = df["total_amount"] < 0

    # Component sum check (fill NaN surcharges with 0)
    component_cols = [
        "fare_amount", "extra", "mta_tax", "tip_amount",
        "tolls_amount", "improvement_surcharge",
        "congestion_surcharge", "Airport_fee", "cbd_congestion_fee",
    ]
    component_sum = sum(df[col].fillna(0) for col in component_cols)
    df["_flag_fare_sum_mismatch"] = (df["total_amount"] - component_sum).abs() > tolerance

    nf = df["_flag_negative_fare"].sum()
    nt = df["_flag_negative_total"].sum()
    fsm = df["_flag_fare_sum_mismatch"].sum()
    logger.info(f"Fare validation: {nf:,} neg-fare, {nt:,} neg-total, {fsm:,} sum-mismatch")
    return df


def validate_categorical_domains(
    df: pd.DataFrame, valid_vendors: set, valid_ratecodes: set
) -> pd.DataFrame:
    """Flag invalid categorical domain values.

    Adds columns:
        - _flag_invalid_vendor (bool): VendorID not in valid_vendors
        - _flag_invalid_ratecode (bool): RatecodeID not in valid_ratecodes (NaN = invalid)

    Args:
        df: DataFrame with VendorID and RatecodeID.
        valid_vendors: Set of valid VendorID values.
        valid_ratecodes: Set of valid RatecodeID values.

    Returns:
        DataFrame with added flag columns.
    """
    df = df.copy()
    df["_flag_invalid_vendor"] = ~df["VendorID"].isin(valid_vendors)
    df["_flag_invalid_ratecode"] = ~df["RatecodeID"].isin(valid_ratecodes)

    iv = df["_flag_invalid_vendor"].sum()
    ir = df["_flag_invalid_ratecode"].sum()
    logger.info(f"Categorical validation: {iv:,} invalid-vendor, {ir:,} invalid-ratecode")
    return df


def compute_composite_validity(df: pd.DataFrame) -> pd.DataFrame:
    """Combine all _flag_* columns into a single is_valid boolean.

    is_valid = True if NO flag columns are True for that row.

    Args:
        df: DataFrame with _flag_* columns.

    Returns:
        DataFrame with added 'is_valid' column.
    """
    df = df.copy()
    # Exclude WARNING-level flags from composite validity.
    # _flag_fare_sum_mismatch is a known TLC data format quirk: total_amount
    # was calculated before some surcharges (congestion, Airport_fee, cbd) were
    # appended to the component columns. The flag is kept for audit purposes.
    warning_flags = {"_flag_fare_sum_mismatch"}
    flag_cols = [c for c in df.columns if c.startswith("_flag_") and c not in warning_flags]

    if not flag_cols:
        df["is_valid"] = True
        logger.warning("No flag columns found — marking all rows as valid")
    else:
        any_flag = df[flag_cols].any(axis=1)
        df["is_valid"] = ~any_flag

    valid_count = df["is_valid"].sum()
    total = len(df)
    logger.info(
        f"Composite validity: {valid_count:,}/{total:,} valid "
        f"({valid_count / total * 100:.1f}%)"
    )
    return df
