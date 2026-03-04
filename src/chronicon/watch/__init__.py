# ABOUTME: Watch mode module for continuous Discourse forum monitoring
# ABOUTME: Provides daemon, status tracking, and git integration for automated archiving

"""Watch mode for continuous monitoring and updating of Discourse archives."""

from .daemon import WatchDaemon
from .git_manager import GitManager
from .status import WatchCycleResult, WatchStatus

__all__ = ["WatchDaemon", "WatchStatus", "WatchCycleResult", "GitManager"]
