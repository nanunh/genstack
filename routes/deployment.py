from fastapi import APIRouter, HTTPException

from store import projects_store
from services.ssh_deployment import ssh_deployment_manager, execute_deployment_mcp_tool

router = APIRouter()


@router.post("/api/projects/{project_id}/deploy")
async def deploy_project_with_ssh(project_id: str, deployment_config: dict = None):
    """Deploy project to remote server using MCP tools"""
    try:
        print(f"[DEBUG] Deploy button clicked for project: {project_id}")

        if project_id not in projects_store:
            raise HTTPException(status_code=404, detail="Project not found")

        project = projects_store[project_id]
        print(f"[DEPLOY] Starting MCP deployment for project: {project.project_name}")

        if not deployment_config:
            return {
                "status": "config_required",
                "message": "SSH configuration required for deployment",
                "project_id": project_id,
                "project_name": project.project_name,
                "config_form": {
                    "ssh_host": {"type": "string", "required": True, "label": "Server IP/Hostname"},
                    "ssh_username": {"type": "string", "required": True, "label": "SSH Username"},
                    "ssh_password": {"type": "password", "required": True, "label": "SSH Password"},
                    "ssh_port": {"type": "number", "default": 22, "label": "SSH Port"},
                    "remote_path": {"type": "string", "default": "/var/www/deployments", "label": "Deployment Path"},
                    "port": {"type": "number", "default": 8000, "label": "Application Port"},
                    "auto_install_deps": {"type": "boolean", "default": True, "label": "Auto Install Dependencies"},
                    "start_service": {"type": "boolean", "default": True, "label": "Start as Service"}
                }
            }

        mcp_params = {
            "project_id": project_id,
            **deployment_config
        }

        deployment_result = await execute_deployment_mcp_tool("deploy_to_server", mcp_params)

        if deployment_result["type"] == "deployment_completed":
            result = deployment_result["result"]
            if result["status"] == "success":
                return {
                    "status": "deployed",
                    "message": f"Project '{project.project_name}' deployed successfully",
                    "project_id": project_id,
                    "deployment_url": result["deployment_url"],
                    "service_status": result["service_status"],
                    "deployment_id": result["deployment_id"],
                    "deployment_logs": result["logs"]
                }
            else:
                return {
                    "status": "failed",
                    "message": result["error"],
                    "deployment_logs": result.get("logs", [])
                }
        else:
            return {
                "status": "failed",
                "message": deployment_result["error"]
            }

    except Exception as e:
        print(f"[ERROR] Deployment API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/projects/{project_id}/deploy/ssh")
async def deploy_project_ssh_config(project_id: str, config: dict):
    """Deploy project with SSH configuration"""
    return await deploy_project_with_ssh(project_id, config)


@router.post("/api/test-ssh-connection")
async def test_ssh_connection_endpoint(ssh_config: dict):
    """Test SSH connection using sshpass before deployment"""
    try:
        result = ssh_deployment_manager.test_ssh_connection_sshpass(ssh_config)
        return result
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }
