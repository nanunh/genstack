"""
Shared pytest fixtures and setup for StackGPT tests.

Key responsibilities:
- Stub mysql.connector BEFORE database.py is imported (it calls
  create_database_and_tables() at module level, which would fail without MySQL).
- Provide a session-scoped FastAPI TestClient.
- Provide a reusable sample ProjectResponse fixture.
"""
import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Environment variables — set before any project module is loaded
# ---------------------------------------------------------------------------
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "stackgpt_test")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")

# ---------------------------------------------------------------------------
# 2. Stub mysql.connector so database.py doesn't need a live MySQL server.
#    database.py runs create_database_and_tables() on import; the mock
#    connection/cursor silently no-ops every call.
# ---------------------------------------------------------------------------
_mock_mysql = MagicMock()
_mock_mysql.Error = Exception          # `except Error` needs a real exception type
sys.modules.setdefault("mysql", MagicMock())
sys.modules.setdefault("mysql.connector", _mock_mysql)

# ---------------------------------------------------------------------------
# 3. Pytest fixtures
# ---------------------------------------------------------------------------
import pytest


@pytest.fixture(scope="session")
def app():
    """Import and return the FastAPI app (once per test session)."""
    from server import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    """Session-scoped TestClient; lifespan runs once for the whole session."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_project():
    """A minimal in-memory ProjectResponse for use in unit tests."""
    from models import ProjectResponse, FileContent
    return ProjectResponse(
        project_id="test-proj-1234",
        project_name="test-project",
        files=[
            FileContent(path="app.py", content='print("hello")', is_binary=False),
            FileContent(path="README.md", content="# Test Project", is_binary=False),
        ],
        instructions="Run with: python app.py",
        created_at="2026-01-01T00:00:00",
    )
