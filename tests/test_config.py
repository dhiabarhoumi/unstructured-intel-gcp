"""Tests for configuration module."""

import pytest
from src.config import Settings, get_settings


def test_settings_default_values():
    """Test default configuration values."""
    settings = Settings()
    
    assert settings.region == "us-central1"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8080
    assert settings.log_level == "INFO"
    assert settings.embedding_model == "all-MiniLM-L6-v2"


def test_settings_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("PROJECT_ID", "test-project")
    monkeypatch.setenv("REGION", "us-west1")
    monkeypatch.setenv("API_PORT", "9000")
    
    settings = Settings()
    
    assert settings.project_id == "test-project"
    assert settings.region == "us-west1"
    assert settings.api_port == 9000


def test_get_settings():
    """Test get_settings function."""
    settings = get_settings()
    assert isinstance(settings, Settings)
