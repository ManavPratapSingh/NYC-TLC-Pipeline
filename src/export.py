import pandas as pd
import json
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

logger = logging.getLogger(__name__)

def export_clean_data(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info(f"Exported {len(df)} rows to {path}")

def export_metrics_csv(metrics_df: pd.DataFrame, path: Path) -> None:
    """Write metrics summary to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(path, index=False)
    logger.info(f"Exported metrics to {path}")

def export_audit_log(audit: dict, path: Path) -> None:
    """Write audit dict as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(audit, f, indent=4)
    logger.info(f"Exported audit log to {path}")

def generate_figures(df: pd.DataFrame, metrics: dict, fig_dir: Path) -> None:
    """Generate 4 PNG charts."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # 1. revenue_per_mile_by_borough.png
    plt.figure(figsize=(10, 6))
    df_rpm = df[df["trip_distance"] > 0].groupby("pu_borough")["fare_per_mile"].mean().reset_index()
    sns.barplot(data=df_rpm, x="pu_borough", y="fare_per_mile")
    plt.title("Mean Revenue per Mile by Pickup Borough")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(fig_dir / "revenue_per_mile_by_borough.png")
    plt.close()
    
    # 2. hourly_trip_volume.png
    plt.figure(figsize=(10, 6))
    if "tpep_pickup_datetime" in df.columns:
        df["hour"] = df["tpep_pickup_datetime"].dt.hour
        hourly = df.groupby("hour").size().reset_index(name="count")
        sns.lineplot(data=hourly, x="hour", y="count")
        plt.title("Hourly Trip Volume")
        plt.tight_layout()
        plt.savefig(fig_dir / "hourly_trip_volume.png")
    plt.close()
    
    # 3. data_quality_yield.png
    plt.figure(figsize=(8, 8))
    labels = ["Valid", "Invalid"]
    sizes = [metrics.get("valid_rows", 0), metrics.get("invalid_rows", 0)]
    if sum(sizes) > 0:
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title("Data Quality Yield")
        plt.tight_layout()
        plt.savefig(fig_dir / "data_quality_yield.png")
    plt.close()
    
    # 4. tip_distribution.png
    plt.figure(figsize=(12, 6))
    df_tips = df[(df["payment_type"] == 1) & (df["fare_amount"] > 0)].copy()
    if not df_tips.empty:
        df_tips["tip_pct"] = (df_tips["tip_amount"] / df_tips["fare_amount"]) * 100
        sns.boxplot(data=df_tips, x="pu_borough", y="tip_pct")
        plt.title("Tip % Distribution by Borough (Credit Card)")
        plt.ylim(0, 50)  # limit for readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(fig_dir / "tip_distribution.png")
    plt.close()
