# Contributing to Chronicon

**[Documentation Index](DOCUMENTATION.md)** > Contributing

**For Developers:** [Development Guide](DEVELOPMENT.md) | [Architecture](ARCHITECTURE.md) | [API Reference](API_REFERENCE.md)

---

Thank you for your interest in contributing to Chronicon! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please:
- Be respectful and considerate
- Be collaborative and constructive
- Be patient and welcoming to newcomers
- Respect differing viewpoints and experiences

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Spam or promotional content
- Publishing others' private information

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

**🐛 Bug Reports**
- Search existing issues first
- Include reproducible steps
- Provide system information
- Attach logs if relevant

**✨ Feature Requests**
- Explain the use case
- Describe expected behavior
- Consider implementation approach
- Discuss in issues before large PRs

**📝 Documentation**
- Fix typos or unclear explanations
- Add examples or tutorials
- Improve API documentation
- Update guides for new features

**🔧 Code Contributions**
- Bug fixes
- New features
- Performance improvements
- Refactoring

**🧪 Testing**
- Add missing test coverage
- Improve test quality
- Add integration tests
- Performance benchmarks

## Development Setup

### Prerequisites

- **Python 3.11+** (required)
- **Git** (required)
- **uv** (recommended) or pip
- **SQLite 3.x** (bundled with Python)
- **PostgreSQL 12+** (optional, for PostgreSQL backend)

### Quick Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/chronicon.git
cd chronicon

# 2. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set up development environment
uv sync --all-extras

# 4. Verify installation
.venv/bin/python -m pytest

# All 350 tests should pass ✓
```

### Alternative: Using pip

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev,postgres]"
pytest
```

## Development Workflow

### 1. Find or Create an Issue

- Check [existing issues](https://github.com/19-84/chronicon/issues)
- Create new issue for bugs or features
- Get feedback before starting large changes
- Link your PR to the issue

### 2. Create a Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/descriptive-name
# or for bugs:
git checkout -b fix/issue-123
```

**Branch naming:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `test/` - Test improvements
- `refactor/` - Code refactoring

### 3. Make Your Changes

**Code Conventions:**
- Add ABOUTME comments to new files (2 lines)
- Use type hints for all function signatures
- Add docstrings to public functions/classes
- Follow PEP 8 (enforced by ruff)
- Keep functions focused and small

**Example:**
```python
# ABOUTME: Brief description of what this file does
# ABOUTME: Second line with additional context

"""Module docstring explaining purpose."""

from typing import Optional

def process_data(input_str: str, limit: int = 100) -> Optional[str]:
    """
    Process input string with optional limit.
    
    Args:
        input_str: String to process
        limit: Maximum length (default 100)
        
    Returns:
        Processed string, or None if invalid
    """
    if not input_str:
        return None
    return input_str[:limit]
```

### 4. Write Tests (TDD Approach)

We practice Test-Driven Development:

```python
# tests/test_my_feature.py

def test_process_data_with_valid_input():
    """Test processing valid input."""
    result = process_data("hello world", limit=5)
    assert result == "hello"

def test_process_data_with_empty_input():
    """Test handling empty input."""
    result = process_data("", limit=5)
    assert result is None
```

**Run your tests:**
```bash
.venv/bin/python -m pytest tests/test_my_feature.py -v
```

### 5. Check Code Quality

```bash
# Format code
.venv/bin/ruff format src/ tests/

# Lint and auto-fix issues
.venv/bin/ruff check src/ tests/ --fix

# Type check
.venv/bin/pyright src/ tests/

# Run all quality checks
.venv/bin/ruff format --check src/ tests/ && \
.venv/bin/ruff check src/ tests/ && \
.venv/bin/pyright src/ tests/
```

### 6. Run Full Test Suite

```bash
# Run all tests
.venv/bin/python -m pytest

# With coverage report
.venv/bin/python -m pytest --cov=chronicon --cov-report=term-missing
```

**Coverage Goals:**
- Minimum: 70% overall
- Target: 80% overall
- Critical paths: 100% (database, exporters)

### 7. Commit Your Changes

```bash
git add .
git commit --no-gpg-sign -m "feat: add new feature"
```

**Commit Message Format:**

```
<type>: <short description>

<optional detailed description>

<optional footer with issue references>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding/updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Build/config changes

**Examples:**
```
feat: add PostgreSQL support for large archives

Implements PostgreSQL backend as alternative to SQLite.
Includes connection pooling and optimized queries.

Closes #123
```

```
fix: handle null values in post metadata

Posts with missing metadata were causing crashes.
Now gracefully handles None values.

Fixes #456
```

### 8. Push and Create Pull Request

```bash
git push origin feature/my-feature
```

Then create a PR on GitHub with:
- Clear title and description
- Link to related issue
- Summary of changes
- Testing performed
- Screenshots (if UI changes)

## Testing Guidelines

### Test Organization

```
tests/
├── test_models.py          # Model unit tests
├── test_database.py        # Database operations
├── test_fetchers.py        # API fetching
├── test_exporters.py       # Export formats
├── test_integration.py     # End-to-end tests
└── fixtures/               # Test data
```

### Writing Good Tests

**Do:**
- Test one thing per test
- Use descriptive test names
- Use fixtures for setup
- Test edge cases
- Test error conditions

**Don't:**
- Test implementation details
- Create flaky tests
- Skip test cleanup
- Use hard-coded values without explanation
- Test third-party code

### Running Specific Tests

```bash
# Single file
.venv/bin/python -m pytest tests/test_database.py

# Single test
.venv/bin/python -m pytest tests/test_database.py::test_save_post

# Tests matching pattern
.venv/bin/python -m pytest -k "test_export"

# With verbose output
.venv/bin/python -m pytest -v

# Stop on first failure
.venv/bin/python -m pytest -x
```

## Code Style

### Formatting

We use **ruff** for formatting (follows Black style):
- Line length: 88 characters
- 4-space indentation
- Double quotes for strings

### Linting

We use **ruff** for linting with these rules:
- pyflakes (F)
- pycodestyle (E, W)
- isort (I)
- pydocstyle (D)
- pyupgrade (UP)

### Type Checking

We use **pyright** for static type checking:
- All function signatures must have type hints
- Public APIs must be fully typed
- Use `typing` module for complex types

### Pre-Commit Checklist

Before committing, ensure:
- [ ] Code is formatted with ruff
- [ ] No linting errors
- [ ] Type checking passes
- [ ] All tests pass
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] Commit message follows format

## Pull Request Process

### Before Submitting

1. **Rebase on latest main:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Squash WIP commits** (if needed):
   ```bash
   git rebase -i HEAD~3  # Last 3 commits
   ```

3. **Run full test suite:**
   ```bash
   .venv/bin/python -m pytest
   ```

4. **Check code quality:**
   ```bash
   .venv/bin/ruff format --check src/ tests/
   .venv/bin/ruff check src/ tests/
   .venv/bin/pyright src/ tests/
   ```

### PR Description Template

```markdown
## Description
Brief description of changes

## Related Issue
Closes #123

## Changes Made
- Added X feature
- Fixed Y bug
- Updated Z documentation

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] All tests passing
- [ ] Tested manually

## Checklist
- [ ] Code follows style guide
- [ ] Added/updated documentation
- [ ] Added/updated tests
- [ ] All tests pass
- [ ] No new warnings
```

### Review Process

1. **Automated Checks:** GitHub Actions will run tests and linting
2. **Code Review:** Maintainer will review your code
3. **Feedback:** Address any requested changes
4. **Approval:** Once approved, your PR will be merged

### After Merge

- Your contribution will be included in the next release
- You'll be credited in the release notes
- Thank you for contributing! 🎉

## Reporting Issues

### Before Reporting

- Search existing issues (open and closed)
- Try latest version
- Check troubleshooting guide
- Gather system information

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. With these options '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- Chronicon version:
- Python version:
- OS:
- Database: SQLite/PostgreSQL

**Additional context**
- Error messages
- Log output
- Screenshots
```

### Feature Request Template

```markdown
**Problem**
Describe the problem this feature would solve.

**Proposed Solution**
Describe your proposed solution.

**Alternatives Considered**
What alternatives have you considered?

**Use Case**
Describe your use case.

**Additional Context**
Any other context or examples.
```

## Getting Help

### Resources

- **Documentation:** https://github.com/19-84/chronicon#readme
- **Issues:** https://github.com/19-84/chronicon/issues
- **Discussions:** https://github.com/19-84/chronicon/discussions

### Questions

- Check [FAQ.md](FAQ.md) first
- Search existing discussions
- Open a GitHub Discussion for questions
- For security issues, use GitHub Security Advisories

## Recognition

Contributors are recognized in:
- Release notes
- Git history
- Future contributors list

## License

By contributing, you agree that your contributions will be licensed under the Unlicense (public domain).

## Thank You!

Every contribution, no matter how small, is appreciated. Thank you for helping make Chronicon better!

---

**Next Steps:**
- [DEVELOPMENT.md](DEVELOPMENT.md) - Detailed development workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) - Understanding the codebase
- [API_REFERENCE.md](API_REFERENCE.md) - API documentation
- [EXAMPLES.md](EXAMPLES.md) - Code examples

**Return to:** [Documentation Index](DOCUMENTATION.md)
