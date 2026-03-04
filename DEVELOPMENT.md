# Development Guide

**[Documentation Index](DOCUMENTATION.md)** > Development

**For Contributors:** [Contributing](CONTRIBUTING.md) | [Architecture](ARCHITECTURE.md) | [API Reference](API_REFERENCE.md)

---

Developer documentation for contributing to Chronicon.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Debugging](#debugging)

## Development Setup

### Prerequisites

- Python 3.11 or later
- uv (recommended) or pip
- Git
- SQLite 3.x (built into Python)
- Optional: PostgreSQL 12+ (for PostgreSQL backend development)

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/19-84/chronicon.git
cd chronicon

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Create virtual environment and install dependencies
uv sync --all-extras

# 4. Verify installation
.venv/bin/python -c "import chronicon; print(chronicon.__version__)"

# 5. Run tests to verify setup
.venv/bin/python -m pytest
```

### Alternative: Using pip

```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

pip install -e ".[dev,postgres]"
pytest
```

### IDE Setup

**VS Code:**

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

**PyCharm:**
- Set interpreter to `.venv/bin/python`
- Enable ruff as formatter
- Configure pytest as test runner

## Project Structure

```
chronicon/
├── src/chronicon/           # Main package
│   ├── models/             # Data models (Post, Topic, User, etc.)
│   ├── storage/            # Database layer (SQLite, PostgreSQL)
│   ├── fetchers/           # API clients and fetchers
│   ├── processors/         # Content processing (HTML, URL rewriting)
│   ├── exporters/          # Export formats (HTML, Markdown)
│   ├── watch/              # Continuous monitoring
│   ├── utils/              # Utilities
│   ├── config.py           # Configuration loading
│   └── cli.py              # CLI interface
├── tests/                   # Test suite
│   ├── fixtures/           # Test data
│   └── test_*.py           # Test files
├── templates/               # Jinja2 templates for HTML export
├── static/                  # CSS and JS for HTML export
├── examples/                # Example configurations and deployments
│   ├── docker/             # Docker examples
│   └── systemd/            # Systemd service examples
├── docs/                    # Additional documentation
├── pyproject.toml          # Project configuration
├── README.md               # User documentation
├── CLAUDE.md               # AI agent development guide
├── ARCHITECTURE.md         # Architecture documentation
└── *.md                    # Additional guides
```

### Key Directories

**`src/chronicon/`**: Main source code
- **`models/`**: Dataclasses for domain objects (Post, Topic, User, Category, SiteConfig)
- **`storage/`**: Database abstraction (SQLite & PostgreSQL implementations)
- **`fetchers/`**: HTTP API clients with rate limiting
- **`processors/`**: Content transformation (HTML parsing, URL rewriting)
- **`exporters/`**: Export format implementations
- **`watch/`**: Daemon, git integration, health monitoring
- **`utils/`**: Cross-cutting utilities

**`tests/`**: Test suite (350+ tests)
- Unit tests for each module
- Integration tests for workflows
- Fixtures for reproducible testing

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/issue-123
```

### 2. Make Changes

Follow code conventions (see below). Add ABOUTME comments to new files:

```python
# ABOUTME: Brief description of what this file does
# ABOUTME: Second line with additional context
```

### 3. Write Tests

**TDD Approach (Recommended):**

```python
# tests/test_my_feature.py

def test_my_feature():
    """Test that my feature works correctly."""
    # Arrange
    input_data = {...}
    
    # Act
    result = my_feature(input_data)
    
    # Assert
    assert result == expected_output
```

Run tests:
```bash
.venv/bin/python -m pytest tests/test_my_feature.py -v
```

### 4. Check Code Quality

```bash
# Format code
.venv/bin/ruff format src/ tests/

# Lint
.venv/bin/ruff check src/ tests/ --fix

# Type check
.venv/bin/pyright src/ tests/

# Run all checks
.venv/bin/ruff format --check src/ tests/ && \
.venv/bin/ruff check src/ tests/ && \
.venv/bin/pyright src/ tests/
```

### 5. Run Tests

```bash
# Run all tests
.venv/bin/python -m pytest

# With coverage
.venv/bin/python -m pytest --cov=chronicon --cov-report=term-missing

# Specific test
.venv/bin/python -m pytest tests/test_my_feature.py::test_specific_case -v
```

### 6. Commit Changes

```bash
git add .
git commit --no-gpg-sign -m "feat: add my new feature"
```

**Commit message format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Build/config changes

### 7. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a pull request on GitHub.

## Testing

### Test Structure

```
tests/
├── test_models.py           # Model tests
├── test_database.py         # Database tests
├── test_fetchers.py         # Fetcher tests
├── test_exporters.py        # Exporter tests
├── test_cli.py              # CLI tests
├── test_integration.py      # End-to-end tests
└── fixtures/                # Test data
    ├── api_responses/       # Sample API responses
    └── sample_data/         # Sample databases
```

### Running Tests

```bash
# All tests
.venv/bin/python -m pytest

# Specific file
.venv/bin/python -m pytest tests/test_database.py

# Specific test
.venv/bin/python -m pytest tests/test_database.py::test_save_post

# With verbose output
.venv/bin/python -m pytest -v

# With coverage
.venv/bin/python -m pytest --cov=chronicon --cov-report=html
# Then open htmlcov/index.html

# Stop on first failure
.venv/bin/python -m pytest -x

# Run in parallel (faster)
.venv/bin/python -m pytest -n auto
```

### Writing Tests

**Example test:**

```python
import pytest
from pathlib import Path
from chronicon.storage import ArchiveDatabase
from chronicon.models import Post

@pytest.fixture
def temp_db(tmp_path):
    """Create temporary test database."""
    db_path = tmp_path / "test.db"
    db = ArchiveDatabase(db_path=db_path)
    yield db
    db.close()

def test_save_and_retrieve_post(temp_db):
    """Test saving and retrieving a post."""
    # Arrange
    post = Post(
        id=123,
        topic_id=1,
        post_number=1,
        username="testuser",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        cooked="<p>Test</p>",
        raw="Test",
        reply_count=0,
        like_count=0
    )
    
    # Act
    temp_db.save_post(post)
    retrieved = temp_db.get_post(123)
    
    # Assert
    assert retrieved is not None
    assert retrieved.id == 123
    assert retrieved.username == "testuser"
```

### Test Coverage Goals

- **Minimum:** 70% overall coverage
- **Target:** 80% overall coverage
- **Critical paths:** 100% coverage (database, API clients, exporters)

## Code Quality

### Formatting

Use `ruff format`:

```bash
.venv/bin/ruff format src/ tests/
```

**Configuration:** See `[tool.ruff]` in `pyproject.toml`

### Linting

Use `ruff check`:

```bash
.venv/bin/ruff check src/ tests/ --fix
```

**Rules:** Configured in `pyproject.toml`

### Type Checking

Use `pyright`:

```bash
.venv/bin/pyright src/ tests/
```

**Type hints required for:**
- Function signatures
- Class attributes
- Return types

### Code Conventions

1. **File headers:** Every file starts with ABOUTME comments
2. **Docstrings:** All public functions, classes, and methods
3. **Type hints:** Required for all function signatures
4. **Line length:** 88 characters (ruff default)
5. **Imports:** Organized by ruff (stdlib, third-party, local)

**Example:**

```python
# ABOUTME: Description of module
# ABOUTME: Additional context

"""Module docstring."""

from pathlib import Path
from typing import Optional

class MyClass:
    """Class docstring."""
    
    def __init__(self, value: int) -> None:
        """
        Initialize MyClass.
        
        Args:
            value: Integer value
        """
        self.value = value
    
    def process(self, data: str) -> Optional[str]:
        """
        Process data.
        
        Args:
            data: Input string
            
        Returns:
            Processed string, or None if invalid
        """
        if not data:
            return None
        return data.upper()
```

## Debugging

### Local Development

```bash
# Run chronicon with Python debugger
python -m pdb -m chronicon.cli archive --urls https://meta.discourse.org
```

### Print Debugging

```python
from rich import print as rprint

rprint("[bold green]Debug info:[/bold green]", variable)
```

### Logging

```python
from chronicon.utils.logger import setup_logger

logger = setup_logger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Testing Specific Components

**Test database operations:**
```python
from chronicon.storage import ArchiveDatabase
from pathlib import Path

db = ArchiveDatabase(db_path=Path("./test.db"))
# Test operations...
db.close()
```

**Test fetchers:**
```python
from chronicon.fetchers import DiscourseAPIClient

client = DiscourseAPIClient(base_url="https://meta.discourse.org", rate_limit=2.0)
data = client.get_json("/latest.json")
print(data)
```

**Test exporters:**
```python
from chronicon.exporters import HTMLStaticExporter

exporter = HTMLStaticExporter(db, output_dir=Path("./test-output"))
exporter.export()
```

### Database Inspection

```bash
# Open database in SQLite
sqlite3 archives/archive.db

# Useful commands:
.tables              # List tables
.schema posts        # Show table schema
SELECT COUNT(*) FROM posts;
SELECT * FROM posts LIMIT 5;
```

### Performance Profiling

```python
import cProfile
import pstats

# Profile code
profiler = cProfile.Profile()
profiler.enable()

# Code to profile
# ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

## Building and Distribution

### Build Package

```bash
# Install build dependencies
pip install build

# Build
python -m build

# Result: dist/chronicon-1.0.0.tar.gz and .whl
```

### Install Locally

```bash
# Install from local source
pip install -e .

# With all extras
pip install -e ".[dev,postgres]"
```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Build package
5. Tag release: `git tag v1.0.0`
6. Push tags: `git push --tags`
7. Create GitHub release
8. (Optional) Publish to PyPI

## Common Development Tasks

### Adding a New Exporter

1. Create file in `src/chronicon/exporters/`
2. Subclass `BaseExporter`
3. Implement `export()` method
4. Add tests in `tests/test_exporters.py`
5. Update CLI to support new format
6. Document in README.md

### Adding a New Database Backend

1. Create file in `src/chronicon/storage/`
2. Subclass `ArchiveDatabaseBase`
3. Implement all required methods
4. Create schema file
5. Add tests
6. Update configuration docs

### Adding New CLI Command

1. Add function to `src/chronicon/cli.py`
2. Add argparse subcommand
3. Add tests in `tests/test_cli.py`
4. Document in README.md

## See Also

**For Developers:**
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute (start here!)
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [CLAUDE.md](CLAUDE.md) - AI agent development guide

**Testing & Quality:**
- [EXAMPLES.md](EXAMPLES.md) - Code examples for testing
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debugging issues

**Other Resources:**
- [README.md](README.md) - User documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history

**Return to:** [Documentation Index](DOCUMENTATION.md)
