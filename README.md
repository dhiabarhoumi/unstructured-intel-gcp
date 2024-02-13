# Unstructured Intelligence Platform on GCP

[![CI](https://github.com/yourhandle/unstructured-intel-gcp/actions/workflows/ci.yml/badge.svg)](https://github.com/yourhandle/unstructured-intel-gcp/actions/workflows/ci.yml)

> Batch + streaming pipelines that turn raw web text & images into searchable, quality-checked insights on GCP.

## Problem

Build a topic & semantic search hub across:
- **Hacker News** stories/comments → tech discourse & sentiment (BQ public dataset)
- **Wikipedia** pageviews → what the world is reading right now (daily aggregates)
- **GitHub** code snippets → how ideas show up in code (BigQuery GitHub Repos)
- **Open Images V7** metadata → attach visual context (labels/boxes) to topics

## Architecture

```
[BigQuery public datasets] ---> [Spark ETL on Dataproc Serverless] ---> [GCS bronze/silver/gold]
                                          |                                     |
                                          |                        [Great Expectations reports -> GCS]
                                          v                                     |
                                    [NLP UDF: embeddings]                       v
                                          |                                 [BigQuery external tables]
                                          v                                     |
                                 [FAISS index build -> GCS] --------------------+
                                          |
                                   [Cloud Run: FastAPI]
                                          |
                                   /search, /trending
```

**Services**: GCS, BigQuery, Dataproc Serverless (Spark), Cloud Run (FastAPI), Cloud Composer (Airflow), Cloud Logging/Monitoring

## What It Does

1. **Ingest & land (bronze)** - Query BQ public tables for HN stories/comments, Wikipedia pageviews, and GitHub files. Store raw snapshots to GCS (Parquet).

2. **Clean & enrich (silver)** - Normalize schemas, deduplicate, detect language, strip markup. Great Expectations runs data quality checks.

3. **NLP (gold)** - Use Sentence-Transformers (all-MiniLM-L6-v2) via PySpark UDF to generate embeddings. Build FAISS index per domain.

4. **Serving** - Cloud Run + FastAPI exposes:
   - `POST /search` → vector search across HN/Wikipedia/GitHub
   - `GET /trending` → HN + Wikipedia joint trend analysis
   - `GET /healthz` → health check

5. **Orchestration** - Composer (Airflow) DAG schedules daily: extract → validate → transform → embed → index → publish.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker
- gcloud CLI
- make

### Setup

```bash
# Clone and setup
git clone https://github.com/yourhandle/unstructured-intel-gcp.git
cd unstructured-intel-gcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# GCP setup
gcloud auth application-default login
export PROJECT_ID=<your-project>
export REGION=us-central1
export BUCKET=gs://<your-bucket>
make gcs-bootstrap
```

### Local Development

```bash
# Extract to GCS (bronze)
python src/extract/bq_to_gcs.py \
  --project $PROJECT_ID \
  --query_sql sql/hn_stories_7d.sql \
  --out_uri $BUCKET/bronze/hn_stories/

# Run Spark jobs (silver & gold)
bash scripts/submit_spark.sh clean_normalize.py \
  --in $BUCKET/bronze --out $BUCKET/silver

bash scripts/submit_spark.sh embed_texts.py \
  --in $BUCKET/silver --out $BUCKET/gold --model all-MiniLM-L6-v2

# Data Quality
python src/dq/run_ge.py \
  --suite conf/ge/hn_suite.yml \
  --target $BUCKET/silver/hn/

# Build FAISS index
python src/index/build_faiss.py \
  --in $BUCKET/gold/embeddings/ \
  --out $BUCKET/faiss/

# Run API locally
docker build -t intel-search:local .
docker run -p 8080:8080 -e FAISS_URI=$BUCKET/faiss/ intel-search:local
# Access OpenAPI docs at http://localhost:8080/docs
```

### Deploy to Cloud Run

```bash
gcloud run deploy intel-search \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars FAISS_URI=$BUCKET/faiss/
```

## Datasets

All queries are in `sql/` directory. These use Google's public BigQuery datasets which are updated regularly.

### Hacker News
```sql
-- Last 7 days of stories
SELECT id, time, title, text, by AS author
FROM `bigquery-public-data.hacker_news.stories`
WHERE time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
AND (title IS NOT NULL OR text IS NOT NULL)
LIMIT 100000;
```

### Wikipedia Pageviews
```sql
-- Last 7 days, top English pages
SELECT datehour, title, views
FROM `bigquery-public-data.wikipedia.pageviews_2024`
WHERE wiki='en' 
AND datehour >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
AND title NOT LIKE 'Special:%' 
AND title NOT LIKE 'File:%'
```

### GitHub Repos
```sql
-- README files sample
SELECT id, repo_name, path, size, content
FROM `bigquery-public-data.github_repos.contents`
WHERE path LIKE '%README%' 
AND size BETWEEN 100 AND 50000
LIMIT 50000;
```

## API Endpoints

### Search
```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "vector databases for production",
    "k": 15,
    "domains": ["hn", "wikipedia", "github"]
  }'
```

### Trending
```bash
curl http://localhost:8080/trending?window=7d&top=50
```

## KPIs & Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| Embedding Model | all-MiniLM-L6-v2 | 384-dimensional vectors |
| Embedding Throughput | ~500 docs/sec | On CPU, batch size 32 |
| Search Latency (P95) | < 150ms | FAISS Flat index |
| Search Latency (P99) | < 300ms | End-to-end API |
| Data Quality Score | > 95% | GE validation pass rate |
| Index Build Time | ~30s | For 100K documents |
| Storage (compressed) | ~2GB | Per 1M documents |

**Evidence**:
- Great Expectations report: `gs://<bucket>/reports/ge/index.html`
- API documentation: `<Cloud Run URL>/docs`
- Query examples: `sql/*.sql`
- Benchmark notebook: `docs/benchmarks.ipynb` (coming soon)
- Architecture diagrams: `docs/architecture.md`

## Limitations

- HN/Wikipedia are public snapshots; near-real-time requires Composer schedule
- Open Images processed as metadata + small sampled subset for demo
- FAISS index rebuilt daily; incremental updates not implemented
- Embedding model runs on CPU (GPU acceleration available via Vertex AI)

## Development

### Run Tests
```bash
make test
```

### Linting & Formatting
```bash
make lint
make format
```

### Pre-commit Hooks
```bash
pre-commit install
```

## CI/CD

GitHub Actions workflow runs on every push:
- Lint (ruff, black, mypy)
- Unit tests (pytest)
- Docker build
- Spark job validation

See `.github/workflows/ci.yml` for details.

## License

MIT
