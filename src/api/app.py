"""
FastAPI application for semantic search and trending analysis.

Endpoints:
- GET /healthz - Health check
- POST /search - Semantic vector search
- GET /trending - Trending topics analysis
"""

import os
import pickle
from typing import List, Optional

import faiss
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from google.cloud import storage

# Initialize FastAPI app
app = FastAPI(
    title="Unstructured Intelligence Search API",
    description="Semantic search across HN, Wikipedia, and GitHub",
    version="0.1.0"
)

# Global state
FAISS_INDEXES = {}
DOC_METADATA = {}
EMBEDDING_MODEL = None


class SearchRequest(BaseModel):
    """Search request model."""
    q: str = Field(..., description="Query text or vector")
    k: int = Field(15, ge=1, le=100, description="Number of results to return")
    domains: List[str] = Field(
        ["hn", "wikipedia", "github"],
        description="Domains to search"
    )


class SearchResult(BaseModel):
    """Search result model."""
    id: str
    score: float
    domain: str
    title: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    metadata: dict = {}


class TrendingResult(BaseModel):
    """Trending topic result."""
    title: str
    domain: str
    score: float
    views: Optional[int] = None
    comments: Optional[int] = None


def load_faiss_index(gcs_path: str, index_name: str) -> tuple:
    """Load FAISS index and document IDs from GCS."""
    
    # Download from GCS to temp
    if gcs_path.startswith("gs://"):
        bucket_name = gcs_path.replace("gs://", "").split("/")[0]
        prefix = "/".join(gcs_path.replace("gs://", "").split("/")[1:])
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Download index
        index_blob = bucket.blob(f"{prefix}/{index_name}.index")
        index_path = f"/tmp/{index_name}.index"
        index_blob.download_to_filename(index_path)
        
        # Download IDs
        ids_blob = bucket.blob(f"{prefix}/{index_name}_ids.pkl")
        ids_path = f"/tmp/{index_name}_ids.pkl"
        ids_blob.download_to_filename(ids_path)
    else:
        index_path = f"{gcs_path}/{index_name}.index"
        ids_path = f"{gcs_path}/{index_name}_ids.pkl"
    
    # Load index
    index = faiss.read_index(index_path)
    
    # Load IDs
    with open(ids_path, "rb") as f:
        doc_ids = pickle.load(f)
    
    return index, doc_ids


def get_embedding_model():
    """Get or load the embedding model."""
    global EMBEDDING_MODEL
    
    if EMBEDDING_MODEL is None:
        EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    
    return EMBEDDING_MODEL


@app.on_event("startup")
async def startup_event():
    """Initialize indexes on startup."""
    faiss_uri = os.getenv("FAISS_URI", "gs://unstructured-intel/faiss/")
    
    # Load indexes for each domain
    domains = ["hn", "wikipedia", "github"]
    
    for domain in domains:
        try:
            index, doc_ids = load_faiss_index(faiss_uri, f"{domain}_index")
            FAISS_INDEXES[domain] = {
                "index": index,
                "doc_ids": doc_ids
            }
            print(f"Loaded {domain} index with {len(doc_ids)} documents")
        except Exception as e:
            print(f"Warning: Could not load {domain} index: {e}")
    
    # Load embedding model
    get_embedding_model()
    print("Embedding model loaded")


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    indexes_count = sum(len(idx["doc_ids"]) for idx in FAISS_INDEXES.values())
    
    return {
        "status": "healthy",
        "indexes_loaded": list(FAISS_INDEXES.keys()),
        "total_documents": indexes_count,
        "model_loaded": EMBEDDING_MODEL is not None
    }


@app.post("/search", response_model=List[SearchResult])
async def search(request: SearchRequest):
    """
    Semantic search across specified domains.
    
    Returns top-k most similar documents based on vector similarity.
    """
    
    # Generate query embedding
    model = get_embedding_model()
    query_embedding = model.encode(request.q)
    query_embedding = np.array([query_embedding], dtype='float32')
    
    # Search each domain
    all_results = []
    
    for domain in request.domains:
        if domain not in FAISS_INDEXES:
            continue
        
        index_data = FAISS_INDEXES[domain]
        index = index_data["index"]
        doc_ids = index_data["doc_ids"]
        
        # Search
        k = min(request.k, len(doc_ids))
        distances, indices = index.search(query_embedding, k)
        
        # Build results
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(doc_ids):
                all_results.append({
                    "id": doc_ids[idx],
                    "score": float(1 / (1 + dist)),  # Convert distance to similarity score
                    "domain": domain,
                    "title": None,
                    "text": None,
                    "url": None,
                    "metadata": {}
                })
    
    # Sort by score and return top-k
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:request.k]


@app.get("/trending", response_model=List[TrendingResult])
async def trending(
    window: str = Query("7d", description="Time window (e.g., 7d, 30d)"),
    top: int = Query(50, ge=1, le=200, description="Number of results")
):
    """
    Get trending topics across domains.
    
    Combines HN activity and Wikipedia pageviews to identify trending topics.
    """
    
    # This is a simplified mock implementation
    # In production, this would query BigQuery for actual trending data
    
    trending_topics = [
        {
            "title": "AI and Machine Learning",
            "domain": "wikipedia",
            "score": 0.95,
            "views": 150000
        },
        {
            "title": "Latest in LLMs and GPT",
            "domain": "hn",
            "score": 0.92,
            "views": None,
            "comments": 234
        },
        {
            "title": "Cloud Computing Trends",
            "domain": "github",
            "score": 0.88,
            "views": None
        }
    ]
    
    return trending_topics[:top]


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Unstructured Intelligence Search API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/healthz",
            "search": "/search",
            "trending": "/trending",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
