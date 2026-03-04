# ABOUTME: HTTP API client for Chronicon
# ABOUTME: Provides rate-limited, retry-enabled HTTP client for Discourse API

"""HTTP client for Discourse API with rate limiting and retry logic."""

import json
import time
import urllib.error
import urllib.request

from ..utils.logger import get_logger

log = get_logger(__name__)


class DiscourseAPIClient:
    """HTTP client for Discourse API with rate limiting."""

    def __init__(
        self,
        base_url: str,
        rate_limit: float = 0.5,
        timeout: int = 15,
        max_retries: int = 5,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the Discourse forum (e.g., https://meta.discourse.org)
            rate_limit: Minimum seconds between requests (default 0.5)
            timeout: Request timeout in seconds (default 15)
            max_retries: Maximum number of retry attempts (default 5)
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time = 0

        # Statistics tracking
        self.requests_made = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.retries_attempted = 0
        self.bytes_transferred = 0
        self.start_time = time.time()

    def get(self, path: str) -> str:
        """
        Fetch a URL and return the response body as string.

        Args:
            path: API path (e.g., /posts.json)

        Returns:
            Response body as string
        """
        url = f"{self.base_url}{path}"
        return self._fetch_with_retry(url)

    def get_json(self, path: str) -> dict:
        """
        Fetch a URL and return the parsed JSON response.

        Args:
            path: API path (e.g., /posts.json)

        Returns:
            Parsed JSON response as dict
        """
        response_text = self.get(path)
        return json.loads(response_text)

    def _fetch_with_retry(self, url: str) -> str:
        """
        Fetch URL with exponential backoff retry logic.

        Args:
            url: Full URL to fetch

        Returns:
            Response body as string

        Raises:
            urllib.error.URLError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                # Track retry attempts (first attempt is not a retry)
                if attempt > 0:
                    self.retries_attempted += 1

                # Rate limiting
                elapsed = time.time() - self.last_request_time
                if elapsed < self.rate_limit:
                    time.sleep(self.rate_limit - elapsed)

                # Make request
                self.requests_made += 1
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Chronicon/1.0.0")

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    self.last_request_time = time.time()
                    response_data = response.read()
                    self.bytes_transferred += len(response_data)
                    self.requests_successful += 1
                    return response_data.decode("utf-8")

            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limit exceeded
                    backoff = self._exponential_backoff(attempt)
                    log.warning(
                        f"Rate limited, waiting {backoff}s before retry "
                        f"{attempt + 1}/{self.max_retries}"
                    )
                    time.sleep(backoff)
                elif e.code >= 500:  # Server error
                    backoff = self._exponential_backoff(attempt)
                    log.warning(
                        f"Server error {e.code}, retrying in {backoff}s "
                        f"({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(backoff)
                else:
                    # Client error, don't retry
                    self.requests_failed += 1
                    raise

            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    backoff = self._exponential_backoff(attempt)
                    log.warning(
                        f"Network error, retrying in {backoff}s "
                        f"({attempt + 1}/{self.max_retries}): {e}"
                    )
                    time.sleep(backoff)
                else:
                    self.requests_failed += 1
                    raise

        self.requests_failed += 1
        raise urllib.error.URLError(
            f"Failed to fetch {url} after {self.max_retries} attempts"
        )

    def _exponential_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = 3
        return base_delay * (2**attempt)

    def get_stats(self) -> dict:
        """
        Get current request statistics.

        Returns:
            Dictionary with request statistics including:
            - requests_made: Total API requests initiated
            - requests_successful: Successful responses
            - requests_failed: Failed responses
            - retries_attempted: Number of retry attempts
            - bytes_transferred: Total bytes downloaded
            - elapsed_time: Seconds since client initialization
            - request_rate: Requests per second
        """
        elapsed = time.time() - self.start_time
        request_rate = self.requests_made / elapsed if elapsed > 0 else 0

        return {
            "requests_made": self.requests_made,
            "requests_successful": self.requests_successful,
            "requests_failed": self.requests_failed,
            "retries_attempted": self.retries_attempted,
            "bytes_transferred": self.bytes_transferred,
            "elapsed_time": elapsed,
            "request_rate": request_rate,
        }

    def reset_stats(self) -> None:
        """Reset all statistics counters."""
        self.requests_made = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.retries_attempted = 0
        self.bytes_transferred = 0
        self.start_time = time.time()
