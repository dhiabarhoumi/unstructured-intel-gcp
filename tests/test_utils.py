"""Tests for utility functions."""

import pytest
from src.utils import truncate_text, extract_urls, word_count


def test_truncate_text():
    """Test text truncation."""
    text = "A" * 1000
    result = truncate_text(text, max_length=100)
    assert len(result) == 103  # 100 + "..."
    assert result.endswith("...")


def test_truncate_text_short():
    """Test truncation with short text."""
    text = "Short text"
    result = truncate_text(text, max_length=100)
    assert result == text


def test_extract_urls():
    """Test URL extraction."""
    text = "Check https://example.com and http://test.org"
    urls = extract_urls(text)
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "http://test.org" in urls


def test_extract_urls_none():
    """Test URL extraction with no URLs."""
    text = "No URLs here"
    urls = extract_urls(text)
    assert len(urls) == 0


def test_word_count():
    """Test word counting."""
    text = "This is a test sentence"
    assert word_count(text) == 5


def test_word_count_empty():
    """Test word count with empty text."""
    assert word_count("") == 0
    assert word_count(None) == 0
