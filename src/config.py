"""Configuration module for application settings."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # GCP
    project_id: str = Field(default="", env="PROJECT_ID")
    region: str = Field(default="us-central1", env="REGION")
    bucket: str = Field(default="", env="BUCKET")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8080, env="API_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # FAISS
    faiss_uri: str = Field(default="gs://unstructured-intel/faiss/", env="FAISS_URI")
    faiss_index_type: str = Field(default="Flat", env="FAISS_INDEX_TYPE")
    
    # Embedding
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    
    # Search
    search_max_k: int = Field(default=100, env="SEARCH_MAX_K")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
