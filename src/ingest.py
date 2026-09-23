"""Data ingestion module — file-based and SQL-based retrieval."""

import pandas as pd
import duckdb
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_trip_data(filepath: Path) -> pd.DataFrame:
    """Load trip parquet file with schema validation.

    Retrieval Mode 1: File-based (pandas + pyarrow).
    Logs row count and column count. Validates file exists.

    Args:
        filepath: Path to the parquet file.

    Returns:
        DataFrame with raw trip data.

    Raises:
        FileNotFoundError: If filepath does not exist.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Trip data file not found: {filepath}")

    logger.info(f"Loading trip data from {filepath}")
    df = pd.read_parquet(filepath)
    logger.info(f"Loaded {len(df):,} rows x {len(df.columns)} columns")
    return df


def load_zone_lookup(filepath: Path) -> pd.DataFrame:
    """Load zone CSV lookup table.

    Retrieval Mode 1: File-based (pandas).
    Validates that expected columns exist.

    Args:
        filepath: Path to the CSV file.

    Returns:
        DataFrame with zone lookup data.

    Raises:
        FileNotFoundError: If filepath does not exist.
        ValueError: If required columns are missing.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Zone lookup file not found: {filepath}")

    logger.info(f"Loading zone lookup from {filepath}")
    df = pd.read_csv(filepath)

    expected_cols = {"LocationID", "Borough", "Zone", "service_zone"}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"Zone lookup missing columns: {missing}")

    logger.info(f"Loaded {len(df):,} zones across {df['Borough'].nunique()} boroughs")
    return df


def query_with_duckdb(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    """Run analytical SQL query on a DataFrame via DuckDB.

    Retrieval Mode 2: SQL-based (DuckDB).
    The DataFrame is available as 'df' in the SQL query.

    Args:
        df: Source DataFrame to query.
        sql: SQL query string (reference the DataFrame as 'df').

    Returns:
        Query result as a DataFrame.

    Example:
        >>> query_with_duckdb(df_trips, 'SELECT PULocationID, COUNT(*) as cnt FROM df GROUP BY PULocationID')
    """
    logger.info(f"Executing DuckDB query: {sql[:120]}...")
    result = duckdb.sql(sql).df()
    logger.info(f"Query returned {len(result):,} rows")
    return result


def validate_ingestion_completeness(df: pd.DataFrame, expected_cols: list[str]) -> dict:
    """Check all expected columns exist and report completeness.

    Args:
        df: Ingested DataFrame to validate.
        expected_cols: List of column names that should be present.

    Returns:
        Dictionary with 'missing_cols', 'extra_cols', 'row_count', 'is_complete'.
    """
    actual = set(df.columns)
    expected = set(expected_cols)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    result = {
        "missing_cols": missing,
        "extra_cols": extra,
        "row_count": len(df),
        "is_complete": len(missing) == 0,
    }

    if missing:
        logger.warning(f"Ingestion missing columns: {missing}")
    else:
        logger.info(f"Ingestion complete: {len(df):,} rows, all {len(expected)} expected columns present")

    return result
