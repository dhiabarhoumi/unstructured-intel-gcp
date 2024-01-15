"""pytest configuration."""

import pytest


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "This is a sample text for testing natural language processing."


@pytest.fixture
def sample_html():
    """Sample HTML for testing."""
    return "<p>Hello <b>world</b>!</p>"


@pytest.fixture
def sample_embeddings():
    """Sample embeddings for testing."""
    import numpy as np
    return np.random.rand(10, 384).astype('float32')
