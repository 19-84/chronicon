# ABOUTME: Concurrency utilities for Chronicon
# ABOUTME: Manages concurrent operations with rate limiting and progress tracking

"""Manage concurrent operations with rate limiting."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from rich.progress import Progress

from .logger import get_logger

log = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result from concurrent processing operation."""

    successful: int
    failed: int
    errors: list[tuple[Any, Exception]]
    results: list[Any]


class ConcurrentProcessor:
    """Manage concurrent operations with rate limiting."""

    def __init__(self, max_workers: int = 8, rate_limit: float = 0.5):
        """
        Initialize concurrent processor.

        Args:
            max_workers: Maximum number of concurrent workers
            rate_limit: Minimum seconds between operations
        """
        self.max_workers = max_workers
        self.rate_limit = rate_limit

    def process_topics(
        self, topics: list[Any], processor: Callable[[Any], None]
    ) -> ProcessingResult:
        """
        Process topics concurrently with error aggregation.

        Args:
            topics: List of topics to process
            processor: Function to process each topic

        Returns:
            ProcessingResult with statistics and errors
        """
        return self.process_items(
            topics, processor, description="Processing topics", rate_limited=True
        )

    def process_items(
        self,
        items: list[Any],
        processor: Callable[[Any], Any],
        description: str = "Processing items",
        rate_limited: bool = True,
    ) -> ProcessingResult:
        """
        Process items concurrently with progress tracking and error handling.

        Args:
            items: List of items to process
            processor: Function to process each item
            description: Description for progress bar
            rate_limited: Whether to apply rate limiting

        Returns:
            ProcessingResult with statistics and any errors
        """
        if not items:
            log.info(f"{description}: No items to process")
            return ProcessingResult(successful=0, failed=0, errors=[], results=[])

        log.info(f"{description}: {len(items)} items")

        errors = []
        results = []

        with Progress() as progress:
            task = progress.add_task(description, total=len(items))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                if rate_limited:
                    futures = {
                        executor.submit(self._rate_limited_call, processor, item): item
                        for item in items
                    }
                else:
                    futures = {executor.submit(processor, item): item for item in items}

                # Process results as they complete
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        log.error(f"Error processing {item}: {e}")
                        errors.append((item, e))
                    progress.update(task, advance=1)

        result_obj = ProcessingResult(
            successful=len(results),
            failed=len(errors),
            errors=errors,
            results=results,
        )

        log.info(
            f"{description} complete: {result_obj.successful} successful, "
            f"{result_obj.failed} failed"
        )

        return result_obj

    def download_assets(
        self, urls: list[str], downloader: Callable[[str], Any]
    ) -> ProcessingResult:
        """
        Download assets concurrently with higher parallelism.

        Args:
            urls: List of URLs to download
            downloader: Function to download each URL

        Returns:
            ProcessingResult with download statistics
        """
        if not urls:
            log.info("Download assets: No URLs to download")
            return ProcessingResult(successful=0, failed=0, errors=[], results=[])

        log.info(f"Downloading {len(urls)} assets...")

        errors = []
        results = []

        with Progress() as progress:
            task = progress.add_task("Downloading assets", total=len(urls))

            # Higher concurrency for I/O-bound downloads
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(downloader, url): url for url in urls}

                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        log.error(f"Failed to download {url}: {e}")
                        errors.append((url, e))
                    progress.update(task, advance=1)

        result_obj = ProcessingResult(
            successful=len(results),
            failed=len(errors),
            errors=errors,
            results=results,
        )

        log.info(
            f"Asset download complete: {result_obj.successful} successful, "
            f"{result_obj.failed} failed"
        )

        return result_obj

    def batch_process(
        self,
        items: list[Any],
        processor: Callable[[Any], Any],
        batch_size: int = 10,
        description: str = "Batch processing",
    ) -> ProcessingResult:
        """
        Process items in batches to limit concurrent operations.

        Args:
            items: List of items to process
            processor: Function to process each item
            batch_size: Number of items to process per batch
            description: Description for logging

        Returns:
            ProcessingResult aggregated across all batches
        """
        if not items:
            log.info(f"{description}: No items to process")
            return ProcessingResult(successful=0, failed=0, errors=[], results=[])

        total_batches = (len(items) + batch_size - 1) // batch_size
        log.info(
            f"{description}: Processing {len(items)} items in {total_batches} batches"
        )

        all_results = []
        all_errors = []

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(items))
            batch = items[start_idx:end_idx]

            log.info(
                f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} items)"
            )

            result = self.process_items(
                batch,
                processor,
                description=f"Batch {batch_num + 1}/{total_batches}",
                rate_limited=True,
            )

            all_results.extend(result.results)
            all_errors.extend(result.errors)

        final_result = ProcessingResult(
            successful=len(all_results),
            failed=len(all_errors),
            errors=all_errors,
            results=all_results,
        )

        log.info(
            f"{description} complete: {final_result.successful} successful, "
            f"{final_result.failed} failed"
        )

        return final_result

    def _rate_limited_call(self, func: Callable, *args, **kwargs):
        """Execute function with rate limiting."""
        time.sleep(self.rate_limit)
        return func(*args, **kwargs)
