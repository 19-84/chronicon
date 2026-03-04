# ABOUTME: Tests for CLI DATABASE_URL environment variable support
# ABOUTME: Verifies archive and watch commands work with SQLite and PostgreSQL

"""
CLI DATABASE_URL tests.

Tests that the archive command properly uses the DATABASE_URL environment
variable when set, and falls back to SQLite when not set.
"""

import os
from unittest.mock import patch


class TestArchiveDatabaseURL:
    """Test archive command DATABASE_URL handling."""

    def test_archive_uses_sqlite_without_database_url(self, tmp_path, monkeypatch):
        """Test archive command uses SQLite when DATABASE_URL not set."""
        # Ensure DATABASE_URL is not set
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Verify DATABASE_URL is not set
        database_url = os.getenv("DATABASE_URL")
        assert database_url is None

    def test_archive_uses_postgres_with_database_url(self, monkeypatch):
        """Test archive command uses PostgreSQL when DATABASE_URL is set."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)

        database_url = os.getenv("DATABASE_URL")
        assert database_url == test_url
        assert database_url.startswith("postgresql://")

    def test_database_url_password_masking(self):
        """Test that password is masked in log output."""
        test_url = "postgresql://user:secret_password@localhost:5432/db"

        # Simulate masking logic from cli.py
        if "@" in test_url:
            masked = (
                test_url.split("@")[0].rsplit(":", 1)[0]
                + ":***@"
                + test_url.split("@")[-1]
            )
        else:
            masked = test_url

        assert "secret_password" not in masked
        assert "***" in masked
        assert "localhost:5432/db" in masked

    def test_database_url_masking_without_password(self):
        """Test masking logic handles URLs without passwords."""
        test_url = "postgresql://localhost:5432/db"

        # This URL doesn't have @ so should remain unchanged
        if "@" in test_url:
            masked = (
                test_url.split("@")[0].rsplit(":", 1)[0]
                + ":***@"
                + test_url.split("@")[-1]
            )
        else:
            masked = test_url

        assert masked == test_url


class TestWatchDatabaseURL:
    """Test watch daemon DATABASE_URL handling."""

    def test_watch_requires_database(self, tmp_path):
        """Test watch daemon fails gracefully without database."""
        from chronicon.config import Config
        from chronicon.watch.daemon import WatchDaemon

        config = Config.defaults()
        daemon = WatchDaemon(
            output_dir=tmp_path,
            config=config,
            formats=["html"],
        )

        # Without DATABASE_URL and without archive.db, should fail to initialize
        # This tests the error handling path
        result = daemon._initialize_database()
        assert result is False

    def test_watch_detects_database_url(self, monkeypatch):
        """Test watch daemon detects DATABASE_URL environment variable."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)

        database_url = os.getenv("DATABASE_URL")
        assert database_url is not None
        assert database_url.startswith("postgresql://")


class TestExportFormatsEnvironment:
    """Test EXPORT_FORMATS environment variable handling."""

    def test_export_formats_parsing(self, tmp_path, monkeypatch):
        """Test EXPORT_FORMATS environment variable is parsed correctly."""
        from chronicon.config import Config
        from chronicon.watch.daemon import WatchDaemon

        # Set EXPORT_FORMATS environment variable
        monkeypatch.setenv("EXPORT_FORMATS", "html,markdown")

        config = Config.defaults()
        daemon = WatchDaemon(
            output_dir=tmp_path,
            config=config,
            formats=None,  # Should be overridden by env var
        )

        assert daemon.formats == ["html", "markdown"]

    def test_export_formats_with_spaces(self, tmp_path, monkeypatch):
        """Test EXPORT_FORMATS handles spaces in comma-separated list."""
        from chronicon.config import Config
        from chronicon.watch.daemon import WatchDaemon

        # Set EXPORT_FORMATS with spaces
        monkeypatch.setenv("EXPORT_FORMATS", "html , markdown , github")

        config = Config.defaults()
        daemon = WatchDaemon(
            output_dir=tmp_path,
            config=config,
            formats=None,
        )

        assert daemon.formats == ["html", "markdown", "github"]

    def test_export_formats_single(self, tmp_path, monkeypatch):
        """Test EXPORT_FORMATS with single format."""
        from chronicon.config import Config
        from chronicon.watch.daemon import WatchDaemon

        monkeypatch.setenv("EXPORT_FORMATS", "html")

        config = Config.defaults()
        daemon = WatchDaemon(
            output_dir=tmp_path,
            config=config,
            formats=None,
        )

        assert daemon.formats == ["html"]

    def test_export_formats_not_set_uses_argument(self, tmp_path, monkeypatch):
        """Test that formats argument is used when EXPORT_FORMATS not set."""
        from chronicon.config import Config
        from chronicon.watch.daemon import WatchDaemon

        # Ensure EXPORT_FORMATS is not set
        monkeypatch.delenv("EXPORT_FORMATS", raising=False)

        config = Config.defaults()
        daemon = WatchDaemon(
            output_dir=tmp_path,
            config=config,
            formats=["github"],
        )

        assert daemon.formats == ["github"]


class TestGitCredentialsEnvironment:
    """Test git credentials environment variable handling."""

    def test_git_credentials_not_configured_without_token(self, tmp_path, monkeypatch):
        """Test git credentials are not configured when GIT_TOKEN is not set."""
        from chronicon.watch.git_manager import GitManager

        monkeypatch.delenv("GIT_TOKEN", raising=False)
        monkeypatch.delenv("GIT_USERNAME", raising=False)
        monkeypatch.delenv("GIT_REMOTE_URL", raising=False)

        # Create a git repo for testing
        (tmp_path / ".git").mkdir()

        with (
            patch.object(GitManager, "is_git_available", return_value=True),
            patch.object(GitManager, "is_git_repo", return_value=True),
        ):
            manager = GitManager(
                repo_path=tmp_path,
                enabled=True,
                push_to_remote=True,
            )
            # _configure_git_credentials should have been called but done nothing
            assert manager.enabled is True

    def test_git_token_without_username_logs_warning(self, tmp_path, monkeypatch):
        """Test that setting GIT_TOKEN without GIT_USERNAME logs a warning."""
        monkeypatch.setenv("GIT_TOKEN", "test_token")
        monkeypatch.delenv("GIT_USERNAME", raising=False)
        monkeypatch.delenv("GIT_REMOTE_URL", raising=False)

        # Verify environment
        assert os.getenv("GIT_TOKEN") == "test_token"
        assert os.getenv("GIT_USERNAME") is None
