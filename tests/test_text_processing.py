"""Tests for text processing utilities."""

import pytest
from src.spark_jobs.clean_normalize import (
    detect_language,
    strip_html,
    clean_text
)


def test_detect_language_english():
    """Test language detection for English text."""
    text = "This is a test sentence in English language."
    assert detect_language(text) == "en"


def test_detect_language_short_text():
    """Test language detection with short text."""
    text = "Hi"
    assert detect_language(text) is None


def test_detect_language_none():
    """Test language detection with None."""
    assert detect_language(None) is None


def test_strip_html_basic():
    """Test HTML stripping with basic tags."""
    html = "<p>Hello <b>world</b>!</p>"
    assert strip_html(html) == "Hello world!"


def test_strip_html_complex():
    """Test HTML stripping with complex markup."""
    html = """
    <div class="container">
        <h1>Title</h1>
        <p>Paragraph with <a href="url">link</a></p>
    </div>
    """
    result = strip_html(html)
    assert "Title" in result
    assert "Paragraph" in result
    assert "<" not in result


def test_strip_html_none():
    """Test HTML stripping with None."""
    assert strip_html(None) is None


def test_clean_text_urls():
    """Test URL removal."""
    text = "Check this out https://example.com/page and http://test.org"
    result = clean_text(text)
    assert "https://" not in result
    assert "http://" not in result


def test_clean_text_whitespace():
    """Test whitespace normalization."""
    text = "Multiple    spaces   and\n\nnewlines"
    result = clean_text(text)
    assert "  " not in result


def test_clean_text_special_chars():
    """Test special character removal."""
    text = "Text with special chars: @#$%^&*"
    result = clean_text(text)
    assert "@" not in result
    assert "#" not in result


def test_clean_text_none():
    """Test clean with None."""
    assert clean_text(None) is None
