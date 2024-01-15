#!/bin/bash
# Submit Spark job to Dataproc Serverless

set -e

SCRIPT_NAME=$1
shift  # Remove first argument

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
BUCKET=${BUCKET:-gs://unstructured-intel-dev}

echo "Submitting Spark job: $SCRIPT_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

gcloud dataproc batches submit pyspark \
    src/spark_jobs/$SCRIPT_NAME \
    --project=$PROJECT_ID \
    --region=$REGION \
    --deps-bucket=$BUCKET/spark-deps \
    --properties=spark.executor.memory=8g,spark.driver.memory=4g \
    --subnet=default \
    -- "$@"

echo "Spark job submitted successfully"
