import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_trip_df():
    data = [
        # Normal
        (1, "2026-07-01 10:00:00", "2026-07-01 10:15:00", 1, 3.0, 1.0, "N", 1, 2, 1,
         10.0, 0.5, 0.5, 2.0, 0.0, 0.3, 13.3, 0.0, 0.0, 0.0),
        # Negative fare
        (1, "2026-07-01 11:00:00", "2026-07-01 11:15:00", 1, 3.0, 1.0, "N", 1, 2, 1,
         -10.0, 0.0, 0.0, 0.0, 0.0, 0.0, -10.0, 0.0, 0.0, 0.0),
        # Zero distance
        (1, "2026-07-01 12:00:00", "2026-07-01 12:15:00", 1, 0.0, 1.0, "N", 1, 1, 1,
         5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.0),
        # Pickup outside date (2008)
        (1, "2008-01-01 10:00:00", "2008-01-01 10:15:00", 1, 3.0, 1.0, "N", 1, 2, 1,
         10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0),
        # Dropoff before pickup
        (1, "2026-07-01 14:15:00", "2026-07-01 14:00:00", 1, 3.0, 1.0, "N", 1, 2, 1,
         10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0),
        # Impossible speed (200 mph)
        (1, "2026-07-01 15:00:00", "2026-07-01 15:15:00", 1, 60.0, 1.0, "N", 1, 2, 1,
         100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0),
        # Invalid VendorID (7)
        (7, "2026-07-01 16:00:00", "2026-07-01 16:15:00", 1, 3.0, 1.0, "N", 1, 2, 1,
         10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0),
        # Invalid RatecodeID (99.0)
        (1, "2026-07-01 17:00:00", "2026-07-01 17:15:00", 1, 3.0, 99.0, "N", 1, 2, 1,
         10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0),
        # Duration too short (10s)
        (1, "2026-07-01 18:00:00", "2026-07-01 18:00:10", 1, 0.1, 1.0, "N", 1, 2, 1,
         2.5, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5, 0.0, 0.0, 0.0),
        # Duration too long (25h)
        (1, "2026-07-01 19:00:00", "2026-07-02 20:00:00", 1, 10.0, 1.0, "N", 1, 2, 1,
         50.0, 0.0, 0.0, 0.0, 0.0, 0.0, 50.0, 0.0, 0.0, 0.0),
        # Invalid Location ID (999)
        (1, "2026-07-01 20:00:00", "2026-07-01 20:15:00", 1, 3.0, 1.0, "N", 999, 2, 1,
         10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0),
    ]
    
    cols = [
        "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", 
        "trip_distance", "RatecodeID", "store_and_fwd_flag", "PULocationID", "DOLocationID", 
        "payment_type", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", 
        "improvement_surcharge", "total_amount", "congestion_surcharge", "Airport_fee", 
        "cbd_congestion_fee"
    ]
    
    df = pd.DataFrame(data, columns=cols)
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    return df

@pytest.fixture
def sample_zone_df():
    data = [
        (1, "Manhattan", "Zone A", "Yellow Zone"),
        (2, "Manhattan", "Zone B", "Yellow Zone"),
        (3, "Queens", "JFK Airport", "Airports"),
        (4, "Brooklyn", "Zone D", "Boro Zone"),
        (5, "Bronx", "Zone E", "Boro Zone"),
    ]
    return pd.DataFrame(data, columns=["LocationID", "Borough", "Zone", "service_zone"])

@pytest.fixture
def tmp_output_dir(tmp_path):
    return tmp_path
