"""Integration-style tests for HTTP endpoints using FastAPI's TestClient.

The test client is session-scoped (created once per test run).
For tests that need a predictable store state, we directly manipulate
the shared `projects_store` dict and clean up afterwards.
"""
import pytest
from store import projects_store, running_processes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_project(sample_project):
    """Insert sample_project into the global store, return its ID."""
    projects_store[sample_project.project_id] = sample_project
    return sample_project.project_id


def _remove_project(project_id):
    projects_store.pop(project_id, None)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_response_contains_status_field(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_response_contains_features(self, client):
        data = client.get("/health").json()
        assert "features" in data


# ---------------------------------------------------------------------------
# Project listing
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_empty_store_returns_200(self, client):
        projects_store.clear()
        response = client.get("/api/projects")
        assert response.status_code == 200

    def test_response_is_a_list(self, client):
        projects_store.clear()
        data = client.get("/api/projects").json()
        # Endpoint returns a plain JSON array of project objects
        assert isinstance(data, list)

    def test_project_appears_in_listing(self, client, sample_project):
        projects_store.clear()
        _load_project(sample_project)
        try:
            data = client.get("/api/projects").json()
            project_ids = [p["project_id"] for p in data]
            assert sample_project.project_id in project_ids
        finally:
            _remove_project(sample_project.project_id)


# ---------------------------------------------------------------------------
# Get single project
# ---------------------------------------------------------------------------

class TestGetProject:
    def test_unknown_id_returns_404(self, client):
        projects_store.clear()
        response = client.get("/api/projects/does-not-exist-9999")
        assert response.status_code == 404

    def test_known_id_returns_200(self, client, sample_project):
        _load_project(sample_project)
        try:
            response = client.get(f"/api/projects/{sample_project.project_id}")
            assert response.status_code == 200
        finally:
            _remove_project(sample_project.project_id)

    def test_response_contains_project_fields(self, client, sample_project):
        _load_project(sample_project)
        try:
            data = client.get(f"/api/projects/{sample_project.project_id}").json()
            assert data["project_id"] == sample_project.project_id
            assert data["project_name"] == sample_project.project_name
            assert isinstance(data["files"], list)
        finally:
            _remove_project(sample_project.project_id)


# ---------------------------------------------------------------------------
# Running projects
# ---------------------------------------------------------------------------

class TestRunningProjects:
    def test_returns_200(self, client):
        response = client.get("/api/projects/running")
        assert response.status_code == 200

    def test_response_has_running_projects_key(self, client):
        data = client.get("/api/projects/running").json()
        assert "running_projects" in data

    def test_empty_when_nothing_running(self, client):
        running_processes.clear()
        data = client.get("/api/projects/running").json()
        # get_running_projects() returns a dict of {project_id: info}
        assert data["running_projects"] == {}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_signup_missing_body_returns_422(self, client):
        response = client.post("/api/auth/signup", json={})
        assert response.status_code == 422

    def test_login_missing_body_returns_422(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_login_db_failure_returns_401(self, client):
        from unittest.mock import patch
        with patch("auth.get_db_connection", return_value=None):
            response = client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "pass"},
            )
        assert response.status_code == 401

    def test_me_without_header_returns_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_logout_returns_200(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 200

    def test_root_redirects(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (301, 302, 307, 308)

    def test_login_page_returns_html(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# MCP info endpoint
# ---------------------------------------------------------------------------

class TestMCPEndpoints:
    def test_mcp_info_returns_200(self, client):
        response = client.get("/mcp/info")
        assert response.status_code == 200

    def test_mcp_tools_returns_list(self, client):
        data = client.get("/mcp/tools").json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0
