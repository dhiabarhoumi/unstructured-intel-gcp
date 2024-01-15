"""Tests for FAISS index building."""

import pytest
import numpy as np
from src.index.build_faiss import build_faiss_index


def test_build_flat_index():
    """Test building a flat FAISS index."""
    embeddings = np.random.rand(100, 384).astype('float32')
    index = build_faiss_index(embeddings, index_type="Flat")
    
    assert index.ntotal == 100
    assert index.d == 384


def test_build_hnsw_index():
    """Test building an HNSW index."""
    embeddings = np.random.rand(100, 384).astype('float32')
    index = build_faiss_index(embeddings, index_type="HNSW")
    
    assert index.ntotal == 100
    assert index.d == 384


def test_search_index():
    """Test searching in FAISS index."""
    # Create dummy embeddings
    embeddings = np.random.rand(100, 384).astype('float32')
    index = build_faiss_index(embeddings, index_type="Flat")
    
    # Search
    query = np.random.rand(1, 384).astype('float32')
    distances, indices = index.search(query, k=5)
    
    assert len(distances[0]) == 5
    assert len(indices[0]) == 5
    assert all(idx < 100 for idx in indices[0])
