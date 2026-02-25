import os
import json
import signal
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from models import FileContent
from store import projects_store, running_processes, PROJECTS_DIR


# ---------------------------------------------------------------------------
# Package / README helpers
# ---------------------------------------------------------------------------

def generate_package_json(project_name: str, dependencies: List[str]) -> str:
    """Generate package.json with dynamic dependencies"""
    deps_obj = {}
    for dep in dependencies:
        if "@" in dep:
            name, version = dep.rsplit("@", 1)
            deps_obj[name] = version
        else:
            deps_obj[dep] = "latest"

    package_data = {
        "name": project_name.lower().replace("_", "-"),
        "version": "1.0.0",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": deps_obj
    }

    return json.dumps(package_data, indent=2)


def generate_readme(project_name: str, prompt: str) -> str:
    """Generate a README.md file"""
    return f"""# {project_name}

{prompt}

## Description
This project was generated using MCP (Model Context Protocol) tools for structured development.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd {project_name}

# Install dependencies
pip install -r requirements.txt
# or for Node.js projects: npm install
```

## Usage

```bash
# Run the application
python main.py
# or: python app.py
# or for React: npm start
```

## Project Structure

This project follows best practices and includes:
- Main application files
- Configuration files
- Dependencies management
- Development tools setup

## Development

1. Make sure all dependencies are installed
2. Run the application in development mode
3. Make your changes
4. Test thoroughly before deploying

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Generated with MCP tools for enhanced development workflow.
"""


# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------

async def install_dependencies(project_dir: Path, files: List[FileContent]) -> bool:
    """Install project dependencies"""

    try:
        if any(f.path == "package.json" for f in files):
            print(f"[DEBUG] Installing npm dependencies in {project_dir}")
            result = subprocess.run(
                ["npm", "install"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"[DEBUG] npm install failed: {result.stderr}")
                return False

            print(f"[DEBUG] npm install completed successfully")
            return True

        elif any(f.path == "requirements.txt" for f in files):
            print(f"[DEBUG] Installing Python dependencies in {project_dir}")
            result = subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"[DEBUG] pip install failed: {result.stderr}")
                return False

            print(f"[DEBUG] pip install completed successfully")
            return True

        return True

    except subprocess.TimeoutExpired:
        print(f"[DEBUG] Dependency installation timed out")
        return False
    except Exception as e:
        print(f"[DEBUG] Dependency installation error: {e}")
        return False


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------

def detect_project_url(files: List[FileContent]) -> str:
    """Detect the likely URL where the project will run"""

    if any("vite" in f.content.lower() for f in files if f.path == "package.json"):
        return "http://localhost:5173"
    elif any("react-scripts" in f.content.lower() for f in files if f.path == "package.json"):
        return "http://localhost:3000"
    elif any("flask" in f.content.lower() for f in files):
        return "http://localhost:5000"
    elif any("fastapi" in f.content.lower() for f in files):
        return "http://localhost:8000"

    return "http://localhost:3000"


# ---------------------------------------------------------------------------
# Project execution
# ---------------------------------------------------------------------------

async def execute_project(project_id: str, run_command: str = None) -> dict:
    """Execute a generated project"""

    if project_id not in projects_store:
        raise ValueError(f"Project {project_id} not found")

    project = projects_store[project_id]
    project_dir = PROJECTS_DIR / f"{project.project_name}_{project.project_id[:8]}"

    if not project_dir.exists():
        raise ValueError(f"Project directory not found: {project_dir}")

    if not run_command:
        if (project_dir / "package.json").exists():
            if any("vite" in f.content.lower() for f in project.files if f.path == "package.json"):
                run_command = "npm run dev"
            else:
                run_command = "npm start"
        elif (project_dir / "requirements.txt").exists():
            if any(f.path in ["main.py", "app.py"] for f in project.files):
                main_file = "main.py" if any(f.path == "main.py" for f in project.files) else "app.py"
                run_command = f"python3 {main_file}"
            else:
                run_command = "python3 -m flask run"
        else:
            run_command = "echo 'No run command detected'"

    try:
        install_success = await install_dependencies(project_dir, project.files)

        if not install_success:
            return {
                "status": "error",
                "message": "Failed to install dependencies",
                "project_id": project_id
            }

        if project_id in running_processes:
            await stop_project(project_id)

        print(f"[DEBUG] Running command: {run_command} in {project_dir}")

        process = subprocess.Popen(
            run_command,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        running_processes[project_id] = {
            "process": process,
            "command": run_command,
            "start_time": datetime.now(),
            "project_name": project.project_name
        }

        await asyncio.sleep(2)

        if process.poll() is None:
            return {
                "status": "running",
                "message": "Project started successfully",
                "project_id": project_id,
                "command": run_command,
                "pid": process.pid,
                "url": detect_project_url(project.files)
            }
        else:
            stdout, stderr = process.communicate()
            return {
                "status": "error",
                "message": f"Process failed to start: {stderr or stdout}",
                "project_id": project_id
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to execute project: {str(e)}",
            "project_id": project_id
        }


async def stop_project(project_id: str) -> dict:
    """Stop a running project"""

    if project_id not in running_processes:
        return {"status": "error", "message": "Project not running"}

    process_info = running_processes[project_id]
    process = process_info["process"]

    try:
        if os.name != 'nt':
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        else:
            process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()

        del running_processes[project_id]

        return {
            "status": "stopped",
            "message": f"Project {process_info['project_name']} stopped successfully",
            "project_id": project_id
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop project: {str(e)}",
            "project_id": project_id
        }


def get_running_projects() -> dict:
    """Get status of all running projects"""

    active_processes = {}

    for project_id, info in running_processes.copy().items():
        process = info["process"]

        if process.poll() is None:
            active_processes[project_id] = {
                "project_name": info["project_name"],
                "command": info["command"],
                "start_time": info["start_time"].isoformat(),
                "pid": process.pid,
                "status": "running"
            }
        else:
            del running_processes[project_id]

    return active_processes
