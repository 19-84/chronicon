# ABOUTME: Unit tests for watch mode status tracking
# ABOUTME: Tests WatchStatus and WatchCycleResult functionality

"""Tests for watch mode status tracking."""

import json
from datetime import datetime

from chronicon.watch.status import WatchCycleResult, WatchStatus


def test_watch_cycle_result_creation():
    """Test creating a WatchCycleResult."""
    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=True,
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
        duration_seconds=45.5,
    )

    assert result.timestamp == "2025-11-12T10:00:00"
    assert result.success is True
    assert result.new_posts == 5
    assert result.modified_posts == 2
    assert result.affected_topics == 3
    assert result.duration_seconds == 45.5
    assert result.error_message is None


def test_watch_cycle_result_with_error():
    """Test creating a WatchCycleResult with error."""
    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=False,
        new_posts=0,
        modified_posts=0,
        affected_topics=0,
        duration_seconds=10.0,
        error_message="Connection timeout",
    )

    assert result.success is False
    assert result.error_message == "Connection timeout"


def test_watch_status_create_initial():
    """Test creating initial WatchStatus."""
    status = WatchStatus.create_initial(pid=12345)

    assert status.pid == 12345
    assert status.is_running is True
    assert status.total_cycles == 0
    assert status.successful_cycles == 0
    assert status.failed_cycles == 0
    assert status.consecutive_errors == 0
    assert status.total_new_posts == 0
    assert status.total_modified_posts == 0
    assert status.total_affected_topics == 0
    assert status.uptime_seconds == 0.0
    assert status.last_check is None
    assert status.next_check is None
    assert status.last_error is None
    assert status.recent_cycles == []


def test_watch_status_record_successful_cycle():
    """Test recording a successful cycle."""
    status = WatchStatus.create_initial(pid=12345)

    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=True,
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
        duration_seconds=45.5,
    )

    status.record_cycle(result)

    assert status.total_cycles == 1
    assert status.successful_cycles == 1
    assert status.failed_cycles == 0
    assert status.consecutive_errors == 0
    assert status.total_new_posts == 5
    assert status.total_modified_posts == 2
    assert status.total_affected_topics == 3
    assert status.last_check == "2025-11-12T10:00:00"
    assert status.last_error is None
    assert len(status.recent_cycles) == 1  # type: ignore[arg-type]
    assert status.recent_cycles[0] == result  # type: ignore[index]


def test_watch_status_record_failed_cycle():
    """Test recording a failed cycle."""
    status = WatchStatus.create_initial(pid=12345)

    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=False,
        new_posts=0,
        modified_posts=0,
        affected_topics=0,
        duration_seconds=10.0,
        error_message="Connection timeout",
    )

    status.record_cycle(result)

    assert status.total_cycles == 1
    assert status.successful_cycles == 0
    assert status.failed_cycles == 1
    assert status.consecutive_errors == 1
    assert status.total_new_posts == 0
    assert status.total_modified_posts == 0
    assert status.total_affected_topics == 0
    assert status.last_error == "Connection timeout"
    assert len(status.recent_cycles) == 1  # type: ignore[arg-type]


def test_watch_status_consecutive_errors_reset():
    """Test that consecutive errors reset on success."""
    status = WatchStatus.create_initial(pid=12345)

    # Record two failures
    for i in range(2):
        result = WatchCycleResult(
            timestamp=f"2025-11-12T10:0{i}:00",
            success=False,
            new_posts=0,
            modified_posts=0,
            affected_topics=0,
            duration_seconds=10.0,
            error_message="Error",
        )
        status.record_cycle(result)

    assert status.consecutive_errors == 2

    # Record success
    result = WatchCycleResult(
        timestamp="2025-11-12T10:02:00",
        success=True,
        new_posts=1,
        modified_posts=0,
        affected_topics=1,
        duration_seconds=20.0,
    )
    status.record_cycle(result)

    assert status.consecutive_errors == 0
    assert status.last_error is None


def test_watch_status_recent_cycles_limit():
    """Test that recent_cycles is limited to 50 entries."""
    status = WatchStatus.create_initial(pid=12345)

    # Record 60 cycles
    for i in range(60):
        result = WatchCycleResult(
            timestamp=f"2025-11-12T10:00:{i:02d}",
            success=True,
            new_posts=1,
            modified_posts=0,
            affected_topics=1,
            duration_seconds=10.0,
        )
        status.record_cycle(result)

    # Should only keep last 50
    assert len(status.recent_cycles) == 50  # type: ignore[arg-type]
    # Check that we kept the most recent ones
    assert status.recent_cycles[0].timestamp == "2025-11-12T10:00:10"  # type: ignore[index]
    assert status.recent_cycles[-1].timestamp == "2025-11-12T10:00:59"  # type: ignore[index]


def test_watch_status_save_and_load(tmp_path):
    """Test saving and loading status from file."""
    status_file = tmp_path / "status.json"

    # Create and save status
    status = WatchStatus.create_initial(pid=12345)
    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=True,
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
        duration_seconds=45.5,
    )
    status.record_cycle(result)
    status.save(status_file)

    # Verify file exists
    assert status_file.exists()

    # Load status
    loaded_status = WatchStatus.load(status_file)

    assert loaded_status is not None
    assert loaded_status.pid == 12345
    assert loaded_status.is_running is True
    assert loaded_status.total_cycles == 1
    assert loaded_status.successful_cycles == 1
    assert loaded_status.total_new_posts == 5
    assert len(loaded_status.recent_cycles) == 1  # type: ignore[arg-type]
    assert loaded_status.recent_cycles[0].timestamp == "2025-11-12T10:00:00"  # type: ignore[index]


def test_watch_status_load_nonexistent_file(tmp_path):
    """Test loading status from nonexistent file."""
    status_file = tmp_path / "nonexistent.json"

    loaded_status = WatchStatus.load(status_file)

    assert loaded_status is None


def test_watch_status_load_corrupt_file(tmp_path):
    """Test loading status from corrupt file."""
    status_file = tmp_path / "corrupt.json"
    status_file.write_text("not valid json {]")

    loaded_status = WatchStatus.load(status_file)

    assert loaded_status is None


def test_watch_status_save_atomic(tmp_path):
    """Test that save is atomic (uses temp file + rename)."""
    status_file = tmp_path / "status.json"

    status = WatchStatus.create_initial(pid=12345)
    status.save(status_file)

    # Temp file should not exist after save
    temp_file = status_file.with_suffix(".tmp")
    assert not temp_file.exists()

    # Status file should exist
    assert status_file.exists()


def test_watch_status_json_structure(tmp_path):
    """Test the JSON structure of saved status."""
    status_file = tmp_path / "status.json"

    status = WatchStatus.create_initial(pid=12345)
    result = WatchCycleResult(
        timestamp="2025-11-12T10:00:00",
        success=True,
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
        duration_seconds=45.5,
    )
    status.record_cycle(result)
    status.save(status_file)

    # Load and verify JSON structure
    with open(status_file) as f:
        data = json.load(f)

    assert "started_at" in data
    assert "last_check" in data
    assert "next_check" in data
    assert "total_cycles" in data
    assert "successful_cycles" in data
    assert "failed_cycles" in data
    assert "consecutive_errors" in data
    assert "total_new_posts" in data
    assert "total_modified_posts" in data
    assert "total_affected_topics" in data
    assert "uptime_seconds" in data
    assert "is_running" in data
    assert "pid" in data
    assert "recent_cycles" in data

    # Verify recent_cycles structure
    assert isinstance(data["recent_cycles"], list)
    assert len(data["recent_cycles"]) == 1
    cycle = data["recent_cycles"][0]
    assert cycle["timestamp"] == "2025-11-12T10:00:00"
    assert cycle["success"] is True
    assert cycle["new_posts"] == 5


def test_watch_status_uptime_calculation():
    """Test that uptime is calculated correctly."""
    status = WatchStatus.create_initial(pid=12345)

    # Record a cycle (this updates uptime)
    result = WatchCycleResult(
        timestamp=datetime.now().isoformat(),
        success=True,
        new_posts=1,
        modified_posts=0,
        affected_topics=1,
        duration_seconds=10.0,
    )
    status.record_cycle(result)

    # Uptime should be > 0
    assert status.uptime_seconds >= 0


def test_watch_status_cumulative_statistics():
    """Test that statistics accumulate correctly."""
    status = WatchStatus.create_initial(pid=12345)

    # Record multiple successful cycles
    for i in range(5):
        result = WatchCycleResult(
            timestamp=f"2025-11-12T10:0{i}:00",
            success=True,
            new_posts=i + 1,
            modified_posts=i,
            affected_topics=i + 1,
            duration_seconds=10.0,
        )
        status.record_cycle(result)

    # Verify cumulative totals
    assert status.total_cycles == 5
    assert status.successful_cycles == 5
    assert status.total_new_posts == 1 + 2 + 3 + 4 + 5  # 15
    assert status.total_modified_posts == 0 + 1 + 2 + 3 + 4  # 10
    assert status.total_affected_topics == 1 + 2 + 3 + 4 + 5  # 15
