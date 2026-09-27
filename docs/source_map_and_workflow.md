# NYC TLC Pipeline: Source Map & Workflow Data Model Diagram

This document contains the end-to-end **Source Map**, **Workflow Data Model**, and **Pipeline Architecture Diagram** for the NYC TLC Yellow Taxi data processing pipeline, as required by the FDE Data Foundations Assignment specifications.

---

## 📐 End-to-End Pipeline & Source Map Diagram

```mermaid
flowchart TD
    %% Source Systems & Ingestion Mode
    subgraph SOURCEMAP["Source Map: Systems & Data Sources"]
        S1["TPEP Vehicle Taximeter & GPS<br/>(VeriFone / CMT / TPEP)"] -->|Transactional Trip Logs| RAW_TRIP["data/raw/yellow_tripdata_2026-07.parquet<br/>(3.53M Rows x 21 Columns)"]
        S2["NYC TLC GIS Reference"] -->|Spatial Location Lookup| RAW_ZONE["data/raw/taxi_zone_lookup.csv<br/>(265 Location IDs x 4 Columns)"]
    end

    subgraph INGESTION["Stage 1: Data Ingestion (src/ingest.py)"]
        RAW_TRIP -->|Retrieval Mode 1: File Ingest| LOAD_TRIP["load_trip_data()<br/>(pandas.read_parquet)"]
        RAW_ZONE -->|Retrieval Mode 1: File Ingest| LOAD_ZONE["load_zone_lookup()<br/>(pandas.read_csv)"]
        LOAD_TRIP --> DUCK["query_with_duckdb()<br/>(Retrieval Mode 2: In-Memory SQL)"]
        LOAD_TRIP & LOAD_ZONE --> COMP_CHECK["validate_ingestion_completeness()<br/>(Schema & Completeness Verification)"]
    end

    subgraph CLEAN_VAL["Stage 2: Validation & Cleaning (src/validate.py & src/clean.py)"]
        COMP_CHECK --> STD_SCHEMA["standardize_schema()<br/>(Cast Timestamps, IDs, Float Monetanies)"]
        STD_SCHEMA --> IMPUTE["handle_missing_values()<br/>(Impute Passenger Count, Ratecode, Surcharges)"]
        
        IMPUTE --> VAL_TIME["validate_timestamps()<br/>(VR-001 to VR-004: Dates, Negative/Short/Long Duration)"]
        IMPUTE --> VAL_LOC["validate_locations()<br/>(VR-005 & VR-006: PULocation & DOLocation 1-265)"]
        IMPUTE --> VAL_DIST["validate_distance_and_speed()<br/>(VR-007 & VR-008: Zero Distance, Speed > 100 mph)"]
        IMPUTE --> VAL_FARE["validate_fares()<br/>(VR-009 to VR-011: Negative Fare/Total, Sum Mismatch)"]
        IMPUTE --> VAL_CAT["validate_categorical_domains()<br/>(VR-012 & VR-013: Vendor & Ratecode Domains)"]

        VAL_TIME & VAL_LOC & VAL_DIST & VAL_FARE & VAL_CAT --> COMP_VALID["compute_composite_validity()<br/>(Zero Silent Fixes: Add _flag_* & is_valid)"]
        COMP_VALID --> DERIVE["derive_trip_metrics()<br/>(trip_duration_mins, fare_per_mile)"]
    end

    subgraph TRANSFORM["Stage 3: Workflow Modeling & Transformation (src/transform.py)"]
        DERIVE --> ENRICH["enrich_with_zones()<br/>(Dual Left Join: pu_borough/zone, do_borough/zone)"]
        ENRICH --> CLASSIFY["classify_trip_type()<br/>(is_airport_trip, is_cross_borough, is_within_zone)"]
        CLASSIFY --> BUCKET["bucket_time_of_day()<br/>(early_morning, morning_rush, midday, evening_rush, night)"]
        BUCKET --> DAY_WEEK["add_day_of_week()<br/>(day_of_week, is_weekend)"]
    end

    subgraph METRICS["Stage 4: Operational Metrics Engine (src/metrics.py)"]
        DAY_WEEK -->|Filter: is_valid == True| FILTER_VALID["Valid Trip Lineage<br/>(3,279,747 Records / 92.9% Yield)"]
        
        FILTER_VALID --> KPI1["compute_revenue_per_mile()<br/>(Primary KPI: total_amount / trip_distance)"]
        FILTER_VALID --> KPI2["compute_avg_trip_speed()<br/>(Borough Speed by Time Bucket)"]
        FILTER_VALID --> KPI3["compute_tip_percentage()<br/>(Credit Card Tip % by Borough)"]
        FILTER_VALID --> KPI4["compute_congestion_burden()<br/>(Congestion Fee % of Total Fare)"]
        
        DAY_WEEK -->|Full Dataset Audit| KPI5["compute_data_quality_yield()<br/>(Audit Report & Rule Flag Counts)"]

        KPI1 & KPI2 & KPI3 & KPI4 --> GEN_SUMMARY["generate_metrics_summary()<br/>(Unified Operational KPI Dashboard)"]
    end

    subgraph EXPORT["Stage 5: Output Generation & Export (src/export.py)"]
        DERIVE -->|Export Clean Parquet| EXP_CLEAN["data/processed/yellow_trips_clean.parquet"]
        DAY_WEEK -->|Export Enriched Parquet| EXP_ENRICH["data/processed/trips_enriched.parquet"]
        GEN_SUMMARY -->|Export Metrics CSV| EXP_CSV["outputs/reports/metrics_summary.csv"]
        KPI5 -->|Export Quality Audit JSON| EXP_JSON["outputs/reports/audit_log.json"]
        GEN_SUMMARY & KPI5 -->|Generate Figures| EXP_FIGS["outputs/figures/*.png<br/>(Revenue, Speed, Yield & Tip Charts)"]
    end
```

---

## 🗺️ Source Map Summary

| Source System | Data Source File | Storage Format | Grain | Ingestion Mode | Ownership & Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TPEP Vehicle Meters** | `data/raw/yellow_tripdata_2026-07.parquet` | Apache Parquet | 1 row per logged taxi hail | Mode 1: File (`read_parquet`)<br/>Mode 2: SQL (`DuckDB`) | NYC TLC / Authorized Vendors (CMT, VeriFone). Transactional trip data (~3.53M rows). |
| **NYC TLC GIS System** | `data/raw/taxi_zone_lookup.csv` | CSV | 1 row per TLC Taxi Zone | Mode 1: File (`read_csv`) | NYC TLC. Master spatial dimension mapping 265 Location IDs to NYC Boroughs & Zones. |

---

## 🔄 Trip Entity State Lifecycle Model

```mermaid
stateDiagram-v2
    [*] --> Requested : Passenger hails / app request
    Requested --> Dispatched : Driver engages meter (pickup_datetime)
    Dispatched --> InProgress : Taxi in transit (distance & fare accruing)
    InProgress --> Completed : Meter disengaged (dropoff_datetime & surcharges locked)
    Completed --> Settled : Payment processed (payment_type, tip_amount, total_amount)
    Settled --> [*]
```
