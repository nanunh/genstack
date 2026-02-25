import os
import json
import time
import subprocess
import tempfile
import zipfile
from typing import Dict, Any, Optional

from store import projects_store


class SSHDeploymentManager:
    """Manages SSH-based project deployments using sshpass"""

    def __init__(self):
        self.deployment_logs: Dict[str, list] = {}

    # ------------------------------------------------------------------
    # Archive helpers
    # ------------------------------------------------------------------

    def create_project_archive(self, project, use_pm2: bool = True) -> str:
        """Create a ZIP archive of the project for deployment"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_path = tmp_file.name

        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_obj in project.files:
                zf.writestr(file_obj.path, file_obj.content)

            deploy_script = self.generate_deployment_script(project, use_pm2)
            zf.writestr("deploy.sh", deploy_script)

            if use_pm2:
                ecosystem_config = self.generate_pm2_ecosystem(project)
                zf.writestr("ecosystem.config.js", ecosystem_config)

        return tmp_path

    def generate_pm2_ecosystem(self, project) -> str:
        """Generate PM2 ecosystem.config.js"""
        has_package_json = any(f.path == "package.json" for f in project.files)

        if has_package_json:
            main_script = "index.js"
            for f in project.files:
                if f.path in ["index.js", "server.js", "app.js", "main.js"]:
                    main_script = f.path
                    break
        else:
            main_script = self.detect_main_python_file(project)

        ecosystem_config = {
            "apps": [{
                "name": project.project_name,
                "script": main_script,
                "cwd": f"/var/www/deployments/{project.project_name}",
                "instances": 1,
                "autorestart": True,
                "watch": False,
                "max_memory_restart": "1G",
                "env": {
                    "NODE_ENV": "production",
                    "PORT": 8000
                },
                "error_file": f"/var/log/pm2/{project.project_name}-error.log",
                "out_file": f"/var/log/pm2/{project.project_name}-out.log",
                "log_file": f"/var/log/pm2/{project.project_name}.log"
            }]
        }

        return json.dumps(ecosystem_config, indent=2)

    def generate_deployment_script(self, project, use_pm2: bool = True) -> str:
        """Generate deployment script based on project type with PM2 support"""

        has_package_json = any(f.path == "package.json" for f in project.files)
        has_requirements_txt = any(f.path == "requirements.txt" for f in project.files)
        has_main_py = any(f.path in ["main.py", "app.py"] for f in project.files)

        script_parts = [
            "#!/bin/bash",
            "set -e",
            "",
            f"# Deployment script for {project.project_name}",
            f"PROJECT_NAME='{project.project_name}'",
            "DEPLOY_DIR=$(pwd)",
            "",
            "echo 'Starting deployment process...'",
            ""
        ]

        if has_package_json and use_pm2:
            script_parts.extend([
                "# Install Node.js dependencies",
                "if command -v npm &> /dev/null; then",
                "    echo 'Installing dependencies with npm...'",
                "    npm install --production",
                "elif command -v yarn &> /dev/null; then",
                "    echo 'Installing dependencies with yarn...'",
                "    yarn install --production",
                "else",
                "    echo 'Error: npm or yarn not found'",
                "    exit 1",
                "fi",
                "",
                "# Install PM2 globally if not present",
                "if ! command -v pm2 &> /dev/null; then",
                "    echo 'Installing PM2...'",
                "    npm install -g pm2",
                "fi",
                "",
                "# Create PM2 log directory",
                "sudo mkdir -p /var/log/pm2",
                "sudo chown $USER:$USER /var/log/pm2",
                "",
                "# Stop existing PM2 process if running",
                "pm2 stop $PROJECT_NAME 2>/dev/null || true",
                "pm2 delete $PROJECT_NAME 2>/dev/null || true",
                "",
                "# Start application with PM2",
                "echo 'Starting application with PM2...'",
                "pm2 start ecosystem.config.js",
                "pm2 startup",
                "pm2 save",
                "",
                "# Show PM2 status",
                "pm2 status",
                ""
            ])
        elif has_package_json:
            script_parts.extend([
                "# Install Node.js dependencies",
                "npm install --production",
                ""
            ])
        elif has_requirements_txt:
            script_parts.extend([
                "# Install Python dependencies",
                "pip install -r requirements.txt",
                ""
            ])

        script_parts.extend([
            "# Setup firewall (if ufw is available)",
            "if command -v ufw &> /dev/null; then",
            "    echo 'Configuring firewall...'",
            f"    sudo ufw allow 8000/tcp",
            "fi",
            "",
            "# Make script executable",
            "chmod +x deploy.sh",
            "",
            "echo 'Deployment preparation completed!'",
            "echo 'Project deployed to: '$DEPLOY_DIR",
        ])

        return "\n".join(script_parts)

    def generate_systemd_service(self, project) -> str:
        """Generate systemd service file for the project"""

        has_package_json = any(f.path == "package.json" for f in project.files)
        has_main_py = any(f.path == "main.py" for f in project.files)
        has_app_py = any(f.path == "app.py" for f in project.files)

        if has_package_json:
            exec_start = "npm start"
            working_dir = f"/var/www/deployments/{project.project_name}"
        elif has_main_py:
            exec_start = f"/var/www/deployments/{project.project_name}/venv/bin/python main.py"
            working_dir = f"/var/www/deployments/{project.project_name}"
        elif has_app_py:
            exec_start = f"/var/www/deployments/{project.project_name}/venv/bin/python app.py"
            working_dir = f"/var/www/deployments/{project.project_name}"
        else:
            exec_start = "echo 'No start command detected'"
            working_dir = f"/var/www/deployments/{project.project_name}"

        return f"""[Unit]
Description={project.project_name} Web Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={working_dir}
ExecStart={exec_start}
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
"""

    # ------------------------------------------------------------------
    # sshpass helpers
    # ------------------------------------------------------------------

    def check_sshpass_installed(self) -> bool:
        """Check if sshpass is installed on the system"""
        try:
            result = subprocess.run(['which', 'sshpass'], capture_output=True, text=True)
            if result.returncode == 0:
                print("[DEBUG] sshpass found:", result.stdout.strip())
                return True
            else:
                print("[ERROR] sshpass not found. Install with: sudo apt-get install sshpass")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to check sshpass: {e}")
            return False

    def execute_ssh_command_sshpass(self, ssh_config: Dict[str, Any], command: str, timeout: int = 60) -> str:
        """Execute SSH command using sshpass"""
        try:
            ssh_host = ssh_config['ssh_host']
            ssh_port = ssh_config.get('ssh_port', 22)
            ssh_username = ssh_config['ssh_username']
            ssh_password = ssh_config['ssh_password']

            ssh_cmd = [
                'sshpass', '-p', ssh_password,
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=ERROR',
                '-p', str(ssh_port),
                f'{ssh_username}@{ssh_host}',
                command
            ]

            print(f"[DEBUG] Executing SSH command: {ssh_username}@{ssh_host}")

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise Exception(f"SSH command failed (exit code {result.returncode}): {error_msg}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise Exception(f"SSH command timed out after {timeout} seconds")
        except Exception as e:
            raise Exception(f"SSH command execution failed: {str(e)}")

    def transfer_file_sshpass(self, ssh_config: Dict[str, Any], local_path: str, remote_path: str) -> None:
        """Transfer file using scp with sshpass"""
        try:
            ssh_host = ssh_config['ssh_host']
            ssh_port = ssh_config.get('ssh_port', 22)
            ssh_username = ssh_config['ssh_username']
            ssh_password = ssh_config['ssh_password']

            scp_cmd = [
                'sshpass', '-p', ssh_password,
                'scp',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=ERROR',
                '-P', str(ssh_port),
                local_path,
                f'{ssh_username}@{ssh_host}:{remote_path}'
            ]

            print(f"[DEBUG] Transferring file: {local_path} -> {ssh_username}@{ssh_host}:{remote_path}")

            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise Exception(f"File transfer failed (exit code {result.returncode}): {error_msg}")

            print(f"[DEBUG] File transfer successful")

        except subprocess.TimeoutExpired:
            raise Exception("File transfer timed out after 3 minutes")
        except Exception as e:
            raise Exception(f"File transfer failed: {str(e)}")

    def test_ssh_connection_sshpass(self, ssh_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SSH connection using sshpass"""
        try:
            if not self.check_sshpass_installed():
                return {
                    "status": "failed",
                    "error": "sshpass not installed. Run: sudo apt-get install sshpass"
                }

            print(f"[DEBUG] Testing SSH connection to {ssh_config['ssh_username']}@{ssh_config['ssh_host']}...")

            test_output = self.execute_ssh_command_sshpass(ssh_config, 'echo "SSH connection successful"', timeout=30)
            whoami_output = self.execute_ssh_command_sshpass(ssh_config, 'whoami', timeout=10)
            pwd_output = self.execute_ssh_command_sshpass(ssh_config, 'pwd', timeout=10)
            uname_output = self.execute_ssh_command_sshpass(ssh_config, 'uname -a', timeout=10)

            return {
                "status": "success",
                "message": "SSH connection test successful",
                "test_output": test_output.strip(),
                "user": whoami_output.strip(),
                "pwd": pwd_output.strip(),
                "system": uname_output.strip()
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def check_server_status(self, ssh_config: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """Check if deployed application is running using sshpass"""
        try:
            try:
                status_output = self.execute_ssh_command_sshpass(
                    ssh_config,
                    f"sudo systemctl status {project_name}",
                    timeout=15
                )
                is_active = "active (running)" in status_output
            except Exception:
                is_active = False

            pm2_active = False
            try:
                pm2_output = self.execute_ssh_command_sshpass(
                    ssh_config,
                    f"pm2 show {project_name}",
                    timeout=10
                )
                pm2_active = "online" in pm2_output.lower()
            except Exception:
                pm2_active = False

            app_port = ssh_config.get('app_port', 8000)
            try:
                port_check = self.execute_ssh_command_sshpass(
                    ssh_config,
                    f"netstat -tlnp | grep :{app_port}",
                    timeout=10
                )
                port_open = bool(port_check.strip())
            except Exception:
                port_open = False

            overall_active = is_active or pm2_active
            status = "running" if overall_active and port_open else "stopped"

            return {
                "status": status,
                "service_active": is_active,
                "pm2_active": pm2_active,
                "port_open": port_open,
                "port": app_port,
                "url": f"http://{ssh_config['ssh_host']}:{app_port}" if overall_active and port_open else None
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def stop_deployment(self, ssh_config: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """Stop a deployed application using sshpass"""
        try:
            stopped_services = []

            try:
                self.execute_ssh_command_sshpass(ssh_config, f"sudo systemctl stop {project_name}")
                self.execute_ssh_command_sshpass(ssh_config, f"sudo systemctl disable {project_name}")
                stopped_services.append("systemctl")
            except Exception as e:
                print(f"[DEBUG] Could not stop systemctl service: {e}")

            try:
                self.execute_ssh_command_sshpass(ssh_config, f"pm2 stop {project_name}")
                self.execute_ssh_command_sshpass(ssh_config, f"pm2 delete {project_name}")
                stopped_services.append("PM2")
            except Exception as e:
                print(f"[DEBUG] Could not stop PM2 process: {e}")

            return {
                "status": "success",
                "stopped_services": stopped_services,
                "project_name": project_name
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def create_pm2_config_for_python(self, project, project_path: str) -> str:
        """Create PM2 ecosystem config for Python projects"""

        python_file = self.detect_main_python_file(project)

        config = f'''module.exports = {{
        apps: [{{
            name: "{project.project_name}",
            script: "{python_file}",
            cwd: "{project_path}",
            interpreter: "python3",
            instances: 1,
            autorestart: true,
            watch: false,
            max_memory_restart: "1G",
            env: {{
            PORT: 8000,
            FLASK_ENV: "production"
            }},
            error_file: "/var/log/pm2/{project.project_name}-error.log",
            out_file: "/var/log/pm2/{project.project_name}-out.log",
            log_file: "/var/log/pm2/{project.project_name}.log"
        }}]
        }};'''

        return config

    def detect_main_python_file(self, project) -> str:
        """Detect the main Python file to run"""

        priority_files = ['app.py', 'main.py', 'server.py', 'run.py']

        for priority_file in priority_files:
            if any(f.path == priority_file for f in project.files):
                return priority_file

        for file in project.files:
            if file.path.endswith('.py') and ('flask' in file.content.lower() and 'app.run' in file.content.lower()):
                return file.path

        for file in project.files:
            if file.path.endswith('.py'):
                return file.path

        return 'app.py'

    # ------------------------------------------------------------------
    # Main deployment method
    # ------------------------------------------------------------------

    def deploy_to_server_sshpass(self, project_id: str, ssh_config: Dict[str, Any]) -> Dict[str, Any]:
        """Main deployment method using sshpass"""

        deployment_id = f"{project_id}_{int(time.time())}"

        try:
            if not self.check_sshpass_installed():
                return {
                    "status": "error",
                    "error": "sshpass not installed. Install with: sudo apt-get install sshpass",
                    "deployment_id": deployment_id
                }

            if project_id not in projects_store:
                raise Exception(f"Project {project_id} not found")

            project = projects_store[project_id]
            use_pm2 = ssh_config.get('use_pm2', True)

            self.deployment_logs[deployment_id] = []
            self.log_deployment(deployment_id, "Starting sshpass-based deployment...")

            self.log_deployment(deployment_id, f"Testing SSH connection to {ssh_config['ssh_host']}...")
            test_result = self.test_ssh_connection_sshpass(ssh_config)

            if test_result["status"] != "success":
                raise Exception(f"SSH connection test failed: {test_result['error']}")

            self.log_deployment(deployment_id, f"SSH connection successful - User: {test_result['user']}")

            self.log_deployment(deployment_id, "Creating project archive...")
            zip_path = self.create_project_archive(project, use_pm2)

            remote_path = ssh_config.get('remote_path', '/var/www/deployments')
            project_remote_path = f"{remote_path}/{project.project_name}"

            self.log_deployment(deployment_id, f"Creating remote directory: {project_remote_path}")
            self.execute_ssh_command_sshpass(ssh_config, f"mkdir -p {project_remote_path}")

            self.log_deployment(deployment_id, "Transferring project files...")
            remote_zip_path = f"{project_remote_path}/{project.project_name}.zip"
            self.transfer_file_sshpass(ssh_config, zip_path, remote_zip_path)

            self.log_deployment(deployment_id, "Extracting files on remote server...")
            extract_commands = [
                f"cd {project_remote_path}",
                f"unzip -o {project.project_name}.zip",
                f"rm {project.project_name}.zip",
                "chmod +x deploy.sh"
            ]

            combined_extract_cmd = " && ".join(extract_commands)
            self.execute_ssh_command_sshpass(ssh_config, combined_extract_cmd)

            if ssh_config.get('auto_install_deps', True):
                self.log_deployment(deployment_id, "Installing dependencies...")
                deploy_output = self.execute_ssh_command_sshpass(
                    ssh_config,
                    f"cd {project_remote_path} && ./deploy.sh",
                    timeout=300
                )
                self.log_deployment(deployment_id, f"Deploy script output: {deploy_output[:200]}...")

            process_manager = "none"
            service_status = "unknown"

            if ssh_config.get('start_service', True):
                use_pm2 = ssh_config.get('use_pm2', True)

                has_package_json = any(f.path == "package.json" for f in project.files)
                has_python_files = any(f.path.endswith('.py') for f in project.files)
                has_flask = any('flask' in f.content.lower() for f in project.files if f.path.endswith('.py'))

                if use_pm2:
                    self.log_deployment(deployment_id, "Force using PM2 as requested...")

                    try:
                        self.log_deployment(deployment_id, "Installing/checking PM2...")
                        self.execute_ssh_command_sshpass(
                            ssh_config,
                            "npm install -g pm2 || echo 'PM2 installation attempted'",
                            timeout=60
                        )
                    except Exception as e:
                        self.log_deployment(deployment_id, f"PM2 install warning: {e}")

                    if has_flask or has_python_files:
                        pm2_config = self.create_pm2_config_for_python(project, project_remote_path)
                        ecosystem_cmd = f"cd {project_remote_path} && cat > ecosystem.config.js << 'EOF'\n{pm2_config}\nEOF"
                        self.execute_ssh_command_sshpass(ssh_config, ecosystem_cmd, timeout=30)
                        self.log_deployment(deployment_id, "Created PM2 config for Python project")

                    try:
                        self.execute_ssh_command_sshpass(
                            ssh_config,
                            f"pm2 stop {project.project_name} 2>/dev/null || true",
                            timeout=15
                        )
                        self.execute_ssh_command_sshpass(
                            ssh_config,
                            f"pm2 delete {project.project_name} 2>/dev/null || true",
                            timeout=15
                        )
                    except Exception:
                        pass

                    self.log_deployment(deployment_id, "Starting with PM2...")
                    pm2_output = self.execute_ssh_command_sshpass(
                        ssh_config,
                        f"cd {project_remote_path} && pm2 start ecosystem.config.js && pm2 save",
                        timeout=60
                    )
                    self.log_deployment(deployment_id, f"PM2 output: {pm2_output[:200]}")
                    process_manager = "pm2"
                    service_status = "started"

            app_port = ssh_config.get('port', ssh_config.get('app_port', 8000))
            try:
                port_check = self.execute_ssh_command_sshpass(
                    ssh_config,
                    f"netstat -tlnp | grep :{app_port}",
                    timeout=10
                )
                port_open = bool(port_check.strip())
            except Exception:
                port_open = False

            if os.path.exists(zip_path):
                os.unlink(zip_path)

            deployment_url = f"http://{ssh_config['ssh_host']}:{app_port}"

            self.log_deployment(deployment_id, f"Deployment completed using {process_manager}!")
            self.log_deployment(deployment_id, f"Service status: {service_status}")
            self.log_deployment(deployment_id, f"Port {app_port} open: {port_open}")
            self.log_deployment(deployment_id, f"Application URL: {deployment_url}")

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "deployment_url": deployment_url,
                "service_status": service_status,
                "port_open": port_open,
                "process_manager": process_manager,
                "project_path": project_remote_path,
                "logs": self.deployment_logs[deployment_id]
            }

        except Exception as e:
            error_msg = f"sshpass deployment failed: {str(e)}"
            self.log_deployment(deployment_id, f"ERROR: {error_msg}")

            return {
                "status": "error",
                "error": error_msg,
                "deployment_id": deployment_id,
                "logs": self.deployment_logs.get(deployment_id, [])
            }

    def log_deployment(self, deployment_id: str, message: str):
        """Log deployment progress"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        if deployment_id not in self.deployment_logs:
            self.deployment_logs[deployment_id] = []

        self.deployment_logs[deployment_id].append(log_entry)
        print(f"[DEPLOY] {log_entry}")


# Module-level singleton
ssh_deployment_manager = SSHDeploymentManager()


# ---------------------------------------------------------------------------
# Deployment MCP tool executor
# ---------------------------------------------------------------------------

async def execute_deployment_mcp_tool(tool_name: str, parameters: dict) -> dict:
    """Execute deployment-specific MCP tools using sshpass"""

    if tool_name == "deploy_to_server":
        try:
            project_id = parameters["project_id"]
            ssh_config = {
                'ssh_host': parameters["ssh_host"],
                'ssh_port': parameters.get("ssh_port", 22),
                'ssh_username': parameters["ssh_username"],
                'ssh_password': parameters["ssh_password"],
                'remote_path': parameters.get("remote_path", "/var/www/deployments"),
                'port': parameters.get("port", 8000),
                'auto_install_deps': parameters.get("auto_install_deps", True),
                'start_service': parameters.get("start_service", True),
                'use_pm2': parameters.get("use_pm2", True)
            }

            print(f"[MCP] Executing sshpass deployment for project {project_id}")
            print(f"[MCP] Target server: {ssh_config['ssh_username']}@{ssh_config['ssh_host']}:{ssh_config['ssh_port']}")

            result = ssh_deployment_manager.deploy_to_server_sshpass(project_id, ssh_config)

            return {
                "type": "deployment_completed",
                "result": result,
                "tool": "deploy_to_server",
                "project_id": project_id
            }

        except Exception as e:
            print(f"[MCP] sshpass deployment failed: {e}")
            return {
                "type": "deployment_failed",
                "error": str(e),
                "tool": "deploy_to_server",
                "project_id": parameters.get("project_id", "unknown")
            }

    elif tool_name == "check_server_status":
        try:
            ssh_config = {
                'ssh_host': parameters["ssh_host"],
                'ssh_port': parameters.get("ssh_port", 22),
                'ssh_username': parameters["ssh_username"],
                'ssh_password': parameters["ssh_password"],
                'app_port': parameters.get("app_port", 8000)
            }

            project_name = parameters["project_name"]

            print(f"[MCP] Checking server status for {project_name} using sshpass")
            result = ssh_deployment_manager.check_server_status(ssh_config, project_name)

            return {
                "type": "status_checked",
                "result": result,
                "tool": "check_server_status",
                "project_name": project_name
            }

        except Exception as e:
            return {
                "type": "status_check_failed",
                "error": str(e),
                "tool": "check_server_status"
            }

    elif tool_name == "stop_deployment":
        try:
            ssh_config = {
                'ssh_host': parameters["ssh_host"],
                'ssh_port': parameters.get("ssh_port", 22),
                'ssh_username': parameters["ssh_username"],
                'ssh_password': parameters["ssh_password"]
            }

            project_name = parameters["project_name"]

            print(f"[MCP] Stopping deployment for {project_name} using sshpass")
            result = ssh_deployment_manager.stop_deployment(ssh_config, project_name)

            return {
                "type": "deployment_stopped",
                "result": result,
                "tool": "stop_deployment"
            }

        except Exception as e:
            return {
                "type": "stop_failed",
                "error": str(e),
                "tool": "stop_deployment"
            }

    else:
        return {"type": "error", "error": f"Unknown deployment tool: {tool_name}"}
