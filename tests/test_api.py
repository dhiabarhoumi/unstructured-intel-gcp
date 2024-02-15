"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "indexes_loaded" in data
    assert "model_loaded" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "endpoints" in data


def test_search_endpoint_structure():
    """Test search endpoint structure."""
    payload = {
        "q": "machine learning",
        "k": 10,
        "domains": ["hn"]
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_search_validation_invalid_k():
    """Test search validation with invalid k."""
    payload = {
        "q": "test",
        "k": 0,  # Invalid: must be >= 1
        "domains": ["hn"]
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 422  # Validation error


def test_trending_endpoint():
    """Test trending endpoint."""
    response = client.get("/trending?window=7d&top=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_trending_default_params():
    """Test trending with default parameters."""
    response = client.get("/trending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 50  # Default top=50
