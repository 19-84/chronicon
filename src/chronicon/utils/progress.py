# ABOUTME: Custom Rich progress columns for Chronicon
# ABOUTME: Provides custom progress columns for displaying rates and statistics

"""Custom progress columns for enhanced CLI display."""

from rich.progress import ProgressColumn, Task
from rich.text import Text


class RateColumn(ProgressColumn):
    """Displays processing rate in items per second."""

    def __init__(self, unit: str = "items", table_column=None):
        """
        Initialize rate column.

        Args:
            unit: Unit name for display (e.g., "topics", "posts", "requests")
            table_column: Rich table column configuration
        """
        super().__init__(table_column=table_column)
        self.unit = unit

    def render(self, task: Task) -> Text:
        """
        Render the rate column.

        Args:
            task: Rich progress task

        Returns:
            Formatted text with rate
        """
        if task.finished or task.speed is None:
            return Text("--", style="progress.data.speed")

        # Format rate based on magnitude
        rate = task.speed
        if rate >= 10:
            return Text(f"{rate:.1f} {self.unit}/s", style="progress.data.speed")
        elif rate >= 1:
            return Text(f"{rate:.2f} {self.unit}/s", style="progress.data.speed")
        else:
            return Text(f"{rate:.3f} {self.unit}/s", style="progress.data.speed")


class CompactTimeRemainingColumn(ProgressColumn):
    """Displays estimated time remaining in compact format."""

    def render(self, task: Task) -> Text:
        """
        Render the time remaining column.

        Args:
            task: Rich progress task

        Returns:
            Formatted text with ETA
        """
        if task.finished:
            return Text("Done", style="progress.elapsed")

        if task.time_remaining is None:
            return Text("--:--", style="progress.remaining")

        remaining = int(task.time_remaining)

        # Format based on duration
        if remaining < 60:
            return Text(f"{remaining}s", style="progress.remaining")
        elif remaining < 3600:
            minutes = remaining // 60
            seconds = remaining % 60
            return Text(f"{minutes}m {seconds}s", style="progress.remaining")
        else:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return Text(f"{hours}h {minutes}m", style="progress.remaining")


class CompactTimeElapsedColumn(ProgressColumn):
    """Displays elapsed time in compact format."""

    def render(self, task: Task) -> Text:
        """
        Render the elapsed time column.

        Args:
            task: Rich progress task

        Returns:
            Formatted text with elapsed time
        """
        elapsed = int(task.elapsed)

        # Format based on duration
        if elapsed < 60:
            return Text(f"{elapsed}s", style="progress.elapsed")
        elif elapsed < 3600:
            minutes = elapsed // 60
            seconds = elapsed % 60
            return Text(f"{minutes}m {seconds}s", style="progress.elapsed")
        else:
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            return Text(f"{hours}h {minutes}m", style="progress.elapsed")
