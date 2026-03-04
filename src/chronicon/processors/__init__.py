# ABOUTME: Processors module for Chronicon
# ABOUTME: Handles content processing, HTML parsing, URL rewriting, and theme extraction

"""
Content processing layer for Discourse archives.

This module provides processors for HTML content, URL rewriting,
and theme extraction from Discourse CSS.
"""

from .html_parser import HTMLProcessor
from .url_rewriter import URLRewriter

__all__ = ["HTMLProcessor", "URLRewriter"]
