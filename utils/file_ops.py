import os
import json
import shutil
import zipfile
import tempfile
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import UploadFile

from models import FileContent, ProjectResponse
from store import projects_store, PROJECTS_DIR


# ---------------------------------------------------------------------------
# Backup & apply
# ---------------------------------------------------------------------------

async def create_backup(project_id: str, file_path: str) -> str:
    """Create a backup of the original file"""
    try:
        project = projects_store.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
        full_file_path = project_dir / file_path

        if not full_file_path.exists():
            raise ValueError(f"File {file_path} not found in project")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = full_file_path.parent / f"{full_file_path.stem}_backup_{timestamp}{full_file_path.suffix}"

        shutil.copy2(full_file_path, backup_path)
        return str(backup_path.relative_to(project_dir))

    except Exception as e:
        print(f"[DEBUG] Backup creation failed: {e}")
        raise Exception(f"Failed to create backup: {str(e)}")


async def apply_code_modification(project_id: str, file_path: str, modified_code: str) -> bool:
    """Apply the modified code to the file"""
    try:
        project = projects_store.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
        full_file_path = project_dir / file_path

        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)

        for file_obj in project.files:
            if file_obj.path == file_path:
                file_obj.content = modified_code
                break

        return True

    except Exception as e:
        print(f"[DEBUG] Code application failed: {e}")
        raise Exception(f"Failed to apply code modifications: {str(e)}")


# ---------------------------------------------------------------------------
# In-memory project file helpers
# ---------------------------------------------------------------------------

def get_file_content(project, file_path: str) -> str:
    """Get content of a file from project"""
    for file in project.files:
        if file.path == file_path:
            return file.content
    raise ValueError(f"File {file_path} not found in project")


def update_file_in_project(project, file_path: str, new_content: str):
    """Update file content in project memory"""
    for file in project.files:
        if file.path == file_path:
            file.content = new_content
            return
    raise ValueError(f"File {file_path} not found in project")


def add_file_to_project(project, file_path: str, content: str):
    """Add new file to project"""
    project.files.append(FileContent(
        path=file_path,
        content=content,
        is_binary=False
    ))


def remove_file_from_project(project, file_path: str):
    """Remove file from project memory"""
    project.files = [f for f in project.files if f.path != file_path]


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

async def save_file_to_filesystem(project, file_path: str, content: str):
    """Save file to filesystem"""
    project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
    full_file_path = project_dir / file_path
    full_file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def delete_file_from_filesystem(project, file_path: str):
    """Delete file from filesystem"""
    project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
    full_file_path = project_dir / file_path
    if full_file_path.exists():
        full_file_path.unlink()


async def save_project_to_filesystem(project: ProjectResponse):
    """Save project files to filesystem"""
    project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"
    project_dir.mkdir(exist_ok=True)

    metadata = {
        "project_id": project.project_id,
        "project_name": project.project_name,
        "created_at": project.created_at,
        "instructions": project.instructions,
        "file_count": len(project.files)
    }

    with open(project_dir / "project_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    for file in project.files:
        file_path = project_dir / file.path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if file.is_binary:
                with open(file_path, "wb") as f:
                    f.write(file.content.encode())
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file.content)
        except Exception as e:
            print(f"Warning: Could not save file {file.path}: {e}")

    with open(project_dir / "README_INSTRUCTIONS.md", "w", encoding="utf-8") as f:
        f.write(f"# {project.project_name} - Instructions\n\n")
        f.write(f"**Project ID:** {project.project_id}\n")
        f.write(f"**Created:** {project.created_at}\n\n")
        f.write("## Setup and Run Instructions\n\n")
        f.write(project.instructions)


async def load_project_from_filesystem(project_id: str, project_dir: Path) -> Optional[ProjectResponse]:
    """Load a project from filesystem into the projects_store"""
    try:
        metadata_file = project_dir / "project_metadata.json"
        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        files = []
        for file_path in project_dir.rglob('*'):
            if file_path.is_file() and file_path.name not in ['project_metadata.json', 'README_INSTRUCTIONS.md']:
                relative_path = file_path.relative_to(project_dir)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    files.append(FileContent(
                        path=str(relative_path),
                        content=content,
                        is_binary=False
                    ))
                except UnicodeDecodeError:
                    with open(file_path, 'rb') as f:
                        content = f.read()

                    files.append(FileContent(
                        path=str(relative_path),
                        content=f"[Binary file - {len(content)} bytes]",
                        is_binary=True
                    ))

        project_response = ProjectResponse(
            project_id=metadata.get("project_id", project_id),
            project_name=metadata.get("project_name", project_dir.name),
            files=files,
            instructions=metadata.get("instructions", "No instructions available"),
            created_at=metadata.get("created_at", datetime.now().isoformat())
        )

        projects_store[project_id] = project_response

        return project_response

    except Exception as e:
        print(f"Error loading project from filesystem: {e}")
        return None


def get_project_response_data(project_response):
    """Convert project response to dict format"""
    return project_response.model_dump() if hasattr(project_response, 'model_dump') else project_response.dict()


# ---------------------------------------------------------------------------
# Directory scanning
# ---------------------------------------------------------------------------

async def scan_projects_directory() -> dict:
    """Scan the generated_projects directory for all projects"""
    try:
        all_projects = []

        if not PROJECTS_DIR.exists():
            return {"projects": []}

        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue

            try:
                metadata_file = project_dir / "project_metadata.json"

                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    project_id = metadata.get("project_id")
                    if project_id:
                        file_count = len([
                            f for f in project_dir.rglob('*')
                            if f.is_file() and f.name not in ['project_metadata.json', 'README_INSTRUCTIONS.md']
                        ])

                        project_info = {
                            "project_id": project_id,
                            "project_name": metadata.get("project_name", project_dir.name),
                            "created_at": metadata.get("created_at", datetime.now().isoformat()),
                            "file_count": file_count,
                            "instructions": metadata.get("instructions", "No instructions available"),
                            "source": "directory_scan",
                            "directory_path": str(project_dir.relative_to(PROJECTS_DIR))
                        }

                        all_projects.append(project_info)

            except Exception as e:
                print(f"Error processing directory {project_dir.name}: {e}")
                continue

        return {"projects": all_projects}

    except Exception as e:
        print(f"Error scanning projects directory: {e}")
        raise Exception(f"Failed to scan projects directory: {str(e)}")


# ---------------------------------------------------------------------------
# Chat history (DB)
# ---------------------------------------------------------------------------

def save_chat_message_to_db(user_id: int, project_id: str, project_name: str,
                             message: str, sender: str, message_type: str = 'text',
                             metadata: dict = None):
    """Save a chat message to database"""
    try:
        from database import get_db_connection

        connection = get_db_connection()
        if not connection:
            return False

        cursor = connection.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute("""
            INSERT INTO code_assistant_history
            (user_id, project_id, project_name, message, sender, message_type, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, project_id, project_name, message, sender, message_type, metadata_json))

        connection.commit()
        cursor.close()
        connection.close()

        return True

    except Exception as e:
        print(f"[ERROR] Failed to save chat message: {e}")
        return False


async def get_chat_history_from_db(user_id: int, project_id: str, limit: int = 50):
    """Get chat history for a project"""
    try:
        from database import get_db_connection

        connection = get_db_connection()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, message, sender, message_type, metadata, created_at, project_id
            FROM code_assistant_history
            WHERE user_id = %s AND project_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, project_id, limit))

        messages = cursor.fetchall()

        for msg in messages:
            if msg['metadata']:
                try:
                    msg['metadata'] = json.loads(msg['metadata'])
                except Exception:
                    msg['metadata'] = {}
            msg['timestamp'] = msg['created_at'].isoformat()

        cursor.close()
        connection.close()

        return list(reversed(messages))

    except Exception as e:
        print(f"[ERROR] Failed to get chat history: {e}")
        return []


# ---------------------------------------------------------------------------
# File upload analysis
# ---------------------------------------------------------------------------

async def analyze_uploaded_files(files: List[UploadFile]) -> dict:
    """Analyze uploaded files and extract their content"""

    file_contents = {}
    file_tree = []
    total_size = 0

    for file in files:
        content = await file.read()
        total_size += len(content)

        await file.seek(0)

        mime_type, _ = mimetypes.guess_type(file.filename)
        is_text = (mime_type and mime_type.startswith('text/')) or file.filename.endswith(
            ('.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml', '.xml', '.sql')
        )

        if is_text:
            try:
                text_content = content.decode('utf-8')
                file_contents[file.filename] = {
                    'content': text_content,
                    'size': len(content),
                    'type': 'text',
                    'mime_type': mime_type
                }
            except UnicodeDecodeError:
                file_contents[file.filename] = {
                    'content': f"[Binary file - {len(content)} bytes]",
                    'size': len(content),
                    'type': 'binary',
                    'mime_type': mime_type
                }
        else:
            file_contents[file.filename] = {
                'content': f"[Binary file - {len(content)} bytes]",
                'size': len(content),
                'type': 'binary',
                'mime_type': mime_type
            }

        file_tree.append({
            'name': file.filename,
            'size': len(content),
            'type': 'binary' if not is_text else 'text'
        })

    return {
        'files': file_contents,
        'tree': file_tree,
        'total_files': len(files),
        'total_size': total_size
    }


async def process_zip_file(zip_file: UploadFile) -> dict:
    """Process uploaded ZIP file and extract contents"""

    file_contents = {}
    file_tree = []

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        content = await zip_file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        with zipfile.ZipFile(tmp_file_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if file_info.is_dir():
                    continue

                file_path = file_info.filename
                file_content = zip_ref.read(file_path)

                mime_type, _ = mimetypes.guess_type(file_path)
                is_text = (mime_type and mime_type.startswith('text/')) or file_path.endswith(
                    ('.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml', '.xml', '.sql')
                )

                if is_text:
                    try:
                        text_content = file_content.decode('utf-8')
                        file_contents[file_path] = {
                            'content': text_content,
                            'size': len(file_content),
                            'type': 'text',
                            'mime_type': mime_type
                        }
                    except UnicodeDecodeError:
                        file_contents[file_path] = {
                            'content': f"[Binary file - {len(file_content)} bytes]",
                            'size': len(file_content),
                            'type': 'binary',
                            'mime_type': mime_type
                        }
                else:
                    file_contents[file_path] = {
                        'content': f"[Binary file - {len(file_content)} bytes]",
                        'size': len(file_content),
                        'type': 'binary',
                        'mime_type': mime_type
                    }

                file_tree.append({
                    'name': file_path,
                    'size': len(file_content),
                    'type': 'binary' if not is_text else 'text'
                })

    finally:
        os.unlink(tmp_file_path)

    return {
        'files': file_contents,
        'tree': file_tree,
        'total_files': len(file_contents),
        'total_size': sum(f['size'] for f in file_contents.values())
    }
