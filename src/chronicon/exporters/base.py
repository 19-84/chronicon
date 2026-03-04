# ABOUTME: Base exporter class for Chronicon
# ABOUTME: Provides common functionality for all export formats

"""Base exporter class."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseExporter(ABC):
    """Base class for all exporters."""

    def __init__(self, db, output_dir: Path, progress=None):
        """
        Initialize exporter.

        Args:
            db: ArchiveDatabase instance
            output_dir: Output directory for exported files
            progress: Optional Rich Progress object for progress tracking
        """
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress = progress

    @abstractmethod
    def export(self) -> None:
        """
        Main export method - must be implemented by subclasses.
        """
        pass

    def get_export_path(self, relative_path: str) -> Path:
        """
        Get full path for an export file.

        Args:
            relative_path: Relative path within output directory

        Returns:
            Full path to export file
        """
        return self.output_dir / relative_path

    @staticmethod
    def _safe_filename(slug: str, topic_id: int, max_length: int = 200) -> str:
        """
        Create a safe filename by truncating slug if needed.

        Ensures the slug portion doesn't make the total filename exceed
        filesystem limits. Most filesystems have a 255 character limit for
        filenames.

        Args:
            slug: Topic slug from Discourse
            topic_id: Topic ID for uniqueness
            max_length: Maximum length for slug portion (default 200)

        Returns:
            Truncated slug that's safe for filesystem use
        """
        if len(slug) <= max_length:
            return slug

        # Truncate and add ellipsis to indicate truncation
        return slug[: max_length - 3] + "..."
