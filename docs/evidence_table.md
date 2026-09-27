# NYC TLC Taxi Pipeline: Evidence Table & KUAL Framework

This document represents the **Final Evidence Table / Operational Dashboard** and the **Known / Unknown / Assumption / Limitation (KUAL) Section** for the NYC TLC Yellow Taxi Data Pipeline (July 2026 Batch, 3,530,109 Total Ingested Records).

---

## 📊 Section 1: Final Operational Evidence Table (KPI Dashboard)

### Table 1: Primary KPI — Revenue Per Trip Mile & Trip Volume by Pickup Borough
> **Primary KPI Formula:** $\text{Revenue Per Mile} = \frac{\sum \text{total\_amount}}{\sum \text{trip\_distance}}$ (Computed on valid records with $\text{trip\_distance} > 0$)

| Pickup Borough | Mean Revenue / Mile ($) | Median Revenue / Mile ($) | Total Valid Trips | Primary Operational Takeaway |
| :--- | ---: | ---: | ---: | :--- |
| **Manhattan** | **$30.82** | $12.38 | 2,882,193 | Core operational volume driver (87.9% of valid trips); high density & slow traffic yield high time-metered revenues per mile. |
| **Brooklyn** | **$44.70** | $7.44 | 88,863 | High revenue per mile driven by cross-borough bottleneck trips and high initial meter flags. |
| **Queens** | **$13.40** | $5.93 | 291,320 | Second largest volume driver (8.9% of trips); longer airport highway miles (JFK/LGA) reduce revenue per mile relative to distance. |
| **Bronx** | **$33.66** | $6.07 | 13,209 | Moderate volume with steady revenue yield per mile across outer borough routes. |
| **Staten Island** | **$76.20** | $4.94 | 282 | Low trip volume; high mean metric driven by Verrazzano bridge tolls and initial rate surcharges. |
| **EWR (Airport)** | **$732.11** | $22.31 | 28 | Rare out-of-state airport hails; high mean skewed by out-of-state flat rate surcharges. |
| **Unknown** | **$53.71** | $10.26 | 3,852 | Unmapped spatial location IDs mapped cleanly to Unknown borough category. |

---

### Table 2: Borough Speed Matrix by Operational Time-of-Day Bucket (mph)
> **Formula:** $\text{Implied Speed} = \frac{\text{trip\_distance}}{\text{duration\_hours}}$

| Pickup Borough | Early Morning (05-08) | Morning Rush (08-11) | Midday (11-16) | Evening Rush (16-20) | Night (20-05) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Manhattan** | 14.54 mph | 9.81 mph | 8.66 mph | **8.61 mph** | 11.59 mph |
| **Brooklyn** | 16.42 mph | 12.40 mph | 11.42 mph | **10.67 mph** | 15.11 mph |
| **Queens** | 23.98 mph | 19.46 mph | 18.15 mph | 20.43 mph | 26.22 mph |
| **Bronx** | 19.50 mph | 15.53 mph | 14.57 mph | 13.97 mph | 18.69 mph |
| **Staten Island** | 23.84 mph | 21.78 mph | 19.39 mph | 23.24 mph | 26.13 mph |
| **EWR (Airport)** | 36.47 mph | 22.09 mph | 19.48 mph | 16.03 mph | 28.47 mph |

---

### Table 3: Customer Tipping Behavior & Regulatory Congestion Fee Burden
> **Credit Card Tip %:** $\frac{\text{tip\_amount}}{\text{fare\_amount}} \times 100$ (Filtered to credit card `payment_type = 1`)  
> **Congestion Burden %:** $\frac{\text{congestion\_surcharge} + \text{cbd\_congestion\_fee}}{\text{total\_amount}} \times 100$

| Pickup Borough | Mean Tip % (Credit Card) | Median Tip % (Credit Card) | Congestion Surcharge Burden (%) | Operational Impact |
| :--- | ---: | ---: | ---: | :--- |
| **Manhattan** | **26.34%** | 27.20% | **11.79%** | Highest tipping willingness; Manhattan trips absorb significant congestion surcharge costs. |
| **Brooklyn** | 23.34% | 23.04% | 1.19% | Strong tipping baseline; minimal congestion fee impact for pickups outside Manhattan. |
| **Queens** | 21.55% | 23.27% | 1.79% | Airport drivers benefit from consistent ~21.5% tipping rates. |
| **Bronx** | 20.60% | 21.01% | 0.43% | Lowest congestion burden; steady 20%+ tipping rate on card payments. |
| **Staten Island** | 32.12% | 23.00% | 0.21% | High card tipping percentage on long inter-borough hires. |

---

### Table 4: Pipeline Data Quality Yield & Verification Summary
> **Quality Yield Formula:** $\text{Yield} = \frac{\text{Valid Records}}{\text{Total Records}} \times 100$

| Metric / Dimension | Metric Value | Percentage / Status | Description |
| :--- | ---: | ---: | :--- |
| **Total Ingested Records** | **3,530,109** | 100.00% | July 2026 raw Yellow Taxi transactional dataset. |
| **Valid Record Yield (`is_valid == True`)** | **3,279,747** | **92.91%** | **Trustworthy records clean of critical anomalies.** |
| **Flagged Invalid Records (`is_valid == False`)** | **250,362** | 7.09% | Preserved explicitly in data lineage (Zero Silent Fixes). |
| *Rule VR-007: Zero Trip Distance* | 128,322 | 3.64% | Cancelled hails or stationary meter runs. |
| *Rule VR-002: Dropoff <= Pickup* | 42,316 | 1.20% | Non-positive trip duration (42,315 zero, 1 negative). |
| *Rule VR-012: Invalid RatecodeID* | 53,756 | 1.52% | Undocumented rate code `99.0`. |
| *Rule VR-013: Invalid VendorID* | 49,526 | 1.40% | Undocumented vendors `6` and `7`. |
| *Rule VR-003: Duration < 30s* | 33,038 | 0.94% | Ultra-short phantom trips. |
| *Rule VR-009 / VR-010: Negative Fares/Totals* | 14,200 / 14,699 | 0.40% | Refunds, voids, or payment disputes. |
| *Rule VR-008: Speed > 100 mph* | 909 | 0.03% | Impossible implied speed anomalies. |
| *Rule VR-001: Dates outside July 2026* | 46 | 0.001% | Meter clock drift (oldest pickup: 2008-12-30). |

---

## 📌 Section 2: Known / Unknown / Assumption / Limitation (KUAL) Framework

| Category | Item 1 | Item 2 | Item 3 | Item 4 | Item 5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Knowns** | **Total Ingestion Volume:** Exactly 3,530,109 trip records ingested for July 2026. | **Null Correlation:** 27.5% missingness in passenger counts & surcharges correlates 100% with `payment_type = 0`. | **Spatial Coverage:** 265 valid TLC taxi zones across 5 NYC boroughs + EWR. | **Negative Fare Volume:** Exactly 14,200 negative fare records exist in raw inputs. | **Data Quality Yield:** Exactly 92.91% (3,279,747 rows) pass all critical validation rules. |
| **Unknowns** | **Undocumented Vendor IDs:** Operational identity of Vendor IDs `6` and `7` (49,526 rows). | **Undocumented Ratecode 99:** Business meaning of `RatecodeID = 99.0` (53,756 rows). | **Cash Tip Amounts:** Cash tip amounts are unrecorded by meters ($0.00$ in data). | **Request Source Sparsity:** Operational cause of 72.5% nulls in `request_source`. | **Exact Micro-Routes:** GPS spatial resolution is limited to zone boundaries, not street geometry. |
| **Assumptions** | **Imputation Safety:** Missing passenger counts can be imputed safely with median ($1.0$). | **TLC Total Amount Quirk:** Component sum discrepancies (> $0.05$) reflect late-added surcharges, not invalid trips. | **Minimum Trip Threshold:** Trips under 30 seconds represent non-passenger meter tests or instant cancels. | **July Date Boundaries:** 46 out-of-range rows (e.g. 2008 dates) represent uncalibrated meter hardware logs. | **Odometer Accuracy:** `trip_distance` represents physical taximeter odometer distance. |
| **Limitations** | **No Driver/Medallion IDs:** Lack of driver keys prevents individual shift performance analysis. | **Batch Ingestion:** Monthly Parquet batch format limits real-time dispatch capabilities. | **Zone Spatial Granularity:** Unable to evaluate street-level traffic signal delays. | **Payment Type Sparsity:** 27.47% `payment_type = 0` restricts credit card tipping analytics on those rows. | **No Passenger Feedback:** No direct customer satisfaction or rating data available. |
