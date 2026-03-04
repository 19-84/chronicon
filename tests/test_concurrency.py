# ABOUTME: Tests for concurrency utilities
# ABOUTME: Tests ThreadPoolExecutor-based concurrent processing with rate limiting

"""Tests for concurrent processing utilities."""

import time

from chronicon.utils.concurrency import ConcurrentProcessor, ProcessingResult


def test_processing_result_dataclass():
    """Test ProcessingResult dataclass."""
    result = ProcessingResult(
        successful=10,
        failed=2,
        errors=[("item1", Exception("error1")), ("item2", Exception("error2"))],
        results=[1, 2, 3],
    )

    assert result.successful == 10
    assert result.failed == 2
    assert len(result.errors) == 2
    assert len(result.results) == 3


def test_concurrent_processor_init():
    """Test ConcurrentProcessor initialization."""
    processor = ConcurrentProcessor(max_workers=4, rate_limit=0.1)

    assert processor.max_workers == 4
    assert processor.rate_limit == 0.1


def test_process_items_empty_list():
    """Test processing empty list of items."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        return item * 2

    result = processor.process_items([], mock_processor, description="Test")

    assert result.successful == 0
    assert result.failed == 0
    assert len(result.errors) == 0
    assert len(result.results) == 0


def test_process_items_success():
    """Test successful concurrent processing."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        return item * 2

    items = [1, 2, 3, 4, 5]
    result = processor.process_items(
        items, mock_processor, description="Test", rate_limited=False
    )

    assert result.successful == 5
    assert result.failed == 0
    assert len(result.results) == 5
    assert sorted(result.results) == [2, 4, 6, 8, 10]


def test_process_items_with_errors():
    """Test processing with some items failing."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        if item == 3:
            raise ValueError(f"Failed on {item}")
        return item * 2

    items = [1, 2, 3, 4, 5]
    result = processor.process_items(
        items, mock_processor, description="Test", rate_limited=False
    )

    assert result.successful == 4
    assert result.failed == 1
    assert len(result.errors) == 1
    assert result.errors[0][0] == 3  # Failed item
    assert isinstance(result.errors[0][1], ValueError)


def test_process_items_all_fail():
    """Test processing where all items fail."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        raise RuntimeError(f"Failed on {item}")

    items = [1, 2, 3]
    result = processor.process_items(
        items, mock_processor, description="Test", rate_limited=False
    )

    assert result.successful == 0
    assert result.failed == 3
    assert len(result.errors) == 3


def test_process_items_with_rate_limiting():
    """Test processing with rate limiting enabled."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.05)

    call_times = []

    def mock_processor(item):
        call_times.append(time.time())
        return item

    items = [1, 2, 3]
    start_time = time.time()
    result = processor.process_items(
        items, mock_processor, description="Test", rate_limited=True
    )
    total_time = time.time() - start_time

    assert result.successful == 3
    assert result.failed == 0
    # With rate limiting, should take at least rate_limit * num_items
    assert total_time >= 0.05 * 3 * 0.5  # Some slack for test execution


def test_process_topics():
    """Test process_topics convenience method."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(topic):
        return f"processed_{topic}"

    topics = ["topic1", "topic2", "topic3"]
    result = processor.process_topics(topics, mock_processor)  # type: ignore[arg-type]

    assert result.successful == 3
    assert result.failed == 0
    assert "processed_topic1" in result.results


def test_download_assets_empty_list():
    """Test downloading with empty URL list."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_downloader(url):
        return url

    result = processor.download_assets([], mock_downloader)

    assert result.successful == 0
    assert result.failed == 0


def test_download_assets_success():
    """Test successful asset downloads."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_downloader(url):
        return f"downloaded_{url}"

    urls = ["url1", "url2", "url3"]
    result = processor.download_assets(urls, mock_downloader)

    assert result.successful == 3
    assert result.failed == 0
    assert "downloaded_url1" in result.results


def test_download_assets_with_failures():
    """Test asset downloads with some failures."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_downloader(url):
        if url == "bad_url":
            raise ConnectionError(f"Failed to download {url}")
        return f"downloaded_{url}"

    urls = ["url1", "bad_url", "url3"]
    result = processor.download_assets(urls, mock_downloader)

    assert result.successful == 2
    assert result.failed == 1
    assert len(result.errors) == 1
    assert result.errors[0][0] == "bad_url"


def test_batch_process_empty_list():
    """Test batch processing with empty list."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        return item * 2

    result = processor.batch_process(
        [], mock_processor, batch_size=2, description="Test"
    )

    assert result.successful == 0
    assert result.failed == 0


def test_batch_process_single_batch():
    """Test batch processing with items fitting in one batch."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        return item * 2

    items = [1, 2, 3]
    result = processor.batch_process(
        items, mock_processor, batch_size=5, description="Test"
    )

    assert result.successful == 3
    assert result.failed == 0
    assert sorted(result.results) == [2, 4, 6]


def test_batch_process_multiple_batches():
    """Test batch processing with multiple batches."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        return item * 2

    items = [1, 2, 3, 4, 5, 6, 7]
    result = processor.batch_process(
        items, mock_processor, batch_size=3, description="Test"
    )

    assert result.successful == 7
    assert result.failed == 0
    assert sorted(result.results) == [2, 4, 6, 8, 10, 12, 14]


def test_batch_process_with_errors():
    """Test batch processing with errors in different batches."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        if item in [3, 7]:
            raise ValueError(f"Failed on {item}")
        return item * 2

    items = [1, 2, 3, 4, 5, 6, 7, 8]
    result = processor.batch_process(
        items, mock_processor, batch_size=3, description="Test"
    )

    assert result.successful == 6
    assert result.failed == 2
    assert len(result.errors) == 2


def test_rate_limited_call():
    """Test rate limiting function."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.05)

    def mock_func(x):
        return x * 2

    start_time = time.time()
    result = processor._rate_limited_call(mock_func, 5)
    elapsed = time.time() - start_time

    assert result == 10
    assert elapsed >= 0.05  # Should have slept for at least rate_limit


def test_concurrent_processor_with_none_results():
    """Test processing functions that return None."""
    processor = ConcurrentProcessor(max_workers=2, rate_limit=0.01)

    def mock_processor(item):
        # Function that returns None (like many side-effect functions)
        return None

    items = [1, 2, 3]
    result = processor.process_items(
        items, mock_processor, description="Test", rate_limited=False
    )

    assert result.successful == 3
    assert result.failed == 0
    assert len(result.results) == 3
    assert all(r is None for r in result.results)


def test_concurrent_processor_large_batch():
    """Test processing a larger batch of items."""
    processor = ConcurrentProcessor(max_workers=4, rate_limit=0.001)

    def mock_processor(item):
        return item + 1

    items = list(range(50))
    result = processor.process_items(
        items, mock_processor, description="Large batch", rate_limited=False
    )

    assert result.successful == 50
    assert result.failed == 0
    assert sorted(result.results) == list(range(1, 51))
