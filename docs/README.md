# Unstructured Intelligence Platform

Architecture diagram showing the data flow from BigQuery public datasets through processing layers to the API.

![Architecture Diagram](architecture_flow.png)

## Components

### Data Sources
- BigQuery Public Datasets (HN, Wikipedia, GitHub)

### Processing Layers
- **Bronze**: Raw data from BigQuery
- **Silver**: Cleaned and normalized data
- **Gold**: Enriched data with embeddings

### Services
- **Dataproc Serverless**: Spark ETL jobs
- **Cloud Storage**: Data lake
- **Cloud Run**: FastAPI service
- **Cloud Composer**: Orchestration

### Search Infrastructure
- **FAISS**: Vector similarity search
- **Sentence Transformers**: Text embeddings

## Screenshots

(Add screenshots of API responses, Great Expectations reports, and BigQuery results)

## Data Quality Reports

Great Expectations validation reports are generated daily and stored in GCS:
- `gs://<bucket>/reports/ge/index.html`
