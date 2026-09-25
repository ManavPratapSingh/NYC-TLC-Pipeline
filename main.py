import sys
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import *
from src.ingest import load_trip_data, load_zone_lookup
from src.clean import clean_pipeline
from src.transform import enrich_with_zones, classify_trip_type, bucket_time_of_day, add_day_of_week
from src.metrics import generate_metrics_summary, compute_data_quality_yield
from src.export import export_clean_data, export_metrics_csv, export_audit_log, generate_figures

def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def check_idempotency(force: bool):
    if ENRICHED_TRIP_FILE.exists() and not force:
        return True
    return False

def run_pipeline(force: bool = False):
    logger = setup_logging()
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if check_idempotency(force):
        logger.info("Pipeline already run. Use --force to rerun.")
        return
        
    start_time = time.time()
    logger.info("Starting NYC TLC Pipeline")
    
    try:
        logger.info("Stage: Ingestion")
        df_trips = load_trip_data(TRIP_FILE)
        df_zones = load_zone_lookup(ZONE_FILE)
        
        logger.info("Stage: Cleaning & Validation")
        df_clean, audit_dict = clean_pipeline(df_trips, df_zones)
        export_clean_data(df_clean, CLEAN_TRIP_FILE)
        
        logger.info("Stage: Transformation")
        df_enriched = enrich_with_zones(df_clean, df_zones)
        df_enriched = classify_trip_type(df_enriched)
        df_enriched = bucket_time_of_day(df_enriched)
        df_enriched = add_day_of_week(df_enriched)
        export_clean_data(df_enriched, ENRICHED_TRIP_FILE)
        
        logger.info("Stage: Metrics")
        valid_enriched = df_enriched[df_enriched["is_valid"] == True]
        summary_df = generate_metrics_summary(valid_enriched)
        dq_yield = compute_data_quality_yield(df_enriched)
        audit_dict.update(dq_yield)
        
        logger.info("Stage: Export")
        export_metrics_csv(summary_df, METRICS_FILE)
        export_audit_log(audit_dict, AUDIT_FILE)
        generate_figures(valid_enriched, dq_yield, FIGURES_DIR)
        
        elapsed = time.time() - start_time
        logger.info(f"Pipeline completed successfully in {elapsed:.2f} seconds.")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run NYC TLC Pipeline")
    parser.add_argument("--force", action="store_true", help="Force rerun even if outputs exist")
    args = parser.parse_args()
    run_pipeline(args.force)
