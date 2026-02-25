"""Tests for utility functions in utils/file_ops.py."""
import pytest
from pathlib import Path
from unittest.mock import patch

from store import projects_store


# ---------------------------------------------------------------------------
# get_project_response_data
# ---------------------------------------------------------------------------

class TestGetProjectResponseData:
    def test_returns_dict_with_expected_keys(self, sample_project):
        from utils.file_ops import get_project_response_data
        data = get_project_response_data(sample_project)
        assert data["project_id"] == "test-proj-1234"
        assert data["project_name"] == "test-project"
        assert isinstance(data["files"], list)
        assert len(data["files"]) == 2

    def test_files_contain_path_and_content(self, sample_project):
        from utils.file_ops import get_project_response_data
        data = get_project_response_data(sample_project)
        paths = [f["path"] for f in data["files"]]
        assert "app.py" in paths
        assert "README.md" in paths

    def test_token_usage_defaults_to_none(self, sample_project):
        from utils.file_ops import get_project_response_data
        data = get_project_response_data(sample_project)
        assert data["token_usage"] is None


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------

class TestCreateBackup:
    @pytest.mark.asyncio
    async def test_creates_backup_file(self, sample_project, tmp_path):
        from utils.file_ops import create_backup

        # Reconstruct the exact directory name the code expects
        project_dir = tmp_path / f"{sample_project.project_name}_{sample_project.project_id[:8]}"
        project_dir.mkdir()
        (project_dir / "app.py").write_text('print("hello")')

        projects_store["test-proj-1234"] = sample_project
        try:
            with patch("utils.file_ops.PROJECTS_DIR", tmp_path):
                backup_path = await create_backup("test-proj-1234", "app.py")
            assert "backup" in backup_path
            assert backup_path.endswith(".py")
        finally:
            projects_store.pop("test-proj-1234", None)

    @pytest.mark.asyncio
    async def test_backup_fails_for_missing_project(self):
        from utils.file_ops import create_backup
        projects_store.pop("nonexistent", None)
        with pytest.raises(Exception, match="Failed to create backup"):
            await create_backup("nonexistent", "app.py")

    @pytest.mark.asyncio
    async def test_backup_fails_for_missing_file(self, sample_project, tmp_path):
        from utils.file_ops import create_backup

        project_dir = tmp_path / f"{sample_project.project_name}_{sample_project.project_id[:8]}"
        project_dir.mkdir()
        # Do NOT create "app.py" — backup should fail

        projects_store["test-proj-1234"] = sample_project
        try:
            with patch("utils.file_ops.PROJECTS_DIR", tmp_path):
                with pytest.raises(Exception, match="Failed to create backup"):
                    await create_backup("test-proj-1234", "app.py")
        finally:
            projects_store.pop("test-proj-1234", None)


# ---------------------------------------------------------------------------
# apply_code_modification
# ---------------------------------------------------------------------------

class TestApplyCodeModification:
    @pytest.mark.asyncio
    async def test_updates_file_on_disk_and_in_store(self, sample_project, tmp_path):
        from utils.file_ops import apply_code_modification

        project_dir = tmp_path / f"{sample_project.project_name}_{sample_project.project_id[:8]}"
        project_dir.mkdir()
        source_file = project_dir / "app.py"
        source_file.write_text('print("hello")')

        projects_store["test-proj-1234"] = sample_project
        try:
            with patch("utils.file_ops.PROJECTS_DIR", tmp_path):
                result = await apply_code_modification(
                    "test-proj-1234", "app.py", 'print("world")'
                )
            assert result is True
            assert source_file.read_text() == 'print("world")'
            # In-memory store should also be updated
            store_file = next(
                f for f in projects_store["test-proj-1234"].files if f.path == "app.py"
            )
            assert store_file.content == 'print("world")'
        finally:
            projects_store.pop("test-proj-1234", None)

    @pytest.mark.asyncio
    async def test_fails_for_missing_project(self):
        from utils.file_ops import apply_code_modification
        projects_store.pop("nonexistent", None)
        with pytest.raises(Exception):
            await apply_code_modification("nonexistent", "app.py", "code")


# ---------------------------------------------------------------------------
# scan_projects_directory
# ---------------------------------------------------------------------------

class TestScanProjectsDirectory:
    @pytest.mark.asyncio
    async def test_returns_dict_with_projects_key(self, tmp_path):
        from utils.file_ops import scan_projects_directory
        with patch("utils.file_ops.PROJECTS_DIR", tmp_path):
            result = await scan_projects_directory()
        assert "projects" in result
        assert isinstance(result["projects"], list)

    @pytest.mark.asyncio
    async def test_empty_directory_returns_empty_list(self, tmp_path):
        from utils.file_ops import scan_projects_directory
        with patch("utils.file_ops.PROJECTS_DIR", tmp_path):
            result = await scan_projects_directory()
        assert result["projects"] == []

    @pytest.mark.asyncio
    async def test_nonexistent_directory_returns_empty_list(self, tmp_path):
        from utils.file_ops import scan_projects_directory
        missing_dir = tmp_path / "does_not_exist"
        with patch("utils.file_ops.PROJECTS_DIR", missing_dir):
            result = await scan_projects_directory()
        assert result["projects"] == []
