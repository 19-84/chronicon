# ABOUTME: Status tracking for watch mode daemon
# ABOUTME: Manages status file, metrics, and cycle results for monitoring

"""Status tracking and metrics for watch mode."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WatchCycleResult:
    """Result from a single watch cycle."""

    timestamp: str
    success: bool
    new_posts: int
    modified_posts: int
    affected_topics: int
    duration_seconds: float
    error_message: str | None = None


@dataclass
class WatchStatus:
    """Current status of the watch daemon."""

    started_at: str
    last_check: str | None
    next_check: str | None
    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    consecutive_errors: int
    total_new_posts: int
    total_modified_posts: int
    total_affected_topics: int
    uptime_seconds: float
    is_running: bool
    pid: int | None
    last_error: str | None = None
    recent_cycles: list[WatchCycleResult] | None = None

    def __post_init__(self):
        """Initialize recent_cycles list if None."""
        if self.recent_cycles is None:
            self.recent_cycles = []

    @classmethod
    def load(cls, status_file: Path) -> Optional["WatchStatus"]:
        """
        Load status from file.

        Args:
            status_file: Path to status JSON file

        Returns:
            WatchStatus instance or None if file doesn't exist
        """
        if not status_file.exists():
            return None

        try:
            with open(status_file) as f:
                data = json.load(f)

            # Convert recent_cycles dicts back to WatchCycleResult objects
            if "recent_cycles" in data and data["recent_cycles"]:
                data["recent_cycles"] = [
                    WatchCycleResult(**cycle) for cycle in data["recent_cycles"]
                ]

            return cls(**data)
        except Exception:
            # If status file is corrupt, return None
            return None

    def save(self, status_file: Path) -> None:
        """
        Save status to file.

        Args:
            status_file: Path to status JSON file
        """
        # Convert to dict
        data = asdict(self)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically (write to temp file, then rename)
        temp_file = status_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            temp_file.rename(status_file)
        except Exception:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise

    def record_cycle(self, result: WatchCycleResult) -> None:
        """
        Record results from a watch cycle.

        Args:
            result: Cycle result to record
        """
        self.total_cycles += 1
        self.last_check = result.timestamp

        if result.success:
            self.successful_cycles += 1
            self.consecutive_errors = 0
            self.last_error = None

            # Update totals
            self.total_new_posts += result.new_posts
            self.total_modified_posts += result.modified_posts
            self.total_affected_topics += result.affected_topics
        else:
            self.failed_cycles += 1
            self.consecutive_errors += 1
            self.last_error = result.error_message

        # Keep only last 50 cycles
        if self.recent_cycles is None:
            self.recent_cycles = []
        self.recent_cycles.append(result)
        if len(self.recent_cycles) > 50:
            self.recent_cycles = self.recent_cycles[-50:]

        # Update uptime
        start_dt = datetime.fromisoformat(self.started_at)
        now_dt = datetime.now()
        self.uptime_seconds = (now_dt - start_dt).total_seconds()

    @classmethod
    def create_initial(cls, pid: int) -> "WatchStatus":
        """
        Create initial status for a new daemon.

        Args:
            pid: Process ID of the daemon

        Returns:
            New WatchStatus instance
        """
        now = datetime.now().isoformat()
        return cls(
            started_at=now,
            last_check=None,
            next_check=None,
            total_cycles=0,
            successful_cycles=0,
            failed_cycles=0,
            consecutive_errors=0,
            total_new_posts=0,
            total_modified_posts=0,
            total_affected_topics=0,
            uptime_seconds=0.0,
            is_running=True,
            pid=pid,
            recent_cycles=[],
        )
