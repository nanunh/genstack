import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from store import projects_store, running_processes, PROJECTS_DIR
from utils.file_ops import scan_projects_directory, load_project_from_filesystem
from utils.project_runner import stop_project
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.token_usage import router as token_router
from routes.deployment import router as deployment_router


# ---------------------------------------------------------------------------
# Startup helper
# ---------------------------------------------------------------------------

async def preload_recent_projects():
    """Load recent projects from filesystem into store on startup"""
    try:
        print("[DEBUG] Preloading recent projects from filesystem...")

        scan_response = await scan_projects_directory()
        directory_projects = scan_response.get("projects", [])

        recent_projects = sorted(
            directory_projects,
            key=lambda x: x["created_at"],
            reverse=True
        )[:10]

        loaded_count = 0
        for project_info in recent_projects:
            project_id = project_info["project_id"]

            if project_id in projects_store:
                continue

            project_dir_name = project_info.get("directory_path")
            if project_dir_name:
                project_dir = PROJECTS_DIR / project_dir_name
                if project_dir.exists():
                    result = await load_project_from_filesystem(project_id, project_dir)
                    if result:
                        loaded_count += 1
                        print(f"[DEBUG] Preloaded project: {result.project_name}")

        print(f"[DEBUG] Preloaded {loaded_count} projects from filesystem")

    except Exception as e:
        print(f"[DEBUG] Error preloading projects: {e}")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Enhanced MCP Project Generator with Intelligent Code Assistant...")

    await preload_recent_projects()

    from services.mcp_tools import MCP_TOOLS
    from store import ANTHROPIC_API_KEY

    print(f"Projects in store: {len(projects_store)}")
    print(f"MCP tools available: {len(MCP_TOOLS)}")

    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY not configured!")

    print("Features enabled:")
    print("  - Intelligent natural language code modification")
    print("  - Multi-file project generation")
    print("  - AST-powered code analysis")
    print("  - Automatic backup creation")
    print("  - Real-time project execution")
    print("  - File-based project improvement")

    yield  # Server runs here

    # Shutdown
    print("Shutting down Enhanced MCP Project Generator...")

    for project_id in list(running_processes.keys()):
        try:
            await stop_project(project_id)
            print(f"Stopped project: {project_id}")
        except Exception as e:
            print(f"Error stopping project {project_id}: {e}")

    print("Shutdown complete")


# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Enhanced MCP Project Generator with Intelligent Code Assistant",
    description="Generate and modify projects using MCP tools with intelligent natural language processing",
    version="2.0.0",
    lifespan=lifespan
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(token_router)
app.include_router(deployment_router)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Resource not found",
            "available_endpoints": [
                "/",
                "/health",
                "/api/projects",
                "/api/generate",
                "/api/generate/files",
                "/mcp/info",
                "/mcp/tools"
            ]
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "Please check server logs for details",
            "timestamp": datetime.now().isoformat()
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    import sys

    ssl_keyfile = "keys/privkey.pem"
    ssl_certfile = "keys/fullchain.pem"

    if not os.path.exists(ssl_keyfile):
        print(f"SSL key file not found: {ssl_keyfile}")
        print("Please ensure your certificate files are in the 'keys' folder")
        exit(1)

    if not os.path.exists(ssl_certfile):
        print(f"SSL certificate file not found: {ssl_certfile}")
        print("Please ensure your certificate files are in the 'keys' folder")
        exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "web"

    if mode == "--enhanced":
        print("Starting Enhanced MCP Project Generator Server...")
        print("Web interface: http://localhost:8000")
        print("Enhanced Code Assistant: http://localhost:8000/api/projects/{project_id}/enhanced-code-assistant")
        print("MCP endpoints: http://localhost:8000/mcp/*")
        print("Health check: http://localhost:8000/health")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=443,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            reload=False,
            log_level="info"
        )
    else:
        print("Starting Enhanced MCP Project Generator Server...")
        print("Web interface: http://localhost:8000")
        print("Enhanced features enabled by default")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            reload=False,
            log_level="info"
        )
