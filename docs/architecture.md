# Architecture

## Overview

The Unstructured Intelligence Platform processes data from multiple public sources (Hacker News, Wikipedia, GitHub) to create a searchable knowledge base with semantic search capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BigQuery Public Datasets                     │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐ │
│  │    HN    │  │ Wikipedia │  │   GitHub   │  │ Open Images  │ │
│  └──────────┘  └───────────┘  └────────────┘  └──────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    Bronze Layer (GCS)   │
              │   Raw Parquet Files     │
              └────────────┬────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Spark ETL (Dataproc)  │
              │  - Deduplication       │
              │  - Language Detection  │
              │  - Text Cleaning       │
              └────────────┬────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
    ┌──────────────────┐   ┌────────────────────┐
    │ Great Expectations│   │  Silver Layer (GCS)│
    │  Data Quality     │   │  Cleaned Data      │
    └──────────────────┘   └──────────┬──────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │    NLP Processing      │
                         │  Sentence Transformers │
                         │   (all-MiniLM-L6-v2)  │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │   Gold Layer (GCS)     │
                         │  Embeddings + Metadata │
                         └────────────┬────────────┘
                                      │
                        ┌─────────────┴──────────────┐
                        │                            │
                        ▼                            ▼
            ┌──────────────────┐        ┌──────────────────────┐
            │  FAISS Indexes   │        │  BigQuery External   │
            │   (Vector DB)    │        │      Tables          │
            └─────────┬─────────┘        └──────────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │   Cloud Run API   │
            │     (FastAPI)     │
            │  /search          │
            │  /trending        │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │   API Consumers   │
            └──────────────────┘
```

## Orchestration

```
┌──────────────────────────────────────────────────┐
│         Cloud Composer (Airflow)                 │
│                                                  │
│  Daily Schedule (2 AM):                         │
│  1. Extract (BQ → GCS)                          │
│  2. Validate (Great Expectations)               │
│  3. Transform (Spark)                           │
│  4. Embed (Sentence Transformers)               │
│  5. Index (FAISS)                               │
│  6. Deploy (Cloud Run)                          │
└──────────────────────────────────────────────────┘
```

## Data Flow

### Bronze Layer (Raw Data)
- **Format**: Parquet (Snappy compressed)
- **Schema**: Original BigQuery schemas
- **Retention**: 30 days

### Silver Layer (Cleaned Data)
- **Format**: Parquet
- **Transformations**:
  - Deduplication by ID
  - Language detection (English only)
  - HTML/Markdown stripping
  - Text normalization
  - Length filtering (50-10,000 chars)
- **Schema**: Normalized across sources
- **Retention**: 90 days

### Gold Layer (Enriched Data)
- **Format**: Parquet with array columns
- **Features**:
  - Text embeddings (384-dimensional vectors)
  - Metadata (source, timestamp, scores)
  - Language, topics
- **Retention**: 180 days

## Technology Choices

### Why Spark on Dataproc Serverless?
- **Scalability**: Handles millions of documents
- **Cost**: Pay only for compute time
- **Integration**: Native BigQuery and GCS connectors
- **Flexibility**: PySpark UDFs for custom transformations

### Why Sentence Transformers (all-MiniLM-L6-v2)?
- **Quality**: State-of-art semantic similarity
- **Speed**: Fast inference (~2ms per document)
- **Size**: Small model (80MB) for edge deployment
- **Community**: Well-maintained, widely adopted

### Why FAISS?
- **Performance**: Sub-millisecond search on millions of vectors
- **Memory**: Efficient index compression
- **Flexibility**: Multiple index types (Flat, IVF, HNSW)
- **Battle-tested**: Production use at Meta

### Why Cloud Run?
- **Simplicity**: Containerized deployment
- **Cost**: Scale to zero when idle
- **Performance**: Auto-scaling on demand
- **Integration**: Native GCP services

## Performance Characteristics

| Component | Throughput | Latency |
|-----------|-----------|---------|
| BQ Extract | ~1M rows/min | - |
| Spark Clean | ~10K docs/sec | - |
| Embedding | ~500 docs/sec | ~2ms/doc |
| FAISS Build | 100K docs | ~30s |
| Search (P95) | - | <150ms |
| API (P99) | - | <300ms |

## Security

- **Authentication**: Google Cloud IAM
- **Authorization**: Workload Identity for services
- **Encryption**: At-rest (GCS) and in-transit (TLS)
- **Network**: VPC with private IPs
- **Secrets**: Secret Manager for credentials

## Monitoring

- **Cloud Logging**: Centralized logs
- **Cloud Monitoring**: Metrics and alerts
- **Cloud Trace**: Distributed tracing
- **Custom Metrics**: Embedding throughput, search latency

## Limitations

1. **Freshness**: Daily batch updates (not real-time)
2. **Scale**: Optimized for ~10M documents
3. **Languages**: English only (easily extensible)
4. **Compute**: CPU-based embedding (GPU available via Vertex AI)
5. **Cost**: BigQuery public dataset queries incur costs
