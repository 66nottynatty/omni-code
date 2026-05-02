# Documentation Specialist

## Documentation Strategy

### The Four Types of Documentation
1. **Learning-Oriented**: Tutorials for beginners
2. **Goal-Oriented**: How to accomplish specific tasks
3. **Understanding-Oriented**: Conceptual explanations
4. **Reference-Oriented**: Technical specifications

### Documentation Pyramid
```
                    ▲
                   /│\
                  / │ \         Code Examples
                 /  │  \        & Recipes
                /───┼───\
               /    │    \      Task Guides
              /     │     \     & Tutorials
             /──────┼──────\
            /       │       \   Conceptual
           /        │        \  Explanations
          /─────────┼─────────\
         /          │          \ Reference
        /           │           \Material
       ▼────────────┼────────────▼
       API Reference│  Config Docs
                    │
```

## README Best Practices

### Structure Template
```markdown
# Project Name

Brief description (one sentence)

[![CI](https://github.com/user/project/actions/workflows/ci.yml/badge.svg)](https://github.com/user/project/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/user/project/branch/main/graph/badge.svg)](https://codecov.io/gh/user/project)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- Feature 1 with brief description
- Feature 2 with brief description
- Feature 3 with brief description

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Redis 7+

### Installation

\`\`\`bash
# Clone the repository
git clone https://github.com/user/project.git
cd project

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
\`\`\`

## Usage

Basic usage example:

\`\`\`python
from project import Client

client = Client(api_key="your-api-key")
result = client.analyze_data(input_data)
print(result)
\`\`\`

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql://localhost:5432/db |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Development

### Running Tests

\`\`\`bash
pytest tests/ -v
\`\`\`

### Code Style

\`\`\`bash
# Format code
ruff format .

# Lint code
ruff check .
\`\`\`

## License

MIT License - see [LICENSE](LICENSE) for details.
```

## Docstrings

### Google Style
```python
def calculate_metrics(
    data: list[float],
    window_size: int = 7,
    include_outliers: bool = False
) -> dict[str, float]:
    """Calculate statistical metrics for time series data.

    Computes mean, median, standard deviation, and trend for the
    given data points within a rolling window.

    Args:
        data: List of numeric values to analyze.
        window_size: Number of periods for rolling window. Defaults to 7.
        include_outliers: Whether to include outliers in calculation.
            Defaults to False.

    Returns:
        Dictionary containing calculated metrics:
            - mean: Average value
            - median: Median value
            - std: Standard deviation
            - trend: Positive, negative, or flat

    Raises:
        ValueError: If data is empty or window_size < 1.
        TypeError: If data contains non-numeric values.

    Example:
        >>> data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> metrics = calculate_metrics(data, window_size=5)
        >>> print(metrics['mean'])
        5.5
    """
    if not data:
        raise ValueError("Data cannot be empty")
    if window_size < 1:
        raise ValueError("Window size must be at least 1")
    
    window = data[:window_size]
    return {
        'mean': statistics.mean(window),
        'median': statistics.median(window),
        'std': statistics.stdev(window) if len(window) > 1 else 0,
        'trend': _calculate_trend(window)
    }
```

### NumPy Style
```python
def interpolate_values(
    x: np.ndarray,
    y: np.ndarray,
    x_new: np.ndarray,
    method: str = 'linear'
) -> np.ndarray:
    """
    Interpolate values using specified method.

    Parameters
    ----------
    x : np.ndarray
        1-D array of x-coordinates of known data points.
    y : np.ndarray
        1-D array of y-coordinates of known data points.
    x_new : np.ndarray
        1-D array of x-coordinates where to interpolate.
    method : str, optional
        Interpolation method. Options: 'linear', 'cubic', 'nearest'.
        Default is 'linear'.

    Returns
    -------
    np.ndarray
        1-D array of interpolated y-values.

    Raises
    ------
    ValueError
        If x and y have different lengths or x is not sorted.

    Notes
    -----
    Linear interpolation connects adjacent points with straight lines.
    Cubic interpolation uses piecewise cubic polynomials for smoother results.

    Examples
    --------
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([1, 4, 9])
    >>> interpolate_values(x, y, np.array([1.5, 2.5]))
    array([2.5, 6.5])
    """
    pass
```

## Changelog Management

### Keep a Changelog Format
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-15

### Added
- New user profile API endpoints
- Support for OAuth2 authentication
- Webhook notifications for order events
- Rate limiting middleware

### Changed
- **Breaking**: `UserService.get_user()` now requires authentication
- **Breaking**: Database schema updated (see migration guide)
- Improved error messages with actionable suggestions
- Performance improvements for bulk operations

### Deprecated
- `legacy_api` flag - will be removed in v3.0
- `format=xml` parameter - use JSON instead

### Fixed
- Fixed race condition in concurrent order processing
- Fixed memory leak in long-running background tasks
- Fixed timezone handling for scheduled reports

### Security
- Updated bcrypt to latest version
- Fixed potential XSS in markdown rendering
- Added rate limiting to prevent brute force attacks
```

## API Documentation

### OpenAPI Specification
```python
# app/docs.py
from fastapi import OpenAPI

description = """
## Overview

The OmniCode API provides programmatic access to the platform's features.

## Authentication

All API requests require authentication via Bearer token:

```
Authorization: Bearer <your-token>
```

## Rate Limiting

- Standard tier: 60 requests/minute
- Pro tier: 600 requests/minute
- Enterprise: Custom limits

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Server Error - Something went wrong on our end |
"""

tags_metadata = [
    {
        "name": "users",
        "description": "User management operations",
    },
    {
        "name": "orders",
        "description": "Order processing and tracking",
    },
    {
        "name": "webhooks",
        "description": "Configure webhook notifications",
    },
]
```

## Code Examples in Documentation

```python
# Example with clear annotations
def process_order(order_id: int) -> OrderResult:
    """
    Process an order through the fulfillment pipeline.
    
    Parameters
    ----------
    order_id : int
        The unique identifier of the order to process.
        
    Returns
    -------
    OrderResult
        Processing result with status and any errors.
        
    Examples
    --------
    Basic usage:
    
    >>> result = process_order(12345)
    >>> print(result.status)
    'completed'
    
    With error handling:
    
    >>> result = process_order(99999)
    >>> if result.errors:
    ...     print(f"Errors: {result.errors}")
    Errors: ['Order not found']
    """
    pass
```

## Documentation-as-Code

### Living Documentation
```markdown
<!-- FEATURES.md -->
# Features

This file contains feature documentation.
Auto-generated: Reference implementation links are updated by CI.

## Order Processing

| Feature | Status | Code Reference |
|---------|--------|----------------|
| Order creation | ✅ Implemented | `app/services/order.py:create_order()` |
| Order cancellation | ✅ Implemented | `app/services/order.py:cancel_order()` |
| Order refunds | 🚧 In Progress | `app/services/order.py:refund_order()` |
| Partial refunds | 📋 Planned | - |
```

## Documentation Tools

| Tool | Purpose |
|------|---------|
| MkDocs | Static site generator |
| Material for MkDocs | Material Design theme |
| MKDocs Material | Better navigation |
| Sphinx | Python documentation |
| Docusaurus | React-based docs |
| Mintlify | Modern API docs |
| Swagger/OpenAPI | API reference |
| Redoc | Alternative API display |
