# ABOUTME: Unit tests for GitManager
# ABOUTME: Tests git integration functionality for watch mode

"""Tests for git integration in watch mode."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from chronicon.watch.git_manager import GitManager


def test_git_manager_initialization():
    """Test GitManager initialization."""
    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=True,
        auto_commit=True,
        push_to_remote=False,
        remote_name="origin",
        branch="main",
        commit_message_template="test: {new_posts} new posts",
    )

    assert manager.repo_path == Path("/tmp/test")
    assert manager.auto_commit is True
    assert manager.push_to_remote is False
    assert manager.remote_name == "origin"
    assert manager.branch == "main"
    assert "test:" in manager.commit_message_template


def test_git_manager_disabled_if_git_not_available():
    """Test that GitManager disables itself if git is not available."""
    with patch.object(GitManager, "is_git_available", return_value=False):
        manager = GitManager(
            repo_path=Path("/tmp/test"),
            enabled=True,
        )

        assert manager.enabled is False


def test_git_manager_disabled_if_not_git_repo():
    """Test that GitManager disables itself if path is not a git repo."""
    with (
        patch.object(GitManager, "is_git_available", return_value=True),
        patch.object(GitManager, "is_git_repo", return_value=False),
    ):
        manager = GitManager(
            repo_path=Path("/tmp/test"),
            enabled=True,
        )

        assert manager.enabled is False


@patch("subprocess.run")
def test_is_git_available_true(mock_run):
    """Test is_git_available when git is available."""
    mock_run.return_value = Mock(returncode=0)

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.is_git_available()

    assert result is True
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_is_git_available_false(mock_run):
    """Test is_git_available when git is not available."""
    mock_run.side_effect = FileNotFoundError()

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.is_git_available()

    assert result is False


@patch("subprocess.run")
def test_is_git_repo_true(mock_run):
    """Test is_git_repo when path is a git repo."""
    mock_run.return_value = Mock(returncode=0)

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.is_git_repo()

    assert result is True


@patch("subprocess.run")
def test_is_git_repo_false(mock_run):
    """Test is_git_repo when path is not a git repo."""
    mock_run.return_value = Mock(returncode=1)

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.is_git_repo()

    assert result is False


@patch("subprocess.run")
def test_has_uncommitted_changes_true(mock_run):
    """Test has_uncommitted_changes when there are changes."""
    mock_run.return_value = Mock(returncode=0, stdout="M file.txt\n")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.has_uncommitted_changes()

    assert result is True


@patch("subprocess.run")
def test_has_uncommitted_changes_false(mock_run):
    """Test has_uncommitted_changes when there are no changes."""
    mock_run.return_value = Mock(returncode=0, stdout="")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.has_uncommitted_changes()

    assert result is False


@patch("subprocess.run")
def test_get_changed_files(mock_run):
    """Test get_changed_files."""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="M  html/index.html\nA  markdown/topic.md\nD  github/README.md\n",
    )

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    changed = manager.get_changed_files(formats=["html", "markdown", "github"])

    assert len(changed) == 3
    assert Path("html/index.html") in changed
    assert Path("markdown/topic.md") in changed
    assert Path("github/README.md") in changed


@patch("subprocess.run")
def test_get_changed_files_filters_by_format(mock_run):
    """Test that get_changed_files filters by format."""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="M  html/index.html\nM  other/file.txt\nM  markdown/topic.md\n",
    )

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    changed = manager.get_changed_files(formats=["html", "markdown"])

    # Should only include html and markdown, not other
    assert len(changed) == 2
    assert Path("html/index.html") in changed
    assert Path("markdown/topic.md") in changed
    assert Path("other/file.txt") not in changed


@patch("subprocess.run")
@patch("pathlib.Path.exists")
def test_stage_files(mock_exists, mock_run):
    """Test stage_files."""
    # Mock directory exists check
    mock_exists.return_value = True

    # Mock git add command
    add_result = Mock(returncode=0)
    # Mock git diff command to return staged files
    diff_result = Mock(returncode=0, stdout="html/index.html\nhtml/topic.html\n")

    mock_run.side_effect = [add_result, diff_result]

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    count = manager.stage_files(formats=["html"])

    assert count == 2


@patch("subprocess.run")
def test_create_commit_success(mock_run):
    """Test create_commit with success."""
    mock_run.return_value = Mock(returncode=0)

    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=False,
        commit_message_template="chore: {new_posts} new, {modified_posts} modified",
    )

    result = manager.create_commit(new_posts=5, modified_posts=2, affected_topics=3)

    assert result is True
    # Verify commit message was formatted
    call_args = mock_run.call_args
    assert "5 new, 2 modified" in str(call_args)


@patch("subprocess.run")
def test_create_commit_nothing_to_commit(mock_run):
    """Test create_commit when there's nothing to commit."""
    mock_run.return_value = Mock(returncode=1, stdout="nothing to commit")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.create_commit(new_posts=0, modified_posts=0, affected_topics=0)

    # Should return True (success) even though no commit was created
    assert result is True


@patch("subprocess.run")
def test_create_commit_failure(mock_run):
    """Test create_commit with failure."""
    mock_run.return_value = Mock(returncode=1, stdout="error", stderr="commit failed")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.create_commit(new_posts=5, modified_posts=2, affected_topics=3)

    assert result is False


@patch("subprocess.run")
def test_push_to_remote_success(mock_run):
    """Test push_to_remote_branch with success."""
    mock_run.return_value = Mock(returncode=0)

    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=False,
        remote_name="origin",
        branch="main",
    )

    result = manager.push_to_remote_branch()

    assert result is True
    # Verify push command
    call_args = mock_run.call_args
    assert "push" in str(call_args)
    assert "origin" in str(call_args)
    assert "main" in str(call_args)


@patch("subprocess.run")
def test_push_to_remote_failure(mock_run):
    """Test push_to_remote_branch with failure."""
    mock_run.return_value = Mock(returncode=1, stderr="push failed")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.push_to_remote_branch()

    assert result is False


@patch("subprocess.run")
def test_push_to_remote_timeout(mock_run):
    """Test push_to_remote_branch with timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git push", timeout=120)

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    result = manager.push_to_remote_branch()

    assert result is False


@patch("subprocess.run")
def test_commit_and_push_no_changes(mock_run):
    """Test commit_and_push when there are no changes."""
    # Mock has_uncommitted_changes to return False
    mock_run.return_value = Mock(returncode=0, stdout="")

    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=True,
        auto_commit=True,
    )

    result = manager.commit_and_push(
        formats=["html"],
        new_posts=0,
        modified_posts=0,
        affected_topics=0,
    )

    # Should succeed with no operations
    assert result is True


@patch("subprocess.run")
def test_commit_and_push_disabled(mock_run):
    """Test commit_and_push when git is disabled."""
    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=False,
    )

    result = manager.commit_and_push(
        formats=["html"],
        new_posts=5,
        modified_posts=2,
        affected_topics=3,
    )

    # Should succeed without doing anything
    assert result is True
    # Should not have called git
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_get_current_branch(mock_run):
    """Test get_current_branch."""
    mock_run.return_value = Mock(returncode=0, stdout="main\n")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    branch = manager.get_current_branch()

    assert branch == "main"


@patch("subprocess.run")
def test_get_remote_url(mock_run):
    """Test get_remote_url."""
    mock_run.return_value = Mock(returncode=0, stdout="git@github.com:user/repo.git\n")

    manager = GitManager(repo_path=Path("/tmp/test"), enabled=False)
    url = manager.get_remote_url()

    assert url == "git@github.com:user/repo.git"


@patch("subprocess.run")
def test_get_status_info(mock_run):
    """Test get_status_info."""

    # Mock responses for various git commands
    def mock_run_side_effect(*args, **kwargs):
        cmd = args[0]
        if "rev-parse" in cmd:
            return Mock(returncode=0)
        elif "branch" in cmd:
            return Mock(returncode=0, stdout="main\n")
        elif "remote get-url" in cmd:
            return Mock(returncode=0, stdout="git@github.com:user/repo.git\n")
        elif "status --porcelain" in cmd:
            return Mock(returncode=0, stdout="")
        return Mock(returncode=0)

    mock_run.side_effect = mock_run_side_effect

    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=True,
        auto_commit=True,
        push_to_remote=True,
    )

    status = manager.get_status_info()

    assert status["enabled"] is True
    assert status["auto_commit"] is True
    assert status["push_to_remote"] is True
    assert "current_branch" in status
    assert "remote_url" in status
    assert "has_changes" in status


def test_commit_message_template_variables():
    """Test that commit message template supports all variables."""
    manager = GitManager(
        repo_path=Path("/tmp/test"),
        enabled=False,
        commit_message_template=(
            "Update: {new_posts} new, {modified_posts} modified, "
            "{topics} topics at {timestamp}"
        ),
    )

    # Test formatting
    message = manager.commit_message_template.format(
        new_posts=5,
        modified_posts=2,
        topics=3,
        timestamp="2025-11-12T10:00:00",
    )

    assert "5 new" in message
    assert "2 modified" in message
    assert "3 topics" in message
    assert "2025-11-12T10:00:00" in message
