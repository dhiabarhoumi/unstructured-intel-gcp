"""Utility functions for text processing."""

import re
from typing import Optional


def truncate_text(text: Optional[str], max_length: int = 500) -> Optional[str]:
    """
    Truncate text to max_length characters.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def extract_urls(text: Optional[str]) -> list[str]:
    """Extract all URLs from text."""
    if not text:
        return []
    
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def word_count(text: Optional[str]) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())
