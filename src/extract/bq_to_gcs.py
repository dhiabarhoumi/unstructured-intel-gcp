"""Extract data from BigQuery to GCS"""

import argparse
import logging
from pathlib import Path

from google.cloud import bigquery
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_bq_to_gcs(
    project_id: str,
    query_sql: str,
    out_uri: str,
    format: str = "PARQUET",
) -> None:
    """
    Extract data from BigQuery using a SQL query and save to GCS.
    
    Args:
        project_id: GCP project ID
        query_sql: Path to SQL file or SQL query string
        out_uri: GCS URI to save output (e.g., gs://bucket/path/)
        format: Output format (PARQUET, CSV, JSON)
    """
    client = bigquery.Client(project=project_id)
    
    # Read SQL query
    if Path(query_sql).exists():
        with open(query_sql, "r") as f:
            query = f.read()
        logger.info(f"Loaded query from {query_sql}")
    else:
        query = query_sql
    
    # Configure extract job
    job_config = bigquery.QueryJobConfig()
    
    logger.info(f"Executing query...")
    query_job = client.query(query, job_config=job_config)
    
    # Wait for query to complete
    results = query_job.result()
    logger.info(f"Query completed. Processed {query_job.total_bytes_processed} bytes")
    
    # Create temp table for extraction
    temp_table_id = f"{project_id}.temp_dataset.extract_{query_job.job_id}"
    
    # Create dataset if doesn't exist
    dataset = bigquery.Dataset(f"{project_id}.temp_dataset")
    dataset.location = "US"
    try:
        client.create_dataset(dataset, exists_ok=True)
        logger.info("Created temp dataset")
    except Exception as e:
        logger.info(f"Dataset exists or error: {e}")
    
    # Save query results to temp table
    job_config = bigquery.QueryJobConfig(destination=temp_table_id)
    query_job = client.query(query, job_config=job_config)
    query_job.result()
    
    logger.info(f"Results saved to temp table {temp_table_id}")
    
    # Extract to GCS
    extract_config = bigquery.ExtractJobConfig()
    extract_config.destination_format = (
        getattr(bigquery.DestinationFormat, format)
    )
    
    if format == "PARQUET":
        extract_config.compression = bigquery.Compression.SNAPPY
    
    # Ensure URI ends with wildcard for sharding
    if not out_uri.endswith("*"):
        out_uri = out_uri.rstrip("/") + "/*.parquet"
    
    extract_job = client.extract_table(
        temp_table_id,
        out_uri,
        job_config=extract_config,
    )
    
    extract_job.result()
    logger.info(f"Extracted to {out_uri}")
    
    # Cleanup temp table
    client.delete_table(temp_table_id)
    logger.info(f"Cleaned up temp table")


def main():
    parser = argparse.ArgumentParser(description="Extract BigQuery data to GCS")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument(
        "--query_sql",
        required=True,
        help="Path to SQL file or SQL query string",
    )
    parser.add_argument(
        "--out_uri",
        required=True,
        help="GCS output URI (gs://bucket/path/)",
    )
    parser.add_argument(
        "--format",
        default="PARQUET",
        choices=["PARQUET", "CSV", "JSON"],
        help="Output format",
    )
    
    args = parser.parse_args()
    
    extract_bq_to_gcs(
        project_id=args.project,
        query_sql=args.query_sql,
        out_uri=args.out_uri,
        format=args.format,
    )


if __name__ == "__main__":
    main()
