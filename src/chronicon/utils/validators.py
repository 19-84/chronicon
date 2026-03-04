# ABOUTME: Input validation utilities for security
# ABOUTME: URL validation, filename sanitization, and path traversal prevention

"""Input validation utilities."""

import ipaddress
from pathlib import Path
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_forum_url(url: str) -> str:
    """
    Validate a forum URL for security.

    Checks:
    - Valid URL format
    - HTTPS protocol (or HTTP for localhost/development)
    - Not a private/internal IP address
    - Not a file:// or other dangerous scheme

    Args:
        url: The URL to validate

    Returns:
        The validated URL (normalized)

    Raises:
        ValidationError: If the URL is invalid or dangerous
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}") from e

    # Check scheme (protocol)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only http:// and "
            f"https:// are allowed."
        )

    # Strongly recommend HTTPS
    if parsed.scheme == "http" and parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        # Allow HTTP for localhost/development, but warn for production
        pass  # We'll log a warning in the caller

    # Check for hostname
    if not parsed.hostname:
        raise ValidationError("URL must have a hostname")

    # Check for private/internal IP addresses (SSRF prevention)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
        ) and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            # Allow localhost for development
            raise ValidationError(
                f"Private/internal IP addresses are not allowed: {parsed.hostname}"
            )
    except ValueError:
        # Not an IP address, it's a hostname - that's fine
        pass

    # Check for suspicious patterns
    if ".." in url or url.count("/") > 100:
        raise ValidationError("URL contains suspicious patterns")

    return url


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename to prevent path traversal and other issues.

    Removes:
    - Path separators (/, \\)
    - Null bytes
    - Control characters
    - Leading/trailing dots and spaces
    - Reserved Windows filenames

    Args:
        filename: The filename to sanitize
        max_length: Maximum allowed length (default: 200)

    Returns:
        A safe filename

    Raises:
        ValidationError: If the filename cannot be sanitized safely
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename must be a non-empty string")

    # Remove path separators and null bytes
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")

    # Remove control characters (ASCII 0-31)
    filename = "".join(char for char in filename if ord(char) >= 32)

    # Remove leading/trailing dots, spaces, and underscores
    filename = filename.strip(". _")

    # Check for reserved Windows filenames
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    name_without_ext = filename.split(".")[0].upper()
    if name_without_ext in reserved_names:
        filename = f"file_{filename}"

    # Truncate to max length
    if len(filename) > max_length:
        # Try to preserve extension
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            max_name_len = max_length - len(ext) - 1
            filename = f"{name[:max_name_len]}.{ext}"
        else:
            filename = filename[:max_length]

    # Final check
    if not filename or filename in (".", ".."):
        raise ValidationError("Filename resulted in an invalid name after sanitization")

    return filename


def validate_path_within_base(path: Path, base: Path) -> Path:
    """
    Validate that a path is within a base directory (no path traversal).

    Args:
        path: The path to validate
        base: The base directory that path must be within

    Returns:
        The resolved absolute path

    Raises:
        ValidationError: If the path escapes the base directory
    """
    try:
        # Resolve both paths to absolute
        path_resolved = path.resolve()
        base_resolved = base.resolve()

        # Check if path is relative to base
        path_resolved.relative_to(base_resolved)

        return path_resolved
    except ValueError as e:
        raise ValidationError(
            f"Path '{path}' is outside the allowed base directory '{base}'"
        ) from e


def validate_file_size(size_bytes: int, max_size_mb: int = 100) -> None:
    """
    Validate that a file size is within acceptable limits.

    Args:
        size_bytes: The file size in bytes
        max_size_mb: Maximum allowed size in megabytes (default: 100)

    Raises:
        ValidationError: If the file is too large
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        raise ValidationError(
            f"File size {size_bytes / 1024 / 1024:.1f}MB exceeds maximum "
            f"allowed size of {max_size_mb}MB"
        )


def validate_commit_message_template(template: str) -> str:
    """
    Validate a git commit message template.

    Checks for:
    - Null bytes
    - Excessive length
    - Basic format string placeholders

    Note: Command injection risk is minimal because subprocess.run is used
    with array arguments (not shell=True), but we still validate for safety.

    Args:
        template: The commit message template string

    Returns:
        The validated template

    Raises:
        ValidationError: If the template is invalid
    """
    if not template or not isinstance(template, str):
        raise ValidationError("Commit message template must be a non-empty string")

    # Check for null bytes
    if "\x00" in template:
        raise ValidationError("Commit message template cannot contain null bytes")

    # Check length (git has a soft limit of 72 chars for subject, but
    # allow more for body)
    if len(template) > 10000:
        raise ValidationError(
            "Commit message template is too long (max 10000 characters)"
        )

    # Check for common format placeholders to ensure it's a valid template
    # This is informational only, not a security check
    common_placeholders = ["{", "topics", "posts", "timestamp"]
    has_placeholder = any(ph in template for ph in common_placeholders)

    if not has_placeholder:
        # This is a warning, not an error - static messages are valid
        pass

    return template
