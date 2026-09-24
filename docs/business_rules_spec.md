# NYC TLC Yellow Taxi Pipeline: Business Rules & Context Specification

## 1. Business Context & Source Reasoning

### Operational Business Questions & Field Mapping
This data pipeline answers critical questions for taxi fleet management and regulatory analysis:
1. **Fleet Utilization & Demand Modeling:** Where and when do passengers need taxis? 
   * *Mapped Fields:* `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `PULocationID`, `DOLocationID`.
2. **Revenue & Yield Analysis:** What are the most profitable routes, and how do tips correlate with trip characteristics? 
   * *Mapped Fields:* `fare_amount`, `tip_amount`, `total_amount`, `payment_type`.
3. **Operational Anomalies & Fraud Detection:** Are drivers experiencing meter errors, cancelled trips, or charging impossible rates? 
   * *Mapped Fields:* `trip_distance`, time duration derived from timestamps, `RatecodeID`.
4. **Toll & Congestion Surcharge Impact:** How do regulatory fees impact total passenger costs? 
   * *Mapped Fields:* `tolls_amount`, `congestion_surcharge`, `cbd_congestion_fee`.

### Source Systems
* **TPEP Vendor Systems:** Taxicab Passenger Enhancement Program (TPEP) authorized vendors (historically VeriFone and Creative Mobile Technologies - IDs 1 and 2) collect data directly from the vehicle's meter and credit card reader. Note: We are seeing undocumented vendors 6 and 7 in this dataset.
* **TLC Data Warehouse:** Vendor data is transmitted to the NYC Taxi & Limousine Commission, where it is aggregated.
* **Public Parquet Files:** The data is finally published for public consumption in monthly Apache Parquet batches.

### Data Attributes
* **Data Grain:** 1 row = 1 completed (or logged) taxicab trip.
* **Ownership:** NYC Taxi & Limousine Commission (TLC).
* **Freshness:** Monthly batch ingestion (Current batch: July 2026, ~3.53M records).

---

## 2. Formal Validation Rules

The profiling of the July 2026 dataset (3,530,109 total records) revealed numerous anomalies requiring strict validation rules.

| Rule ID | Rule Name | Column(s) Affected | Invalid Condition | Business Justification | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VR-001** | Date out of range | `tpep_pickup_datetime` | Pickup not in July 2026 | Downstream aggregations for July 2026 reporting will be skewed by out-of-range data. (Data shows 46 rows outside July 2026). | CRITICAL |
| **VR-002** | Negative or zero duration | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | dropoff_datetime <= pickup_datetime | A trip cannot end before or exactly when it begins. (Data shows 1 negative, 42,315 zero durations). | CRITICAL |
| **VR-003** | Duration too short | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | Duration < 30 seconds | Trips under 30 seconds are typically meter errors, immediate cancellations, or system testing. (Data shows 75,354 occurrences). | WARNING |
| **VR-004** | Duration too long | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | Duration > 24 hours | A single continuous taxi trip over 24 hours is highly improbable and likely represents a stuck meter. (Data shows 37 occurrences). | CRITICAL |
| **VR-005** | Invalid pickup location | `PULocationID` | PULocationID not in 1-265 | We only have definitions for 265 TLC Taxi Zones. Unmapped zones break spatial joins. | CRITICAL |
| **VR-006** | Invalid dropoff location | `DOLocationID` | DOLocationID not in 1-265 | Unmapped dropoff zones break routing analytics and spatial joins. | CRITICAL |
| **VR-007** | Zero trip distance | `trip_distance` | trip_distance = 0 | A trip must cover physical distance. 0 distance indicates a stationary meter run or hardware failure. (Data shows 128,322 occurrences). | WARNING |
| **VR-008** | Impossible speed | `trip_distance`, `tpep_..._datetime` | (trip_distance / duration_hrs) > 100 mph | Taxis cannot physically average >100 mph in NYC traffic. Indicates corrupted distance or time data. | CRITICAL |
| **VR-009** | Negative fare amount | `fare_amount` | fare_amount < 0 | Drivers do not pay passengers. Negative values (14,200 found) may reflect refunds/voids but distort aggregate revenue. | CRITICAL |
| **VR-010** | Negative total amount | `total_amount` | total_amount < 0 | Total collected revenue cannot be negative for the same reasons as VR-009. | CRITICAL |
| **VR-011** | Fare component sum mismatch | `total_amount`, `fare_amount`, `tip_amount`, `tolls_amount`, `mta_tax`, etc. | \|Sum of components - total_amount\| > 0.05 | Ensures financial integrity. A $0.05 tolerance is used to handle floating point/rounding discrepancies. | CRITICAL |
| **VR-012** | Invalid RatecodeID | `RatecodeID` | RatecodeID not in (1, 2, 3, 4, 5, 6) | Values like 99.0 (found in 53,756 rows) are undocumented and prevent accurate fare rate analysis. | WARNING |
| **VR-013** | Invalid VendorID | `VendorID` | VendorID not in (1, 2) | Values 6 and 7 are undocumented TPEP providers. We cannot verify their meter calibration or data formats. | WARNING |
| **VR-014** | Missing mandatory fields | `tpep_pickup_datetime`, `PULocationID` | Fields IS NULL | Missing fundamental timestamps or spatial IDs renders the row entirely useless for analytics. | CRITICAL |

---

## 3. KPI Definitions

These Key Performance Indicators drive fleet operational strategies.

### 1. Revenue Per Trip Mile (Primary)
* **Formula:** `SUM(total_amount) / SUM(trip_distance)`
* **Aggregation Dimensions:** Time-of-day, Day-of-week, Borough.
* **Business Interpretation:** Measures the financial efficiency of a route or time period. High values indicate highly profitable miles (often slow traffic but high time-based meter charges, or high tips). Low values mean drivers are driving empty or taking low-margin long-hauls.
* **Filters:** Valid records only (distance > 0, total_amount > 0).

### 2. Average Trip Speed (mph)
* **Formula:** `SUM(trip_distance) / SUM((dropoff_datetime - pickup_datetime) in hours)`
* **Aggregation Dimensions:** PULocationID, hour of day.
* **Business Interpretation:** Measures traffic fluidity and operational efficiency. Lower speeds generally correlate with higher congestion areas and can negatively impact driver shifts (despite high revenue/mile).
* **Filters:** Valid records only; drop zero distance and zero duration trips.

### 3. Tip Percentage
* **Formula:** `SUM(tip_amount) / SUM(fare_amount) * 100`
* **Aggregation Dimensions:** DOLocationID, VendorID, Time-of-day.
* **Business Interpretation:** Indicates passenger satisfaction and willingness to tip based on destination or time. High percentages attract drivers to specific zones.
* **Filters:** `payment_type = 1` (Credit Card only, as cash tips are typically unrecorded).

### 4. Congestion Surcharge Burden
* **Formula:** `SUM(congestion_surcharge + COALESCE(cbd_congestion_fee, 0)) / SUM(total_amount) * 100`
* **Aggregation Dimensions:** Time-of-day, dropoff borough (Manhattan vs outer boroughs).
* **Business Interpretation:** Represents the percentage of the passenger's total bill that is purely regulatory congestion fees. High burden may deter ridership in those zones.
* **Filters:** Valid records only.

### 5. Data Quality Yield
* **Formula:** `(COUNT(valid_rows) / COUNT(total_rows)) * 100`
* **Aggregation Dimensions:** VendorID, Date.
* **Business Interpretation:** Tracks the health of the TPEP vendor data feeds. A drop in yield means faulty meters, network drops, or software bugs from the vendors (such as the 27.5% nulls observed for payment_type=0).
* **Filters:** None (applies to the entire batch).

---

## 4. KUAL Table (Knowns, Unknowns, Assumptions, Limitations)

| Category | Item 1 | Item 2 | Item 3 | Item 4 | Item 5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Knowns** | Total trip volume is ~3.53M records for July 2026. | 27.5% of rows have nulls across key fields correlated strictly with `payment_type=0`. | There are 265 valid TLC zones (plus EWR and Unknown). | 14,200 trips resulted in negative fares. | Vendor IDs 1 and 2 are the standard TPEP providers. |
| **Unknowns** | The operational meaning of `RatecodeID = 99.0` (53,756 instances). | The true identity of undocumented `VendorID`s 6 and 7. | The exact routes or streets taken between PU and DO zones. | The meaning of `request_source`, which is 72.5% null. | Whether negative fares represent cancelled trips, refunds, or system tests. |
| **Assumptions** | Missing data with `payment_type=0` represents voided, aborted, or cash-disputed trips. | A $0.05 tolerance safely accounts for floating point anomalies in fare sums. | Trips under 30s are not meaningful passenger journeys and can be treated as anomalies. | `trip_distance` is measured via the taxi meter's odometer, not straight-line distance. | Only July 2026 data is relevant; the 46 out-of-range rows are logging artifacts. |
| **Limitations** | 27.5% missing data limits comprehensive revenue/demand analysis. | Zone-level spatial granularity limits micro-routing (street-by-street) optimization. | Monthly batch processing prevents real-time fleet dispatching use cases. | Lack of Driver/Medallion IDs prevents shift-level or driver-specific performance analysis. | High sparsity in `request_source` limits analysis on digital vs street hails. |

---

## 5. Workflow Model Description

The data represents the lifecycle of a taxi trip, which can be modeled as the following entity-state transitions.

* **Entity:** Taxi Trip

### States & Transitions
1. **Requested (Null state in this data / Implicit)**
   * *Trigger:* Passenger flags down a cab or requests via an app (`request_source`).
   * *Data Mapping:* Not fully captured until the meter is engaged.
2. **Dispatched / Engaged**
   * *Trigger:* Driver accepts the fare and turns on the meter.
   * *Data Mapping:* `tpep_pickup_datetime` is logged; GPS logs `PULocationID`.
3. **In-Progress**
   * *Trigger:* The taxi physically moves toward the destination.
   * *Data Mapping:* Meter calculates `trip_distance` and time elapsed, continually updating the base `fare_amount` based on the `RatecodeID`.
4. **Completed**
   * *Trigger:* Driver stops the meter upon reaching the destination.
   * *Data Mapping:* `tpep_dropoff_datetime` is logged; GPS logs `DOLocationID`. Surcharges (`congestion_surcharge`, `mta_tax`) are locked in.
5. **Settled**
   * *Trigger:* Passenger pays for the trip.
   * *Data Mapping:* `payment_type` is recorded. `tip_amount` is added (if credit card), and `total_amount` is finalized and transmitted by the `VendorID`.
