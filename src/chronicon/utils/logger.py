# ABOUTME: Logging setup for Chronicon
# ABOUTME: Configures rich-enhanced logging for the application

"""Logging setup with rich formatting."""

import logging

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(debug: bool = False) -> None:
    """
    Set up logging with rich formatting.

    Args:
        debug: If True, set log level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
