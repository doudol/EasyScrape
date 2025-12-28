"""Pytest configuration and shared fixtures."""
import pytest
import asyncio
from typing import Generator, Any

# Check for pytest-mock
try:
    import pytest_mock
    HAS_PYTEST_MOCK = True
except ImportError:
    HAS_PYTEST_MOCK = False

# Sample HTML fixtures
SIMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="Test description">
    <meta property="og:title" content="OG Title">
</head>
<body>
    <nav>Navigation</nav>
    <header>Header</header>
    <h1>Main Title</h1>
    <p class="intro">Introduction paragraph</p>
    <div class="content">
        <a href="/page1">Link 1</a>
        <a href="https://example.com/page2">Link 2</a>
        <a href="javascript:alert(1)">Bad Link</a>
        <img src="/img/photo.jpg" alt="Photo">
        <img src="data:image/png;base64,xxx" alt="Bad">
    </div>
    <aside>Sidebar</aside>
    <footer>Footer</footer>
</body>
</html>
"""

JSONLD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Product Page</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Product",
        "price": "99.99"
    }
    </script>
</head>
<body><h1>Product</h1></body>
</html>
"""

MALFORMED_HTML = "<html><h1>Title<p>No closing tags<a href='test'>link"

EMPTY_HTML = ""

TABLE_HTML = """
<html>
<body>
<table>
    <tr><th>Name</th><th>Price</th></tr>
    <tr><td>Item 1</td><td>$10</td></tr>
    <tr><td>Item 2</td><td>$20</td></tr>
</table>
</body>
</html>
"""

FORM_HTML = """
<html>
<body>
<form action="/submit" method="POST">
    <input type="text" name="username" value="">
    <input type="password" name="password">
    <input type="submit" value="Login">
</form>
</body>
</html>
"""


@pytest.fixture
def simple_html() -> str:
    """Simple HTML document for testing."""
    return SIMPLE_HTML


@pytest.fixture
def jsonld_html() -> str:
    """HTML with JSON-LD structured data."""
    return JSONLD_HTML


@pytest.fixture
def malformed_html() -> str:
    """Malformed HTML for edge case testing."""
    return MALFORMED_HTML


@pytest.fixture
def empty_html() -> str:
    """Empty HTML string."""
    return EMPTY_HTML


@pytest.fixture
def table_html() -> str:
    """HTML with table data."""
    return TABLE_HTML


@pytest.fixture
def form_html() -> str:
    """HTML with form elements."""
    return FORM_HTML


@pytest.fixture
def sample_urls() -> list:
    """List of sample URLs for testing."""
    return [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/json",
    ]


@pytest.fixture
def dangerous_urls() -> list:
    """URLs that should be blocked by SSRF protection."""
    return [
        "http://localhost/admin",
        "http://127.0.0.1/secret",
        "http://169.254.169.254/metadata",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://172.16.0.1/private",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
    ]


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Skip tests that require mocker if pytest-mock is not installed
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "requires_mock: mark test as requiring pytest-mock"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests that require mocker if pytest-mock is not installed."""
    if HAS_PYTEST_MOCK:
        return
    
    skip_mock = pytest.mark.skip(reason="pytest-mock not installed")
    for item in items:
        # Check if test uses mocker fixture
        if "mocker" in item.fixturenames:
            item.add_marker(skip_mock)
