# ABOUTME: Unit tests for health check server
# ABOUTME: Tests HTTP endpoints, server lifecycle, and status reporting

"""Tests for health check server."""

import json
import urllib.error
import urllib.request
from time import sleep

import pytest

from chronicon.watch.health_server import HealthCheckHandler, HealthCheckServer
from chronicon.watch.status import WatchCycleResult, WatchStatus


@pytest.fixture
def status_file(tmp_path):
    """Create a temporary status file path."""
    return tmp_path / "watch_status.json"


@pytest.fixture
def healthy_status(status_file):
    """Create and save a healthy status."""
    status = WatchStatus.create_initial(pid=12345)

    # Record a successful cycle
    result = WatchCycleResult(
        timestamp="2025-11-19T10:00:00",
        success=True,
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
        duration_seconds=45.5,
    )
    status.record_cycle(result)
    status.last_check = "2025-11-19T10:00:00"
    status.next_check = "2025-11-19T11:00:00"

    # Save to file
    status.save(status_file)
    return status


@pytest.fixture
def unhealthy_status(status_file):
    """Create and save an unhealthy status (3+ consecutive errors)."""
    status = WatchStatus.create_initial(pid=12345)

    # Record multiple failed cycles
    for i in range(3):
        result = WatchCycleResult(
            timestamp=f"2025-11-19T10:{i:02d}:00",
            success=False,
            new_posts=0,
            modified_posts=0,
            affected_topics=0,
            duration_seconds=5.0,
            error_message="Connection timeout",
        )
        status.record_cycle(result)

    status.last_check = "2025-11-19T10:02:00"
    status.next_check = "2025-11-19T11:00:00"
    status.last_error = "Connection timeout"

    # Save to file
    status.save(status_file)
    return status


def fetch_json(url: str):
    """Fetch JSON from a URL."""
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())


def fetch_with_status(url: str):
    """Fetch URL and return both status code and data."""
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        # Read the error response body
        return e.code, json.loads(e.read().decode())


# ============================================================================
# Server Lifecycle Tests
# ============================================================================


def test_health_server_start_stop(status_file):
    """Test starting and stopping the health server."""
    server = HealthCheckServer(port=18888, status_file=status_file)

    # Initially not running
    assert not server.is_running()

    # Start server
    server.start()
    sleep(0.1)  # Give server time to start
    assert server.is_running()

    # Stop server
    server.stop()
    assert not server.is_running()


def test_health_server_responds_to_requests(status_file, healthy_status):
    """Test that server responds to HTTP requests."""
    server = HealthCheckServer(port=18889, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        # Test root endpoint
        response = urllib.request.urlopen("http://localhost:18889/")
        assert response.status == 200
        assert b"Chronicon Watch Health Check" in response.read()
    finally:
        server.stop()


# ============================================================================
# Root Endpoint Tests
# ============================================================================


def test_root_endpoint_returns_html(status_file):
    """Test that root endpoint returns HTML documentation."""
    server = HealthCheckServer(port=18890, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        with urllib.request.urlopen("http://localhost:18890/") as response:
            content = response.read().decode()
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/html"
            assert "Chronicon Watch Health Check" in content
            assert "GET /health" in content
            assert "GET /metrics" in content
    finally:
        server.stop()


# ============================================================================
# Health Endpoint Tests
# ============================================================================


def test_health_endpoint_no_status_file(status_file):
    """Test /health endpoint when status file doesn't exist."""
    server = HealthCheckServer(port=18891, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18891/health")

        assert status_code == 503
        assert data["status"] == "initializing"
        assert data["healthy"] is False
        assert "No status file found" in data["message"]
    finally:
        server.stop()


def test_health_endpoint_healthy_status(status_file, healthy_status):
    """Test /health endpoint with healthy status."""
    server = HealthCheckServer(port=18892, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18892/health")

        assert status_code == 200
        assert data["status"] == "healthy"
        assert data["healthy"] is True
        assert data["running"] is True
        assert data["pid"] == 12345
        assert data["consecutive_errors"] == 0
        assert data["last_check"] is not None
    finally:
        server.stop()


def test_health_endpoint_unhealthy_status(status_file, unhealthy_status):
    """Test /health endpoint with unhealthy status (3+ errors)."""
    server = HealthCheckServer(port=18893, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18893/health")

        assert status_code == 503
        assert data["status"] == "unhealthy"
        assert data["healthy"] is False
        assert data["running"] is True
        assert data["consecutive_errors"] == 3
    finally:
        server.stop()


def test_health_endpoint_not_running(status_file):
    """Test /health endpoint when daemon is not running."""
    # Create status with is_running = False
    status = WatchStatus.create_initial(pid=12345)
    status.is_running = False
    status.save(status_file)

    server = HealthCheckServer(port=18894, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18894/health")

        assert status_code == 503
        assert data["healthy"] is False
        assert data["running"] is False
    finally:
        server.stop()


# ============================================================================
# Metrics Endpoint Tests
# ============================================================================


def test_metrics_endpoint_no_status_file(status_file):
    """Test /metrics endpoint when status file doesn't exist."""
    server = HealthCheckServer(port=18895, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18895/metrics")

        assert status_code == 503
        assert "error" in data
        assert "No status file found" in data["error"]
    finally:
        server.stop()


def test_metrics_endpoint_healthy_status(status_file, healthy_status):
    """Test /metrics endpoint with healthy status."""
    server = HealthCheckServer(port=18896, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18896/metrics")

        assert status_code == 200

        # Check status section
        assert "status" in data
        assert data["status"]["running"] is True
        assert data["status"]["pid"] == 12345
        assert "uptime_seconds" in data["status"]
        assert "uptime_hours" in data["status"]

        # Check cycles section
        assert "cycles" in data
        assert data["cycles"]["total"] == 1
        assert data["cycles"]["successful"] == 1
        assert data["cycles"]["failed"] == 0
        assert data["cycles"]["consecutive_errors"] == 0
        assert data["cycles"]["success_rate"] == 100.0

        # Check updates section
        assert "updates" in data
        assert data["updates"]["total_new_posts"] == 5
        assert data["updates"]["total_modified_posts"] == 2
        assert data["updates"]["total_affected_topics"] == 3

        # Check timing section
        assert "timing" in data
        assert data["timing"]["last_check"] is not None
        assert data["timing"]["next_check"] is not None

        # Check recent_cycles
        assert "recent_cycles" in data
        assert len(data["recent_cycles"]) == 1
        assert data["recent_cycles"][0]["success"] is True
        assert data["recent_cycles"][0]["new_posts"] == 5
    finally:
        server.stop()


def test_metrics_endpoint_with_multiple_cycles(status_file):
    """Test /metrics endpoint with multiple cycles."""
    status = WatchStatus.create_initial(pid=12345)

    # Record multiple cycles
    for i in range(15):  # More than 10 to test limiting
        result = WatchCycleResult(
            timestamp=f"2025-11-19T10:{i:02d}:00",
            success=i % 3 != 0,  # Fail every 3rd cycle
            new_posts=i,
            modified_posts=i // 2,
            affected_topics=i // 3,
            duration_seconds=30.0 + i,
            error_message="Test error" if i % 3 == 0 else None,
        )
        status.record_cycle(result)

    status.save(status_file)

    server = HealthCheckServer(port=18897, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18897/metrics")

        assert status_code == 200
        assert data["cycles"]["total"] == 15
        assert data["cycles"]["successful"] == 10
        assert data["cycles"]["failed"] == 5

        # Should only return last 10 cycles
        assert len(data["recent_cycles"]) == 10

        # last_error is optional (only included if status.last_error is set)
        # Don't assert its presence since the last cycle might be successful
    finally:
        server.stop()


# ============================================================================
# 404 Tests
# ============================================================================


def test_unknown_endpoint_returns_404(status_file):
    """Test that unknown endpoints return 404."""
    server = HealthCheckServer(port=18898, status_file=status_file)

    try:
        server.start()
        sleep(0.1)

        status_code, data = fetch_with_status("http://localhost:18898/unknown")

        assert status_code == 404
        assert "error" in data
        assert "Not found" in data["error"]
        assert "/health" in data["message"]
        assert "/metrics" in data["message"]
    finally:
        server.stop()


# ============================================================================
# Handler Tests
# ============================================================================


def test_handler_class_variable_set(status_file):
    """Test that HealthCheckHandler class variable is set correctly."""
    HealthCheckServer(port=18899, status_file=status_file)

    # Class variable should be set after initialization
    assert HealthCheckHandler.status_file_path == status_file
