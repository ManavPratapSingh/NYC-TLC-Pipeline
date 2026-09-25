"""Transformation module — zone enrichment, trip classification, and time bucketing."""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def enrich_with_zones(df: pd.DataFrame, zone_df: pd.DataFrame) -> pd.DataFrame:
    """Left-join trips with zone lookup for pickup and dropoff boroughs/zones.

    Joins:
        - PULocationID → pu_borough, pu_zone, pu_service_zone
        - DOLocationID → do_borough, do_zone, do_service_zone

    Unmatched boroughs are filled with 'Unknown'.

    Args:
        df: Trip DataFrame with PULocationID and DOLocationID.
        zone_df: Zone lookup DataFrame with LocationID, Borough, Zone, service_zone.

    Returns:
        Enriched DataFrame with 6 new zone columns.
    """
    df = df.copy()

    # Prepare zone lookup with renamed columns for PU join
    pu_zones = zone_df.rename(columns={
        "Borough": "pu_borough",
        "Zone": "pu_zone",
        "service_zone": "pu_service_zone",
    })[["LocationID", "pu_borough", "pu_zone", "pu_service_zone"]]

    # Prepare zone lookup with renamed columns for DO join
    do_zones = zone_df.rename(columns={
        "Borough": "do_borough",
        "Zone": "do_zone",
        "service_zone": "do_service_zone",
    })[["LocationID", "do_borough", "do_zone", "do_service_zone"]]

    # Join pickup
    df = df.merge(pu_zones, left_on="PULocationID", right_on="LocationID", how="left")
    df.drop(columns=["LocationID"], inplace=True)

    # Join dropoff
    df = df.merge(do_zones, left_on="DOLocationID", right_on="LocationID", how="left")
    df.drop(columns=["LocationID"], inplace=True)

    # Fill unmatched
    for col in ["pu_borough", "pu_zone", "pu_service_zone",
                 "do_borough", "do_zone", "do_service_zone"]:
        df[col] = df[col].fillna("Unknown")

    logger.info(f"Zone enrichment complete: {df['pu_borough'].nunique()} PU boroughs, "
                f"{df['do_borough'].nunique()} DO boroughs")
    return df


def classify_trip_type(df: pd.DataFrame) -> pd.DataFrame:
    """Classify trips into operational categories.

    Adds columns:
        - is_airport_trip (bool): PU or DO service zone is 'Airports'
        - is_cross_borough (bool): PU borough differs from DO borough
        - is_within_zone (bool): PULocationID equals DOLocationID

    Args:
        df: Enriched DataFrame with pu_service_zone, do_service_zone, pu_borough, do_borough.

    Returns:
        DataFrame with classification columns.
    """
    df = df.copy()

    df["is_airport_trip"] = (
        (df["pu_service_zone"] == "Airports") | (df["do_service_zone"] == "Airports")
    )
    df["is_cross_borough"] = df["pu_borough"] != df["do_borough"]
    df["is_within_zone"] = df["PULocationID"] == df["DOLocationID"]

    airport = df["is_airport_trip"].sum()
    cross = df["is_cross_borough"].sum()
    within = df["is_within_zone"].sum()
    logger.info(f"Trip classification: {airport:,} airport, {cross:,} cross-borough, "
                f"{within:,} within-zone")
    return df


def bucket_time_of_day(df: pd.DataFrame) -> pd.DataFrame:
    """Bucket pickup time into operational time-of-day categories.

    Adds column 'time_bucket':
        - 'early_morning': hours 5–7
        - 'morning_rush': hours 8–10
        - 'midday': hours 11–15
        - 'evening_rush': hours 16–19
        - 'night': hours 20–23 and 0–4

    Args:
        df: DataFrame with tpep_pickup_datetime.

    Returns:
        DataFrame with time_bucket column.
    """
    df = df.copy()

    hour = df["tpep_pickup_datetime"].dt.hour
    conditions = [
        (hour >= 5) & (hour < 8),
        (hour >= 8) & (hour < 11),
        (hour >= 11) & (hour < 16),
        (hour >= 16) & (hour < 20),
    ]
    choices = ["early_morning", "morning_rush", "midday", "evening_rush"]

    import numpy as np
    df["time_bucket"] = np.select(conditions, choices, default="night")

    logger.info(f"Time bucketing complete: {df['time_bucket'].value_counts().to_dict()}")
    return df


def add_day_of_week(df: pd.DataFrame) -> pd.DataFrame:
    """Add day-of-week and weekend indicator.

    Adds columns:
        - day_of_week (str): Monday, Tuesday, ..., Sunday
        - is_weekend (bool): True for Saturday and Sunday

    Args:
        df: DataFrame with tpep_pickup_datetime.

    Returns:
        DataFrame with day_of_week and is_weekend columns.
    """
    df = df.copy()

    df["day_of_week"] = df["tpep_pickup_datetime"].dt.day_name()
    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"])

    weekend_pct = df["is_weekend"].mean() * 100
    logger.info(f"Day-of-week added: {weekend_pct:.1f}% weekend trips")
    return df
