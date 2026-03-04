# ABOUTME: Unit tests for WatchDaemon
# ABOUTME: Tests daemon functionality like PID/lock management and basic operations

"""Tests for watch daemon."""

import os
from unittest.mock import patch

import pytest

from chronicon.config import Config
from chronicon.watch.daemon import WatchDaemon


@pytest.fixture
def temp_archive(tmp_path):
    """Create a temporary archive directory with database."""
    archive_dir = tmp_path / "archives"
    archive_dir.mkdir()

    # Create a minimal database file (just a file, not a real SQLite DB)
    db_file = archive_dir / "archive.db"
    db_file.touch()

    return archive_dir


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Config.defaults()
    return config


def test_daemon_initialization(mock_config, temp_archive):
    """Test WatchDaemon initialization."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=["html", "markdown"],
        daemon_mode=False,
    )

    assert daemon.output_dir == temp_archive
    assert daemon.config == mock_config
    assert daemon.formats == ["html", "markdown"]
    assert daemon.daemon_mode is False
    assert daemon.running is False
    assert daemon.status is None


def test_daemon_file_paths(mock_config, temp_archive):
    """Test that daemon creates correct file paths."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    assert daemon.pid_file == temp_archive / ".chronicon-watch.pid"
    assert daemon.lock_file == temp_archive / ".chronicon-watch.lock"
    assert daemon.status_file == temp_archive / ".chronicon-watch-status.json"
    assert daemon.log_file == temp_archive / "chronicon-watch.log"


def test_create_and_remove_pid_file(mock_config, temp_archive):
    """Test PID file creation and removal."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    # Create PID file
    daemon._create_pid_file()
    assert daemon.pid_file.exists()
    assert daemon.pid_file.read_text() == str(os.getpid())

    # Remove PID file
    daemon._remove_pid_file()
    assert not daemon.pid_file.exists()


def test_create_and_remove_lock_file(mock_config, temp_archive):
    """Test lock file creation and removal."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    # Create lock file
    daemon._create_lock_file()
    assert daemon.lock_file.exists()
    assert daemon.lock_file.read_text() == str(os.getpid())

    # Remove lock file
    daemon._remove_lock_file()
    assert not daemon.lock_file.exists()


def test_check_lock_file_no_file(mock_config, temp_archive):
    """Test check_lock_file when no file exists."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    result = daemon._check_lock_file()
    assert result is False


def test_check_lock_file_with_running_process(mock_config, temp_archive):
    """Test check_lock_file with current process PID."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    # Create lock file with current PID
    daemon._create_lock_file()

    # Check should return True (process is running)
    result = daemon._check_lock_file()
    assert result is True

    # Clean up
    daemon._remove_lock_file()


def test_check_lock_file_with_stale_pid(mock_config, temp_archive):
    """Test check_lock_file with non-existent PID."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    # Create lock file with non-existent PID
    daemon.lock_file.write_text("999999")

    # Check should return False and remove stale lock file
    result = daemon._check_lock_file()
    assert result is False
    assert not daemon.lock_file.exists()


def test_get_status_no_file(mock_config, temp_archive):
    """Test get_status when no status file exists."""
    status = WatchDaemon.get_status(temp_archive)
    assert status is None


def test_get_status_with_file(mock_config, temp_archive):
    """Test get_status when status file exists."""
    from chronicon.watch.status import WatchStatus

    # Create a status file
    status = WatchStatus.create_initial(pid=12345)
    status_file = temp_archive / ".chronicon-watch-status.json"
    status.save(status_file)

    # Get status
    loaded = WatchDaemon.get_status(temp_archive)
    assert loaded is not None
    assert loaded.pid == 12345


@patch("os.kill")
@patch("time.sleep")
def test_stop_daemon_success(mock_sleep, mock_kill, mock_config, temp_archive):
    """Test stopping a running daemon."""
    # Create PID file
    pid_file = temp_archive / ".chronicon-watch.pid"
    pid_file.write_text("12345")

    # First call checks if process exists (signal 0), second sends SIGTERM,
    # subsequent calls check if process exited (should raise OSError when gone)
    def kill_side_effect(pid, sig):
        if kill_side_effect.call_count == 0:
            kill_side_effect.call_count += 1
            return  # Process exists (check with signal 0)
        elif kill_side_effect.call_count == 1:
            kill_side_effect.call_count += 1
            return  # SIGTERM sent successfully
        else:
            # Process exited
            raise OSError()

    kill_side_effect.call_count = 0
    mock_kill.side_effect = kill_side_effect

    result = WatchDaemon.stop_daemon(temp_archive)
    assert result is True


def test_stop_daemon_no_pid_file(mock_config, temp_archive):
    """Test stopping daemon when no PID file exists."""
    result = WatchDaemon.stop_daemon(temp_archive)
    assert result is False


@patch("os.kill")
def test_stop_daemon_stale_pid(mock_kill, mock_config, temp_archive):
    """Test stopping daemon with stale PID."""
    # Create PID file
    pid_file = temp_archive / ".chronicon-watch.pid"
    pid_file.write_text("12345")

    # Mock kill to raise OSError immediately (process doesn't exist)
    mock_kill.side_effect = OSError()

    result = WatchDaemon.stop_daemon(temp_archive)
    assert result is False
    # PID file should be removed
    assert not pid_file.exists()


def test_signal_handlers_setup(mock_config, temp_archive):
    """Test that signal handlers are set up."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
    )

    # Verify signal handlers are registered
    # Note: We can't easily test the handlers themselves without actually
    # sending signals. But we can verify the daemon has the handler methods
    assert hasattr(daemon, "_handle_shutdown_signal")
    assert hasattr(daemon, "_handle_reload_signal")
    assert callable(daemon._handle_shutdown_signal)
    assert callable(daemon._handle_reload_signal)


def test_daemon_defaults_to_all_formats(mock_config, temp_archive):
    """Test that daemon defaults to all formats if none specified."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=None,
    )

    assert daemon.formats == ["html", "md"]


def test_daemon_can_specify_specific_formats(mock_config, temp_archive):
    """Test that daemon can be configured with specific formats."""
    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=["html"],
    )

    assert daemon.formats == ["html"]


def test_run_update_cycle_calls_export_users_by_username(mock_config, temp_archive):
    """Test that _run_update_cycle calls export_users_by_username."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock, Mock

    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=["html"],
    )

    # Set up mocked database and client
    daemon.db = MagicMock()
    daemon.client = MagicMock()
    daemon.site_url = "https://example.com"
    daemon.git_manager = MagicMock()
    daemon.git_manager.enabled = False

    # Mock config methods
    daemon.config.get_category_filter = Mock(return_value=None)

    # Create a mock UpdateStatistics
    @dataclass
    class FakeStats:
        new_posts: int = 2
        modified_posts: int = 1
        new_topics: int = 1
        affected_topics: int = 2
        affected_usernames: int = 2
        fetch_errors: int = 0
        duration_seconds: float = 1.0

    # Patch UpdateManager to return our mock
    mock_update_manager = MagicMock()
    mock_update_manager.update_archive.return_value = FakeStats()
    mock_update_manager.get_topics_to_regenerate.return_value = {1, 2}
    mock_update_manager.get_affected_usernames.return_value = {"alice", "bob"}

    with (
        patch(
            "chronicon.watch.daemon.UpdateManager",
            return_value=mock_update_manager,
        ),
        patch("chronicon.watch.daemon.HTMLStaticExporter") as mock_html_exporter_cls,
    ):
        mock_html_instance = MagicMock()
        mock_html_exporter_cls.return_value = mock_html_instance

        # Create html dir so the exporter path check passes
        html_dir = temp_archive / "html"
        html_dir.mkdir()

        result = daemon._run_update_cycle()

    assert result.success
    assert result.new_posts == 2
    # Verify export_users_by_username was called
    mock_html_instance.export_users_by_username.assert_called_once_with(
        {"alice", "bob"}
    )


def test_run_update_cycle_skips_users_when_no_changes(mock_config, temp_archive):
    """Test that _run_update_cycle skips user regeneration when there are no changes."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock, Mock

    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=["html"],
    )

    daemon.db = MagicMock()
    daemon.client = MagicMock()
    daemon.site_url = "https://example.com"
    daemon.git_manager = MagicMock()
    daemon.git_manager.enabled = False

    daemon.config.get_category_filter = Mock(return_value=None)

    @dataclass
    class FakeStats:
        new_posts: int = 0
        modified_posts: int = 0
        new_topics: int = 0
        affected_topics: int = 0
        affected_usernames: int = 0
        fetch_errors: int = 0
        duration_seconds: float = 0.5

    mock_update_manager = MagicMock()
    mock_update_manager.update_archive.return_value = FakeStats()
    mock_update_manager.get_topics_to_regenerate.return_value = set()
    mock_update_manager.get_affected_usernames.return_value = set()

    with (
        patch(
            "chronicon.watch.daemon.UpdateManager",
            return_value=mock_update_manager,
        ),
        patch("chronicon.watch.daemon.HTMLStaticExporter") as mock_html_exporter_cls,
    ):
        mock_html_instance = MagicMock()
        mock_html_exporter_cls.return_value = mock_html_instance

        result = daemon._run_update_cycle()

    assert result.success
    # export_users_by_username should NOT be called (no affected topics)
    mock_html_instance.export_users_by_username.assert_not_called()


def test_run_update_cycle_downloads_assets_for_affected_topics(
    mock_config, temp_archive
):
    """Test that _run_update_cycle downloads assets for affected topics."""
    from dataclasses import dataclass
    from datetime import datetime
    from unittest.mock import MagicMock, Mock

    from chronicon.models.post import Post

    daemon = WatchDaemon(
        output_dir=temp_archive,
        config=mock_config,
        formats=["html"],
    )

    # Set up mocked database and client
    daemon.db = MagicMock()
    daemon.client = MagicMock()
    daemon.site_url = "https://example.com"
    daemon.git_manager = MagicMock()
    daemon.git_manager.enabled = False

    # Mock config methods
    daemon.config.get_category_filter = Mock(return_value=None)

    # Create a test post with images
    mock_post = Post(
        id=101,
        topic_id=42,
        user_id=1,
        post_number=1,
        username="testuser",
        raw="test",
        cooked='<img src="https://cdn.example.com/img_690w.webp">',
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    daemon.db.get_topic_posts.return_value = [mock_post]

    @dataclass
    class FakeStats:
        new_posts: int = 2
        modified_posts: int = 1
        new_topics: int = 1
        affected_topics: int = 1
        affected_usernames: int = 1
        fetch_errors: int = 0
        duration_seconds: float = 1.0

    mock_update_manager = MagicMock()
    mock_update_manager.update_archive.return_value = FakeStats()
    mock_update_manager.get_topics_to_regenerate.return_value = {42}
    mock_update_manager.get_affected_usernames.return_value = {"testuser"}

    with (
        patch(
            "chronicon.watch.daemon.UpdateManager",
            return_value=mock_update_manager,
        ),
        patch("chronicon.watch.daemon.HTMLStaticExporter") as mock_html_exporter_cls,
        patch("chronicon.watch.daemon.AssetDownloader") as mock_asset_dl_class,
        patch("chronicon.watch.daemon.HTMLProcessor") as mock_html_proc_class,
    ):
        mock_html_instance = MagicMock()
        mock_html_exporter_cls.return_value = mock_html_instance

        # Setup mock HTML processor
        mock_html_proc = mock_html_proc_class.return_value
        mock_html_proc.extract_image_sets.return_value = {
            "img_base": {
                "all_urls": [
                    "https://cdn.example.com/img_690w.webp",
                    "https://cdn.example.com/img_1380w.webp",
                ],
                "medium": "https://cdn.example.com/img_690w.webp",
                "highest": "https://cdn.example.com/img_1380w.webp",
            }
        }

        # Setup mock asset downloader
        mock_asset_dl = mock_asset_dl_class.return_value

        # Create html dir so the exporter path check passes
        html_dir = temp_archive / "html"
        html_dir.mkdir()

        result = daemon._run_update_cycle()

    assert result.success
    # Verify asset downloader was called with medium and highest
    download_calls = mock_asset_dl.download_image.call_args_list
    downloaded_urls = [call[0][0] for call in download_calls]
    assert "https://cdn.example.com/img_690w.webp" in downloaded_urls
    assert "https://cdn.example.com/img_1380w.webp" in downloaded_urls
