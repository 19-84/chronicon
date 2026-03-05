# ABOUTME: URL rewriter for Chronicon
# ABOUTME: Converts absolute URLs to relative paths for offline viewing

"""Rewrite URLs from absolute to relative paths."""

import os
from pathlib import Path


class URLRewriter:
    """Rewrite URLs from absolute to relative paths."""

    def __init__(self, base_url: str):
        """
        Initialize URL rewriter.

        Args:
            base_url: Base URL of the Discourse forum
        """
        self.base_url = base_url.rstrip("/")

    def rewrite_image_url(self, url: str, local_path: Path, context_path: Path) -> str:
        """
        Rewrite an image URL to a relative local path.

        Args:
            url: Original image URL
            local_path: Local path where image is stored
            context_path: Path of the file referencing this image

        Returns:
            Relative URL
        """
        try:
            # Calculate relative path from context file to image
            # Both paths should be absolute
            context_dir = context_path.parent
            relative = os.path.relpath(local_path, context_dir)
            return relative
        except (ValueError, AttributeError):
            # If relative path calculation fails, return local path
            return str(local_path)

    def rewrite_user_link(self, username: str) -> str:
        """
        Rewrite a user profile link.

        Args:
            username: Username

        Returns:
            Relative URL to user profile
        """
        return f"/u/{username}/"

    def rewrite_topic_link(self, topic_id: int, slug: str) -> str:
        """
        Rewrite a topic link.

        Args:
            topic_id: Topic ID
            slug: Topic slug

        Returns:
            Relative URL to topic
        """
        return f"/t/{slug}/{topic_id}/"

    def rewrite_category_link(self, category_id: int, slug: str) -> str:
        """
        Rewrite a category link.

        Args:
            category_id: Category ID
            slug: Category slug

        Returns:
            Relative URL to category
        """
        return f"/c/{slug}/{category_id}/"
