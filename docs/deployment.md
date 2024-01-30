# Deployment Guide

## Prerequisites

- GCP Project with billing enabled
- `gcloud` CLI installed and configured
- Docker installed
- Python 3.11+

## Initial Setup

### 1. Enable Required APIs

```bash
gcloud services enable \
  bigquery.googleapis.com \
  storage.googleapis.com \
  dataproc.googleapis.com \
  run.googleapis.com \
  composer.googleapis.com \
  cloudscheduler.googleapis.com
```

### 2. Create GCS Bucket

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export BUCKET_NAME=unstructured-intel-${PROJECT_ID}

gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${BUCKET_NAME}
```

### 3. Set Up Bucket Structure

```bash
gsutil -m mkdir \
  gs://${BUCKET_NAME}/bronze \
  gs://${BUCKET_NAME}/silver \
  gs://${BUCKET_NAME}/gold \
  gs://${BUCKET_NAME}/reports \
  gs://${BUCKET_NAME}/faiss \
  gs://${BUCKET_NAME}/spark-deps
```

### 4. Upload Spark Jobs

```bash
gsutil -m cp src/spark_jobs/*.py gs://${BUCKET_NAME}/jobs/
```

## Deploy Cloud Run API

### Build and Deploy

```bash
gcloud run deploy unstructured-intel-api \
  --source . \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars FAISS_URI=gs://${BUCKET_NAME}/faiss/,PROJECT_ID=${PROJECT_ID}
```

### Test Deployment

```bash
SERVICE_URL=$(gcloud run services describe unstructured-intel-api \
  --region ${REGION} \
  --format 'value(status.url)')

curl ${SERVICE_URL}/healthz
```

## Set Up Cloud Composer

### Create Composer Environment

```bash
gcloud composer environments create unstructured-intel-composer \
  --location ${REGION} \
  --python-version 3.11 \
  --machine-type n1-standard-2 \
  --disk-size 30
```

### Upload DAG

```bash
COMPOSER_BUCKET=$(gcloud composer environments describe \
  unstructured-intel-composer \
  --location ${REGION} \
  --format 'value(config.dagGcsPrefix)')

gsutil cp airflow/dags/unstructured_dag.py ${COMPOSER_BUCKET}/
```

### Set Airflow Variables

```bash
gcloud composer environments run unstructured-intel-composer \
  --location ${REGION} \
  variables set -- gcp_project_id ${PROJECT_ID}

gcloud composer environments run unstructured-intel-composer \
  --location ${REGION} \
  variables set -- gcp_region ${REGION}

gcloud composer environments run unstructured-intel-composer \
  --location ${REGION} \
  variables set -- gcs_bucket gs://${BUCKET_NAME}
```

## Configure Dataproc Serverless

### Create Dataproc Metastore (Optional)

```bash
gcloud metastore services create unstructured-intel-metastore \
  --location ${REGION} \
  --tier=DEVELOPER \
  --hive-metastore-version 3.1.2
```

## Monitoring & Logging

### Create Log-Based Metrics

```bash
gcloud logging metrics create embedding_throughput \
  --description="Embedding processing throughput" \
  --log-filter='resource.type="cloud_run_revision" 
    jsonPayload.message=~"Embedded.*documents"'
```

### Set Up Alerts

```bash
# Create alert for API errors
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="API Error Rate" \
  --condition-threshold-value=10 \
  --condition-threshold-duration=60s
```

## Security

### Create Service Account

```bash
gcloud iam service-accounts create unstructured-intel-sa \
  --display-name="Unstructured Intel Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:unstructured-intel-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:unstructured-intel-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

## Cost Optimization

### Set Lifecycle Policies

```bash
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["bronze/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["silver/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://${BUCKET_NAME}
```

### Enable Request Logging

```bash
gcloud logging sinks create unstructured-intel-logs \
  storage.googleapis.com/${BUCKET_NAME}/logs \
  --log-filter='resource.type="cloud_run_revision"'
```

## Troubleshooting

### View Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Dataproc logs
gcloud logging read "resource.type=dataproc.googleapis.com/Job" --limit 50
```

### Debug Spark Jobs

```bash
# Submit test job
gcloud dataproc batches submit pyspark \
  gs://${BUCKET_NAME}/jobs/clean_normalize.py \
  --region=${REGION} \
  --deps-bucket=${BUCKET_NAME}/spark-deps \
  -- --in gs://${BUCKET_NAME}/bronze/test/ \
     --out gs://${BUCKET_NAME}/silver/test/ \
     --dataset hn_stories
```
