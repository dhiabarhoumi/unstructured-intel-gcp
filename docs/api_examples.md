# API Usage Examples

## Search Endpoint

### Basic Search
```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "machine learning optimization techniques",
    "k": 10
  }'
```

### Domain-Specific Search
```bash
# Search only HN
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "kubernetes scaling patterns",
    "k": 20,
    "domains": ["hn"]
  }'

# Search Wikipedia and GitHub
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "natural language processing",
    "k": 15,
    "domains": ["wikipedia", "github"]
  }'
```

## Trending Endpoint

### Get Top Trending Topics
```bash
curl "http://localhost:8080/trending?window=7d&top=50"
```

### Different Time Windows
```bash
# Last 30 days
curl "http://localhost:8080/trending?window=30d&top=100"

# Last 24 hours
curl "http://localhost:8080/trending?window=1d&top=25"
```

## Health Check

```bash
curl http://localhost:8080/healthz
```

Response:
```json
{
  "status": "healthy",
  "indexes_loaded": ["hn", "wikipedia", "github"],
  "total_documents": 125000,
  "model_loaded": true
}
```

## Python Client Example

```python
import requests

# Search example
response = requests.post(
    "http://localhost:8080/search",
    json={
        "q": "distributed systems consensus algorithms",
        "k": 15,
        "domains": ["hn", "github"]
    }
)

results = response.json()
for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Domain: {result['domain']}")
    print(f"ID: {result['id']}")
    print("---")

# Trending example
response = requests.get(
    "http://localhost:8080/trending",
    params={"window": "7d", "top": 20}
)

trending = response.json()
for item in trending:
    print(f"{item['title']} - {item['domain']}")
    print(f"Score: {item['score']:.2f}")
    print()
```

## JavaScript/TypeScript Client Example

```typescript
// Search
const searchResponse = await fetch('http://localhost:8080/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    q: 'vector databases performance',
    k: 10,
    domains: ['hn', 'github']
  })
});

const results = await searchResponse.json();
console.log(`Found ${results.length} results`);

// Trending
const trendingResponse = await fetch(
  'http://localhost:8080/trending?window=7d&top=30'
);
const trending = await trendingResponse.json();
```
