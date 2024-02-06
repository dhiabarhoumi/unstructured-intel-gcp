# Performance Tuning Guide

## Embedding Generation

### Batch Size Optimization

The embedding batch size significantly impacts throughput:

```python
# Test different batch sizes
BATCH_SIZES = [8, 16, 32, 64, 128]

for batch_size in BATCH_SIZES:
    # Configure in spark job
    spark.conf.set("spark.embedding.batch_size", batch_size)
```

**Recommendations:**
- CPU: batch_size = 32
- GPU: batch_size = 128-256
- Memory-constrained: batch_size = 16

### Parallel Processing

```python
# Adjust Spark parallelism
spark.conf.set("spark.default.parallelism", "200")
spark.conf.set("spark.sql.shuffle.partitions", "200")

# Repartition data
df = df.repartition(200)
```

## FAISS Index Selection

### Index Types Comparison

| Index Type | Build Time | Search Time | Memory | Accuracy |
|------------|-----------|-------------|---------|----------|
| Flat | Fast | Slow | High | 100% |
| IVF | Medium | Fast | Medium | 95-99% |
| HNSW | Slow | Very Fast | High | 95-99% |
| PQ | Fast | Fast | Low | 90-95% |

### When to Use Each

**Flat (IndexFlatL2)**
```python
# Best for: < 1M vectors, exact search required
index = faiss.IndexFlatL2(dimension)
```

**IVF (IndexIVFFlat)**
```python
# Best for: 1M-10M vectors, good accuracy/speed tradeoff
quantizer = faiss.IndexFlatL2(dimension)
nlist = 100  # number of clusters
index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
index.train(embeddings)
index.nprobe = 10  # search in 10 clusters
```

**HNSW (IndexHNSWFlat)**
```python
# Best for: fastest search, higher memory ok
M = 32  # number of connections
index = faiss.IndexHNSWFlat(dimension, M)
index.hnsw.efConstruction = 40  # build quality
index.hnsw.efSearch = 16  # search quality
```

**Product Quantization**
```python
# Best for: > 10M vectors, memory constrained
m = 8  # number of subquantizers
nbits = 8  # bits per subquantizer
index = faiss.IndexPQ(dimension, m, nbits)
```

## BigQuery Optimization

### Partition Filtering

```sql
-- Use partition filters to reduce scanned data
SELECT *
FROM `bigquery-public-data.hacker_news.stories`
WHERE DATE(time) BETWEEN '2024-01-01' AND '2024-01-31'  -- partition filter
AND score > 10
```

### Clustering

```sql
-- Use clustering columns for better performance
CREATE TABLE processed_stories
CLUSTER BY domain, date
AS SELECT ...
```

### Materialized Views

```sql
-- Cache frequently accessed aggregations
CREATE MATERIALIZED VIEW trending_topics AS
SELECT 
  DATE(time) as date,
  REGEXP_EXTRACT(title, r'\b[A-Z][a-z]+\b') as topic,
  COUNT(*) as frequency
FROM `bigquery-public-data.hacker_news.stories`
GROUP BY date, topic
```

## Spark Tuning

### Memory Configuration

```bash
# Executor memory
--executor-memory 8g
--executor-cores 4
--num-executors 10

# Driver memory
--driver-memory 4g
```

### Broadcast Joins

```python
from pyspark.sql.functions import broadcast

# Broadcast small tables
df_result = large_df.join(
    broadcast(small_df),
    "key"
)
```

### Caching

```python
# Cache frequently accessed DataFrames
df_filtered = df.filter(col("language") == "en")
df_filtered.cache()
df_filtered.count()  # materialize cache
```

## Cloud Run Scaling

### Concurrency Settings

```bash
gcloud run deploy intel-search \
  --concurrency 80 \  # requests per instance
  --max-instances 10 \  # max scale
  --min-instances 1    # keep warm
```

### Cold Start Optimization

```python
# Lazy load heavy models
@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

# Pre-warm with startup probe
@app.get("/startup")
async def startup():
    get_model()  # load model
    return {"status": "ready"}
```

## Data Quality Performance

### Sampling Strategy

```python
# Sample data for validation
sample_size = 10000
df_sample = df.sample(False, sample_size / df.count())

# Run GE on sample
validate(df_sample)
```

### Parallel Validation

```python
# Run expectations in parallel
expectations = [
    ExpectColumnValuesToNotBeNull("id"),
    ExpectColumnValuesToBeInSet("language", ["en"]),
    ExpectColumnValueLengthsToBeBetween("text", 50, 10000),
]

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_expectation, expectations))
```

## Monitoring Metrics

### Key Metrics to Track

```python
import time
from prometheus_client import Counter, Histogram

# Request latency
REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'API request latency'
)

# Embedding throughput
EMBEDDING_COUNTER = Counter(
    'embeddings_generated_total',
    'Total embeddings generated'
)

# Search operations
SEARCH_COUNTER = Counter(
    'searches_total',
    'Total searches performed',
    ['domain']
)
```

### Custom Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_performance(operation, duration, metadata=None):
    """Structured logging for performance tracking."""
    log_entry = {
        "operation": operation,
        "duration_ms": duration * 1000,
        "timestamp": time.time(),
        **(metadata or {})
    }
    logger.info(json.dumps(log_entry))
```

## Cost Optimization

### BigQuery

- Use partition and cluster filtering
- Set query cost limits
- Use BI Engine for frequently accessed data

### Cloud Storage

- Use lifecycle policies
- Compress data (Snappy/Gzip)
- Use appropriate storage class

### Compute

- Use preemptible VMs for Spark
- Scale Cloud Run to zero when idle
- Use sustained use discounts

## Benchmarking

### Load Testing

```bash
# Install k6
brew install k6

# Run load test
k6 run --vus 50 --duration 30s loadtest.js
```

```javascript
// loadtest.js
import http from 'k6/http';
import { check } from 'k6';

export default function () {
  const payload = JSON.stringify({
    q: 'machine learning',
    k: 10
  });

  const response = http.post(
    'http://localhost:8080/search',
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(response, {
    'is status 200': (r) => r.status === 200,
    'response time < 300ms': (r) => r.timings.duration < 300,
  });
}
```
