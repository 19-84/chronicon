# ABOUTME: Git integration for watch mode auto-commits
# ABOUTME: Handles automatic commits and pushes with templated commit messages

"""Git integration for automatic commits during watch mode."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

log = get_logger(__name__)


class GitManager:
    """Manages git operations for auto-commit functionality."""

    def __init__(
        self,
        repo_path: Path,
        enabled: bool = False,
        auto_commit: bool = True,
        push_to_remote: bool = False,
        remote_name: str = "origin",
        branch: str = "main",
        commit_message_template: str = (
            "chore: update archive - {new_posts} new, {modified_posts} "
            "modified, {topics} topics"
        ),
    ):
        """
        Initialize git manager.

        Args:
            repo_path: Path to git repository
            enabled: Enable git integration
            auto_commit: Automatically commit changes
            push_to_remote: Push commits to remote
            remote_name: Name of git remote
            branch: Branch name
            commit_message_template: Template for commit messages
        """
        self.repo_path = Path(repo_path)
        self.enabled = enabled
        self.auto_commit = auto_commit
        self.push_to_remote = push_to_remote
        self.remote_name = remote_name
        self.branch = branch
        self.commit_message_template = commit_message_template

        # Check if git is available and repo exists
        if self.enabled:
            if not self.is_git_available():
                log.warning("Git not available, disabling git integration")
                self.enabled = False
            elif not self.is_git_repo():
                log.warning(
                    f"{repo_path} is not a git repository, disabling git integration"
                )
                self.enabled = False
            else:
                log.info(f"Git integration enabled for {repo_path}")
                # Configure git credentials from environment if available
                if self.push_to_remote:
                    self._configure_git_credentials()

    def is_git_available(self) -> bool:
        """
        Check if git is available on the system.

        Returns:
            True if git is available
        """
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return False

    def is_git_repo(self) -> bool:
        """
        Check if repo_path is a git repository.

        Returns:
            True if it's a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                check=False,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _configure_git_credentials(self) -> bool:
        """
        Configure git credentials from environment variables.

        Supports HTTPS token authentication for GitHub, GitLab, Forgejo, etc.
        Uses per-repository credential configuration for security.

        Environment variables:
            GIT_TOKEN: Personal access token
            GIT_USERNAME: Git username
            GIT_REMOTE_URL: Remote repository URL (https://...)

        Returns:
            True if credentials were configured, False otherwise
        """
        import os

        git_token = os.getenv("GIT_TOKEN")
        git_username = os.getenv("GIT_USERNAME")
        git_remote_url = os.getenv("GIT_REMOTE_URL")

        if not git_token:
            log.debug("GIT_TOKEN not set, skipping credential configuration")
            return False

        if not git_username:
            log.warning("GIT_TOKEN set but GIT_USERNAME not set")
            return False

        try:
            # Set the remote URL if provided with embedded credentials
            if git_remote_url:
                if git_remote_url.startswith("https://"):
                    # Insert credentials into URL for this repo
                    # Format: https://username:token@host/path
                    url_parts = git_remote_url.replace("https://", "")
                    authenticated_url = (
                        f"https://{git_username}:{git_token}@{url_parts}"
                    )

                    # Set remote URL with credentials
                    result = subprocess.run(
                        [
                            "git",
                            "remote",
                            "set-url",
                            self.remote_name,
                            authenticated_url,
                        ],
                        cwd=self.repo_path,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )

                    if result.returncode == 0:
                        log.info(f"Configured git credentials for {self.remote_name}")
                        return True
                    else:
                        stderr_msg = (
                            result.stderr.decode() if result.stderr else "unknown error"
                        )
                        log.error(f"Failed to configure git remote: {stderr_msg}")
                        return False
                else:
                    log.warning("GIT_REMOTE_URL must be an HTTPS URL for token auth")
                    return False
            else:
                log.debug("GIT_REMOTE_URL not set, skipping credential configuration")
                return False

        except Exception as e:
            log.error(f"Error configuring git credentials: {e}")
            return False

    def has_uncommitted_changes(self) -> bool:
        """
        Check if there are uncommitted changes.

        Returns:
            True if there are uncommitted changes
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception as e:
            log.error(f"Error checking git status: {e}")
            return False

    def get_changed_files(self, formats: list[str]) -> list[Path]:
        """
        Get list of changed files for specified formats.

        Args:
            formats: List of export formats (html, markdown, github)

        Returns:
            List of changed file paths relative to repo
        """
        changed = []

        try:
            # Get all changed files
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=10,
            )

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                # Parse git status output (format: "XY filename")
                filename = line[3:].strip()

                # Check if file is in one of the export directories
                for fmt in formats:
                    if filename.startswith(f"{fmt}/"):
                        changed.append(Path(filename))
                        break

            return changed

        except Exception as e:
            log.error(f"Error getting changed files: {e}")
            return []

    def stage_files(self, formats: list[str]) -> int:
        """
        Stage changed files for specified formats.

        Args:
            formats: List of export formats

        Returns:
            Number of files staged
        """
        staged_count = 0

        try:
            # Stage each format directory that has changes
            for fmt in formats:
                fmt_dir = self.repo_path / fmt
                if not fmt_dir.exists():
                    continue

                # Add all changes in format directory
                result = subprocess.run(
                    ["git", "add", fmt],
                    cwd=self.repo_path,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    # Count staged files
                    count_result = subprocess.run(
                        ["git", "diff", "--cached", "--name-only", fmt],
                        cwd=self.repo_path,
                        capture_output=True,
                        check=True,
                        text=True,
                        timeout=10,
                    )
                    files = [f for f in count_result.stdout.splitlines() if f.strip()]
                    staged_count += len(files)
                else:
                    log.error(f"Failed to stage {fmt}: {result.stderr}")

            log.info(f"Staged {staged_count} files")
            return staged_count

        except Exception as e:
            log.error(f"Error staging files: {e}")
            return 0

    def create_commit(
        self, new_posts: int, modified_posts: int, affected_topics: int
    ) -> bool:
        """
        Create a commit with templated message.

        Args:
            new_posts: Number of new posts
            modified_posts: Number of modified posts
            affected_topics: Number of affected topics

        Returns:
            True if commit was created successfully
        """
        try:
            # Format commit message
            message = self.commit_message_template.format(
                new_posts=new_posts,
                modified_posts=modified_posts,
                topics=affected_topics,
                timestamp=datetime.now().isoformat(),
            )

            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                check=False,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                log.info(f"Created commit: {message}")
                return True
            else:
                # Check if there's nothing to commit
                if "nothing to commit" in result.stdout.lower():
                    log.debug("No changes to commit")
                    return True
                else:
                    log.error(f"Failed to create commit: {result.stderr}")
                    return False

        except Exception as e:
            log.error(f"Error creating commit: {e}")
            return False

    def push_to_remote_branch(self) -> bool:
        """
        Push commits to remote.

        Returns:
            True if push was successful
        """
        try:
            log.info(f"Pushing to {self.remote_name}/{self.branch}...")

            result = subprocess.run(
                ["git", "push", self.remote_name, self.branch],
                cwd=self.repo_path,
                capture_output=True,
                check=False,
                text=True,
                timeout=120,  # 2 minutes for network operations
            )

            if result.returncode == 0:
                log.info("Successfully pushed to remote")
                return True
            else:
                log.error(f"Failed to push: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            log.error("Push timed out after 2 minutes")
            return False
        except Exception as e:
            log.error(f"Error pushing to remote: {e}")
            return False

    def commit_and_push(
        self,
        formats: list[str],
        new_posts: int,
        modified_posts: int,
        affected_topics: int,
    ) -> bool:
        """
        Stage, commit, and optionally push changes.

        Args:
            formats: List of export formats to commit
            new_posts: Number of new posts
            modified_posts: Number of modified posts
            affected_topics: Number of affected topics

        Returns:
            True if all operations succeeded
        """
        if not self.enabled or not self.auto_commit:
            return True

        # Check if there are any changes
        if not self.has_uncommitted_changes():
            log.debug("No changes to commit")
            return True

        # Stage files
        staged = self.stage_files(formats)
        if staged == 0:
            log.debug("No files staged")
            return True

        # Create commit
        if not self.create_commit(new_posts, modified_posts, affected_topics):
            log.error("Failed to create commit")
            return False

        # Push if enabled
        if self.push_to_remote and not self.push_to_remote_branch():
            log.warning("Failed to push to remote (commit was created locally)")
            return False

        return True

    def get_current_branch(self) -> str | None:
        """
        Get current git branch name.

        Returns:
            Branch name or None if unable to determine
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except Exception as e:
            log.error(f"Error getting current branch: {e}")
            return None

    def get_remote_url(self) -> str | None:
        """
        Get remote URL.

        Returns:
            Remote URL or None if not configured
        """
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", self.remote_name],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def get_status_info(self) -> dict[str, Any]:
        """
        Get git status information.

        Returns:
            Dict with git status info
        """
        return {
            "enabled": self.enabled,
            "is_repo": self.is_git_repo() if self.enabled else False,
            "current_branch": self.get_current_branch() if self.enabled else None,
            "remote_url": self.get_remote_url() if self.enabled else None,
            "has_changes": self.has_uncommitted_changes() if self.enabled else False,
            "auto_commit": self.auto_commit,
            "push_to_remote": self.push_to_remote,
        }
