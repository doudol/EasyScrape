# Contributing to EasyScrape

Thank you for your interest in contributing to EasyScrape! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/doudol/easyscrape.git
cd easyscrape

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Install pre-commit hooks
pre-commit install

# Install Playwright browsers (for JS rendering tests)
playwright install chromium
```

## Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=easyscrape --cov-report=html

# Run specific test file
pytest tests/test_core.py -v

# Run in parallel
pytest -v -n auto
```

## Code Style

We use the following tools for code quality:

### Black (Formatting)
```bash
# Check formatting
black --check easyscrape/ tests/

# Auto-format
black easyscrape/ tests/
```

### isort (Import Sorting)
```bash
isort easyscrape/ tests/
```

### mypy (Type Checking)
```bash
mypy easyscrape/
```

### Bandit (Security)
```bash
bandit -r easyscrape/
```

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/my-feature
   ```
3. **Make your changes** with clear, descriptive commits
4. **Add tests** for new functionality
5. **Run the test suite** to ensure nothing is broken
6. **Update documentation** if needed
7. **Submit a pull request** with a clear description

### PR Checklist

- [ ] Tests pass (`pytest -v`)
- [ ] Code is formatted (`black --check`)
- [ ] Types check (`mypy easyscrape/`)
- [ ] Security check passes (`bandit -r easyscrape/`)
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (if applicable)

## Coding Guidelines

### Docstrings

Use Google-style docstrings:

```python
def scrape(url: str, config: Optional[Config] = None) -> ScrapeResult:
    """Fetch a URL and return a result with extraction helpers.
    
    Args:
        url: The URL to fetch (must be http:// or https://)
        config: Optional configuration object
    
    Returns:
        ScrapeResult with response data and extraction methods.
    
    Raises:
        InvalidURLError: If URL is invalid or blocked
    
    Example:
        >>> result = scrape("https://example.com")
        >>> print(result.title())
        'Example Domain'
    """
```

### Type Hints

All public APIs must have type hints:

```python
from typing import Optional, List, Dict

def process(items: List[str], config: Optional[Config] = None) -> Dict[str, int]:
    ...
```

### Error Handling

- Use custom exceptions from `easyscrape.exceptions`
- Provide helpful error messages
- Don't catch and silence exceptions without logging

### Security

- All URLs must go through `validate_url()` before fetching
- Never use `eval()` or `exec()`
- Validate all file paths for traversal attacks
- Never log sensitive data (passwords, API keys)

## Reporting Issues

### Bug Reports

Include:
- Python version
- EasyScrape version
- Operating system
- Minimal code to reproduce
- Expected vs actual behavior
- Full traceback (if applicable)

### Feature Requests

Include:
- Clear description of the feature
- Use case / motivation
- Example API (if applicable)

## Questions?

Open a GitHub issue with the `question` label.

Thank you for contributing!
