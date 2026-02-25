"""Tests for Pydantic models in models.py."""
import pytest
from pydantic import ValidationError

from models import (
    SignupRequest,
    LoginRequest,
    ProjectRequest,
    FileContent,
    ProjectResponse,
    MCPTool,
    MCPToolCall,
    CodeModificationRequest,
    CodeModificationResponse,
    EnhancedCodeAssistantRequest,
    EnhancedCodeAssistantResponse,
    ChatMessage,
)


# ---------------------------------------------------------------------------
# SignupRequest
# ---------------------------------------------------------------------------

class TestSignupRequest:
    def test_valid(self):
        req = SignupRequest(name="Alice", email="alice@example.com", password="secret")
        assert req.name == "Alice"
        assert req.email == "alice@example.com"
        assert req.password == "secret"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="alice@example.com", password="secret")

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            SignupRequest(name="Alice", password="secret")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            SignupRequest(name="Alice", email="alice@example.com")


# ---------------------------------------------------------------------------
# LoginRequest
# ---------------------------------------------------------------------------

class TestLoginRequest:
    def test_valid_with_defaults(self):
        req = LoginRequest(email="alice@example.com", password="secret")
        assert req.remember is False

    def test_remember_true(self):
        req = LoginRequest(email="alice@example.com", password="secret", remember=True)
        assert req.remember is True

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")


# ---------------------------------------------------------------------------
# ProjectRequest
# ---------------------------------------------------------------------------

class TestProjectRequest:
    def test_all_fields_optional(self):
        req = ProjectRequest()
        assert req.prompt is None
        assert req.project_name is None
        assert req.auto_run is False
        assert req.input_mode == "text"
        assert req.file_analysis_prompt is None

    def test_with_prompt_and_auto_run(self):
        req = ProjectRequest(prompt="Build a todo app", auto_run=True)
        assert req.prompt == "Build a todo app"
        assert req.auto_run is True


# ---------------------------------------------------------------------------
# FileContent
# ---------------------------------------------------------------------------

class TestFileContent:
    def test_valid_defaults(self):
        fc = FileContent(path="app.py", content='print("hi")')
        assert fc.is_binary is False

    def test_binary_flag(self):
        fc = FileContent(path="logo.png", content="", is_binary=True)
        assert fc.is_binary is True

    def test_missing_path_raises(self):
        with pytest.raises(ValidationError):
            FileContent(content="code")

    def test_missing_content_raises(self):
        with pytest.raises(ValidationError):
            FileContent(path="app.py")


# ---------------------------------------------------------------------------
# ProjectResponse
# ---------------------------------------------------------------------------

class TestProjectResponse:
    def test_valid_minimal(self):
        pr = ProjectResponse(
            project_id="abc123",
            project_name="my-app",
            files=[FileContent(path="main.py", content="# main")],
            instructions="Run: python main.py",
            created_at="2026-01-01T00:00:00",
        )
        assert pr.project_id == "abc123"
        assert len(pr.files) == 1
        assert pr.token_usage is None

    def test_with_token_usage(self):
        pr = ProjectResponse(
            project_id="abc123",
            project_name="my-app",
            files=[],
            instructions="",
            created_at="2026-01-01T00:00:00",
            token_usage={"input_tokens": 100, "output_tokens": 200},
        )
        assert pr.token_usage["input_tokens"] == 100

    def test_empty_files_list(self):
        pr = ProjectResponse(
            project_id="abc123",
            project_name="my-app",
            files=[],
            instructions="",
            created_at="2026-01-01T00:00:00",
        )
        assert pr.files == []

    def test_missing_project_id_raises(self):
        with pytest.raises(ValidationError):
            ProjectResponse(
                project_name="my-app",
                files=[],
                instructions="",
                created_at="2026-01-01T00:00:00",
            )


# ---------------------------------------------------------------------------
# MCPTool / MCPToolCall
# ---------------------------------------------------------------------------

class TestMCPTool:
    def test_valid(self):
        tool = MCPTool(
            name="create_file",
            description="Creates a new file in the project",
            input_schema={"type": "object", "properties": {}},
        )
        assert tool.name == "create_file"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            MCPTool(description="desc", input_schema={})


class TestMCPToolCall:
    def test_valid(self):
        call = MCPToolCall(tool="create_file", parameters={"path": "app.py"})
        assert call.tool == "create_file"
        assert call.parameters["path"] == "app.py"


# ---------------------------------------------------------------------------
# CodeModificationRequest / CodeModificationResponse
# ---------------------------------------------------------------------------

class TestCodeModificationRequest:
    def test_default_modification_type(self):
        req = CodeModificationRequest(
            project_id="abc",
            file_path="app.py",
            modification_prompt="Add logging",
        )
        assert req.modification_type == "general"

    def test_custom_modification_type(self):
        req = CodeModificationRequest(
            project_id="abc",
            file_path="app.py",
            modification_prompt="Fix bug",
            modification_type="bugfix",
        )
        assert req.modification_type == "bugfix"

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            CodeModificationRequest(modification_prompt="Fix bug")


class TestCodeModificationResponse:
    def test_valid(self):
        resp = CodeModificationResponse(
            success=True,
            original_code="x = 1",
            modified_code="x = 2",
            changes_made=["Updated x value"],
            file_path="app.py",
            modification_type="general",
            backup_created=True,
        )
        assert resp.success is True
        assert resp.backup_created is True


# ---------------------------------------------------------------------------
# EnhancedCodeAssistantRequest / Response
# ---------------------------------------------------------------------------

class TestEnhancedCodeAssistantRequest:
    def test_valid_no_context(self):
        req = EnhancedCodeAssistantRequest(project_id="abc", message="Add a login page")
        assert req.context is None

    def test_with_context(self):
        req = EnhancedCodeAssistantRequest(
            project_id="abc",
            message="Add a login page",
            context="Flask app",
        )
        assert req.context == "Flask app"


class TestEnhancedCodeAssistantResponse:
    def test_valid(self):
        resp = EnhancedCodeAssistantResponse(
            success=True,
            action_taken="created_file",
            affected_files=["app.py"],
            new_files=["login.html"],
            deleted_files=[],
            explanation="Added login page",
            changes_summary=["Created login.html"],
            next_steps=["Run the app"],
            mcp_calls_made=[],
        )
        assert resp.success is True
        assert "login.html" in resp.new_files


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------

class TestChatMessage:
    def test_valid(self):
        msg = ChatMessage(
            message="Hello",
            sender="user",
            timestamp="2026-01-01T12:00:00",
            project_id="abc123",
        )
        assert msg.sender == "user"
        assert msg.project_id == "abc123"

    def test_missing_sender_raises(self):
        with pytest.raises(ValidationError):
            ChatMessage(message="Hi", timestamp="2026-01-01T12:00:00", project_id="abc")
