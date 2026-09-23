from pathlib import Path

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
LOGS_DIR = BASE_DIR / "logs"

# --- Input Files ---
TRIP_FILE = RAW_DIR / "yellow_tripdata_2026-07.parquet"
ZONE_FILE = RAW_DIR / "taxi_zone_lookup.csv"

# --- Output Files ---
CLEAN_TRIP_FILE = PROCESSED_DIR / "yellow_trips_clean.parquet"
ENRICHED_TRIP_FILE = PROCESSED_DIR / "trips_enriched.parquet"
METRICS_FILE = REPORTS_DIR / "metrics_summary.csv"
AUDIT_FILE = REPORTS_DIR / "audit_log.json"

# --- Column Definitions ---
TIMESTAMP_COLS = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
MONETARY_COLS = ["fare_amount", "extra", "mta_tax", "tip_amount",
                 "tolls_amount", "improvement_surcharge", "total_amount",
                 "congestion_surcharge", "Airport_fee", "cbd_congestion_fee"]
LOCATION_COLS = ["PULocationID", "DOLocationID"]

# --- Validation Thresholds (Business Rules) ---
EXPECTED_DATE_MIN = "2026-07-01"
EXPECTED_DATE_MAX = "2026-08-01"
MIN_TRIP_DURATION_SECS = 30
MAX_TRIP_DURATION_SECS = 86400  # 24 hours
MAX_SPEED_MPH = 100.0
VALID_VENDOR_IDS = {1, 2}
VALID_RATECODE_IDS = {1, 2, 3, 4, 5, 6}
VALID_PAYMENT_TYPES = {0, 1, 2, 3, 4}
FARE_SUM_TOLERANCE = 0.05  # $0.05