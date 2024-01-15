"""
Airflow DAG for Unstructured Intelligence Platform.

Daily orchestration:
1. Extract from BigQuery to GCS (bronze)
2. Run data quality checks
3. Clean and normalize (silver)
4. Generate embeddings (gold)
5. Build FAISS indexes
6. Publish to Cloud Run
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocSubmitJobOperator,
    DataprocCreateClusterOperator,
    DataprocDeleteClusterOperator
)
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

# Configuration
PROJECT_ID = "{{ var.value.gcp_project_id }}"
REGION = "{{ var.value.gcp_region }}"
BUCKET = "{{ var.value.gcs_bucket }}"
CLUSTER_NAME = "unstructured-intel-cluster"

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 15),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "unstructured_intelligence_pipeline",
    default_args=default_args,
    description="Daily ETL for unstructured intelligence platform",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    catchup=False,
    tags=["data-engineering", "nlp", "gcp"],
)

# Task 1: Extract HN Stories
extract_hn_stories = BigQueryToGCSOperator(
    task_id="extract_hn_stories",
    source_project_dataset_table=f"{PROJECT_ID}.bronze.hn_stories_temp",
    destination_cloud_storage_uris=[f"{BUCKET}/bronze/hn_stories/*.parquet"],
    export_format="PARQUET",
    compression="SNAPPY",
    dag=dag,
)

# Task 2: Extract HN Comments
extract_hn_comments = BigQueryToGCSOperator(
    task_id="extract_hn_comments",
    source_project_dataset_table=f"{PROJECT_ID}.bronze.hn_comments_temp",
    destination_cloud_storage_uris=[f"{BUCKET}/bronze/hn_comments/*.parquet"],
    export_format="PARQUET",
    compression="SNAPPY",
    dag=dag,
)

# Task 3: Extract Wikipedia
extract_wikipedia = BigQueryToGCSOperator(
    task_id="extract_wikipedia",
    source_project_dataset_table=f"{PROJECT_ID}.bronze.wiki_pageviews_temp",
    destination_cloud_storage_uris=[f"{BUCKET}/bronze/wiki_pageviews/*.parquet"],
    export_format="PARQUET",
    compression="SNAPPY",
    dag=dag,
)

# Task 4: Extract GitHub
extract_github = BigQueryToGCSOperator(
    task_id="extract_github",
    source_project_dataset_table=f"{PROJECT_ID}.bronze.github_readmes_temp",
    destination_cloud_storage_uris=[f"{BUCKET}/bronze/github_readmes/*.parquet"],
    export_format="PARQUET",
    compression="SNAPPY",
    dag=dag,
)

# Task Group: Data Quality Checks
with TaskGroup("data_quality", dag=dag) as dq_group:
    
    def run_ge_validation(**context):
        """Run Great Expectations validation."""
        import subprocess
        
        datasets = ["hn_stories", "hn_comments", "wiki_pageviews", "github_readmes"]
        
        for dataset in datasets:
            cmd = [
                "python", "src/dq/run_ge.py",
                "--suite", f"conf/ge/{dataset}_suite.yml",
                "--target", f"{BUCKET}/bronze/{dataset}/"
            ]
            subprocess.run(cmd, check=True)
    
    validate_data = PythonOperator(
        task_id="validate_with_ge",
        python_callable=run_ge_validation,
    )

# Task Group: Clean and Normalize (Silver)
with TaskGroup("clean_normalize", dag=dag) as clean_group:
    
    # Dataproc job configs
    spark_job_config = {
        "reference": {"project_id": PROJECT_ID},
        "placement": {"cluster_name": CLUSTER_NAME},
        "pyspark_job": {
            "main_python_file_uri": f"{BUCKET}/jobs/clean_normalize.py",
            "jar_file_uris": ["gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar"],
        },
    }
    
    clean_hn_stories = DataprocSubmitJobOperator(
        task_id="clean_hn_stories",
        job=spark_job_config,
        region=REGION,
        project_id=PROJECT_ID,
    )

# Task Group: Generate Embeddings (Gold)
with TaskGroup("embeddings", dag=dag) as embed_group:
    
    embed_job_config = {
        "reference": {"project_id": PROJECT_ID},
        "placement": {"cluster_name": CLUSTER_NAME},
        "pyspark_job": {
            "main_python_file_uri": f"{BUCKET}/jobs/embed_texts.py",
            "jar_file_uris": ["gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar"],
        },
    }
    
    embed_hn = DataprocSubmitJobOperator(
        task_id="embed_hn",
        job=embed_job_config,
        region=REGION,
        project_id=PROJECT_ID,
    )

# Task: Build FAISS Indexes
def build_indexes(**context):
    """Build FAISS indexes for all domains."""
    import subprocess
    
    domains = ["hn", "wikipedia", "github"]
    
    for domain in domains:
        cmd = [
            "python", "src/index/build_faiss.py",
            "--in", f"{BUCKET}/gold/{domain}/",
            "--out", f"{BUCKET}/faiss/",
            "--index_name", f"{domain}_index"
        ]
        subprocess.run(cmd, check=True)

build_faiss = PythonOperator(
    task_id="build_faiss_indexes",
    python_callable=build_indexes,
    dag=dag,
)

# Task: Deploy to Cloud Run
def deploy_api(**context):
    """Deploy updated API to Cloud Run."""
    import subprocess
    
    cmd = [
        "gcloud", "run", "deploy", "intel-search",
        "--source", ".",
        "--region", REGION,
        "--allow-unauthenticated",
        "--set-env-vars", f"FAISS_URI={BUCKET}/faiss/"
    ]
    subprocess.run(cmd, check=True)

deploy_cloud_run = PythonOperator(
    task_id="deploy_to_cloud_run",
    python_callable=deploy_api,
    dag=dag,
)

# Define task dependencies
[extract_hn_stories, extract_hn_comments, extract_wikipedia, extract_github] >> dq_group
dq_group >> clean_group >> embed_group >> build_faiss >> deploy_cloud_run
