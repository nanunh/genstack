// Same JS as before but with updated messaging
(function checkAuthentication() {
    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    
    if (!token && !window.location.pathname.includes('login.html') && !window.location.pathname.includes('signup.html')) {
        window.location.href = '/login';
    }
})();

const AppState = {
    projects: [],
    isLoading: false,
    currentProject: null,
    inputMode: 'text', // 'text' or 'files'
    selectedFiles: []
};

const elements = {
    textForm: document.getElementById('textForm'),
    fileForm: document.getElementById('fileForm'),
    loading: document.getElementById('loading'),
    result: document.getElementById('result'),
    projectsContainer: document.getElementById('projects'),
    generateTextBtn: document.getElementById('generateTextBtn'),
    generateFilesBtn: document.getElementById('generateFilesBtn'),
    refreshBtn: document.getElementById('refreshBtn'),
    searchInput: document.getElementById('searchProjects'),
    textModeBtn: document.getElementById('textModeBtn'),
    fileModeBtn: document.getElementById('fileModeBtn'),
    fileDropZone: document.getElementById('fileDropZone'),
    filesInput: document.getElementById('files'),
    fileList: document.getElementById('fileList'),
    fileItems: document.getElementById('fileItems'),
    clearFiles: document.getElementById('clearFiles')
};

const ApiService = {
    async generateProjectFromText(prompt, projectName = null, autoRun = false) {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                prompt, 
                project_name: projectName || null,
                auto_run: autoRun,
                input_mode: 'text'
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate project');
        }
        
        return await response.json();
    },

    async generateProjectFromFiles(files, analysisPrompt, projectName = null, autoRun = false) {
        const formData = new FormData();
        
        // Add all files
        for (const file of files) {
            formData.append('files', file);
        }
        
        // Add other parameters
        formData.append('analysis_prompt', analysisPrompt || 'Analyze and improve this project');
        if (projectName) {
            formData.append('project_name', projectName);
        }
        formData.append('auto_run', autoRun.toString());
        
        const response = await fetch('/api/generate/files', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate project from files');
        }
        
        return await response.json();
    },
    
    async generateProjectStream(prompt, projectName = null, autoRun = false, onUpdate) {
        const params = new URLSearchParams({
            prompt: prompt,
            project_name: projectName || '',
            auto_run: autoRun.toString()
        });
        
        const eventSource = new EventSource(`/api/generate/stream?${params}`);
        
        eventSource.onmessage = function(event) {
            if (event.data === '[DONE]') {
                eventSource.close();
                return;
            }
            
            try {
                const data = JSON.parse(event.data);
                onUpdate(data);
            } catch (error) {
                console.error('Error parsing stream data:', error);
                onUpdate({type: 'error', message: 'Error parsing stream data'});
            }
        };
        
        eventSource.onerror = function(event) {
            console.error('EventSource error:', event);
            eventSource.close();
            onUpdate({type: 'error', message: 'Connection error occurred'});
        };
        
        return eventSource;
    },

    async analyzeFiles(files) {
        const formData = new FormData();
        
        for (const file of files) {
            formData.append('files', file);
        }
        
        const response = await fetch('/api/analyze/files', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze files');
        }
        
        return await response.json();
    },
    

    // Alternative using fetch with streaming (if EventSource doesn't work)
    async generateProjectStreamFetch(prompt, projectName = null, autoRun = false, onUpdate) {
        const response = await fetch('/api/generate/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                project_name: projectName || null,
                auto_run: autoRun
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to start streaming generation');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { value, done } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        
                        if (data === '[DONE]') {
                            return;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            onUpdate(parsed);
                        } catch (error) {
                            // Skip invalid JSON lines
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    },
    
    async getProjects() {
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error('Failed to fetch projects');
        }
        return await response.json();
    },
    
    async getProject(projectId) {
        const response = await fetch(`/api/projects/${projectId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch project details');
        }
        return await response.json();
    },

    async runProject(projectId) {
        const response = await fetch(`/api/projects/${projectId}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        if (!response.ok) {
            throw new Error('Failed to run project');
        }
        return await response.json();
    },

    async stopProject(projectId) {
        const response = await fetch(`/api/projects/${projectId}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        if (!response.ok) {
            throw new Error('Failed to stop project');
        }
        return await response.json();
    },

    async deployProject(projectId) {
        const response = await fetch(`/api/projects/${projectId}/deploy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        if (!response.ok) {
            throw new Error('Failed to deploy project');
        }
        return await response.json();
    },
    async getRunningProjects() {
        const response = await fetch('/api/projects/running');
        if (!response.ok) {
            throw new Error('Failed to fetch running projects');
        }
        return await response.json();
    }
};

const ModeManager = {
    switchToTextMode() {
        AppState.inputMode = 'text';
        elements.textForm.style.display = 'block';
        elements.fileForm.style.display = 'none';
        elements.textModeBtn.classList.add('active');
        elements.fileModeBtn.classList.remove('active');
    },
    
    switchToFileMode() {
        AppState.inputMode = 'files';
        elements.textForm.style.display = 'none';
        elements.fileForm.style.display = 'block';
        elements.textModeBtn.classList.remove('active');
        elements.fileModeBtn.classList.add('active');
    }
};

const FileManager = {
    init() {
        // File input change handler
        elements.filesInput.addEventListener('change', (e) => {
            this.handleFiles(Array.from(e.target.files));
        });
        
        // Drag and drop handlers
        elements.fileDropZone.addEventListener('click', () => {
            elements.filesInput.click();
        });
        
        elements.fileDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.fileDropZone.classList.add('drag-over');
        });
        
        elements.fileDropZone.addEventListener('dragleave', () => {
            elements.fileDropZone.classList.remove('drag-over');
        });
        
        elements.fileDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.fileDropZone.classList.remove('drag-over');
            this.handleFiles(Array.from(e.dataTransfer.files));
        });
        
        // Clear files handler
        elements.clearFiles.addEventListener('click', () => {
            this.clearFiles();
        });
    },
    
    handleFiles(files) {
        AppState.selectedFiles = [...AppState.selectedFiles, ...files];
        this.displayFiles();
    },
    
    displayFiles() {
        if (AppState.selectedFiles.length === 0) {
            elements.fileList.style.display = 'none';
            return;
        }
        
        elements.fileList.style.display = 'block';
        elements.fileItems.innerHTML = '';
        
        let totalSize = 0;
        
        AppState.selectedFiles.forEach((file, index) => {
            totalSize += file.size;
            
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${this.formatFileSize(file.size)}</span>
                    <span class="file-type">${file.type || 'unknown'}</span>
                </div>
                <button type="button" class="remove-file" data-index="${index}">×</button>
            `;
            
            elements.fileItems.appendChild(fileItem);
        });
        
        // Add total info
        const totalInfo = document.createElement('div');
        totalInfo.className = 'files-total';
        totalInfo.innerHTML = `
            <strong>Total: ${AppState.selectedFiles.length} files (${this.formatFileSize(totalSize)})</strong>
        `;
        elements.fileItems.appendChild(totalInfo);
        
        // Add remove file handlers
        document.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.removeFile(index);
            });
        });
    },
    
    removeFile(index) {
        AppState.selectedFiles.splice(index, 1);
        this.displayFiles();
    },
    
    clearFiles() {
        AppState.selectedFiles = [];
        elements.filesInput.value = '';
        this.displayFiles();
    },
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

const DeploymentManager = {
    currentDeploymentId: null,
    
    async deployProject(projectId) {
        try {
            // First request deployment config form
            const response = await fetch(`/api/projects/${projectId}/deploy`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to initiate deployment');
            }
            
            const result = await response.json();
            
            if (result.status === 'config_required') {
                // Show SSH configuration modal
                this.showSSHConfigModal(projectId, result);
            } else {
                // Handle other responses
                this.updateDeploymentStatus(projectId, result);
            }
            
        } catch (error) {
            console.error('Deployment error:', error);
            this.showDeploymentError(projectId, error.message);
        }
    },
    
    showSSHConfigModal(projectId, configInfo) {
        // Remove any existing modal first
        const existingModal = document.querySelector('.ssh-config-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal-open class to body to prevent scrolling
        document.body.classList.add('modal-open');
        
        // Create modal overlay with proper CSS class
        const modal = document.createElement('div');
        modal.className = 'ssh-config-modal'; // This matches the CSS class
        
        // Create modal content with proper CSS class
        const content = document.createElement('div');
        content.className = 'ssh-config-content'; // This matches the CSS class
        
        content.innerHTML = `
            <div class="ssh-header">
                <div>
                    <h2>🚀 Deploy to Server</h2>
                    <p>Project: ${configInfo.project_name}</p>
                </div>
                <button type="button" id="closeSSHModal" class="close-btn">×</button>
            </div>
            
            <div class="ssh-body">
                <form id="sshConfigForm">
                    <div class="form-section">
                        <h3>🔐 SSH Connection Details</h3>
                        
                        <div class="form-row two-col">
                            <div class="form-field">
                                <label for="ssh_host">Server IP/Hostname *</label>
                                <input type="text" 
                                       id="ssh_host" 
                                       name="ssh_host" 
                                       required
                                       placeholder="192.168.1.100 or server.domain.com">
                            </div>
                            <div class="form-field">
                                <label for="ssh_port">SSH Port</label>
                                <input type="number" 
                                       id="ssh_port" 
                                       name="ssh_port" 
                                       value="22"
                                       min="1" max="65535">
                            </div>
                        </div>
                        
                        <div class="form-row equal-col">
                            <div class="form-field">
                                <label for="ssh_username">SSH Username *</label>
                                <input type="text" 
                                       id="ssh_username" 
                                       name="ssh_username" 
                                       required
                                       placeholder="root or ubuntu">
                            </div>
                            <div class="form-field">
                                <label for="ssh_password">SSH Password *</label>
                                <input type="password" 
                                       id="ssh_password" 
                                       name="ssh_password" 
                                       required
                                       placeholder="Your SSH password">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <h3>⚙️ Deployment Settings</h3>
                        
                        <div class="form-row two-col">
                            <div class="form-field">
                                <label for="remote_path">Deployment Path</label>
                                <input type="text" 
                                       id="remote_path" 
                                       name="remote_path" 
                                       value="/var/www/deployments"
                                       placeholder="/var/www/deployments">
                            </div>
                            <div class="form-field">
                                <label for="port">App Port</label>
                                <input type="number" 
                                       id="port" 
                                       name="port" 
                                       value="8000"
                                       min="1000" max="65535">
                            </div>
                        </div>
                        
                        <div class="form-checkboxes">
                            <label class="checkbox-label">
                                <input type="checkbox" 
                                       id="auto_install_deps" 
                                       name="auto_install_deps" 
                                       checked>
                                <span class="checkmark"></span>
                                <span>Auto-install dependencies</span>
                            </label>
                            
                            <label class="checkbox-label">
                                <input type="checkbox" 
                                       id="start_service" 
                                       name="start_service" 
                                       checked>
                                <span class="checkmark"></span>
                                <span>Start as process manager service (PM2 for Node.js, systemctl for others)</span>
                            </label>
                            
                            <label class="checkbox-label">
                                <input type="checkbox" 
                                       id="use_pm2" 
                                       name="use_pm2" 
                                       checked>
                                <span class="checkmark"></span>
                                <span>Use PM2 for Node.js projects (recommended)</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="security-warning">
                        <div class="security-warning-header">
                            <span>🔒</span>
                            <strong>Security Notice</strong>
                        </div>
                        <p class="security-warning-text">
                            Your SSH credentials are transmitted securely and not stored. 
                            PM2 will be used for Node.js projects for better process management.
                            Ensure your server has proper firewall rules and security measures in place.
                        </p>
                    </div>
                </form>
            </div>
            
            <div class="ssh-footer">
                <div class="deployment-info">
                    <div>📦 Project will be zipped and transferred</div>
                    <div>🔧 Dependencies will be installed automatically</div>
                    <div>⚡ PM2 will manage Node.js applications</div>
                </div>
                
                <div class="buttons">
                    <button type="button" id="cancelDeployment" class="btn-cancel">Cancel</button>
                    <button type="button" id="startDeployment" class="btn-deploy">🚀 Start Deployment</button>
                </div>
            </div>
        `;
        
        // Append content to modal
        modal.appendChild(content);
        
        // Append modal to body (this is crucial!)
        document.body.appendChild(modal);
        
        // Force layout reflow to ensure modal appears
        modal.offsetHeight;
        
        // Add the 'show' class to trigger CSS animations
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
        
        // Event listeners with proper cleanup
        const closeModal = () => {
            modal.classList.remove('show');
            setTimeout(() => {
                document.body.classList.remove('modal-open');
                if (document.body.contains(modal)) {
                    document.body.removeChild(modal);
                }
            }, 300); // Wait for animation to complete
        };
        
        // Close button handler
        document.getElementById('closeSSHModal').addEventListener('click', closeModal);
        
        // Cancel button handler  
        document.getElementById('cancelDeployment').addEventListener('click', closeModal);
        
        // Deploy button handler
        document.getElementById('startDeployment').addEventListener('click', () => {
            this.startDeploymentWithConfig(projectId, modal);
        });
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        // Close on ESC key
        const handleKeyPress = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', handleKeyPress);
                closeModal();
            }
        };
        document.addEventListener('keydown', handleKeyPress);
        
        // Focus first input after modal is rendered
        setTimeout(() => {
            const firstInput = document.getElementById('ssh_host');
            if (firstInput) {
                firstInput.focus();
            }
        }, 100);
    },

    showDeploymentProgressWithPM2(projectId, config) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        if (deployBtn) {
            deployBtn.disabled = true;
            deployBtn.textContent = 'Deploying...';
            deployBtn.style.background = '#ffa500';
        }
        
        const processManager = config.use_pm2 ? 'PM2' : 'systemctl';
        
        if (statusDiv) {
            statusDiv.style.display = 'block';
            statusDiv.innerHTML = `
                <div class="deployment-progress" style="
                    background: linear-gradient(135deg, #fff3cd 0%, #fef1e1 100%);
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 16px;
                    color: #856404;
                ">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                        <div style="
                            width: 20px; height: 20px; border: 2px solid #856404;
                            border-top: 2px solid transparent; border-radius: 50%;
                            animation: spin 1s linear infinite;
                        "></div>
                        <strong>Deploying to ${config.ssh_username}@${config.ssh_host}</strong>
                    </div>
                    <div style="font-size: 13px; line-height: 1.4;">
                        <div>📦 Creating project archive with ${processManager} config...</div>
                        <div>🔐 Connecting via SSH...</div>
                        <div>📤 Transferring files...</div>
                        <div>⚙️ Installing dependencies...</div>
                        <div>${config.use_pm2 ? '⚡ Starting with PM2...' : '🚀 Starting service...'}</div>
                    </div>
                    <div style="margin-top: 12px; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; font-size: 12px;">
                        <strong>Process Manager:</strong> ${processManager}<br>
                        <strong>Port:</strong> ${config.port}<br>
                        <strong>Auto-install deps:</strong> ${config.auto_install_deps ? 'Yes' : 'No'}
                    </div>
                    <div style="margin-top: 8px; font-size: 12px; opacity: 0.8;">
                        This may take several minutes...
                    </div>
                </div>
            `;
        }
    },

    updateDeploymentStatusWithPM2(projectId, result) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        if (result.status === 'deployed') {
            if (deployBtn) {
                deployBtn.disabled = false;
                deployBtn.textContent = 'Deployed ✓';
                deployBtn.style.background = '#28a745';
            }
            
            const processManager = result.process_manager || 'systemctl';
            
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="deployment-success" style="
                        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                        border: 1px solid #c3e6cb;
                        border-radius: 6px;
                        padding: 16px;
                        color: #155724;
                    ">
                        <div style="margin-bottom: 12px;">
                            <strong>🎉 Deployment Successful!</strong>
                        </div>
                        <div style="margin: 8px 0;">
                            <strong>Application URL:</strong>
                            <a href="${result.deployment_url}" target="_blank" style="
                                color: #6f42c1; text-decoration: none; font-weight: 600;
                                padding: 4px 8px; background: rgba(111, 66, 193, 0.1);
                                border-radius: 4px; margin-left: 8px; transition: all 0.2s;
                            ">${result.deployment_url}</a>
                        </div>
                        <div style="font-size: 13px; margin: 8px 0;">
                            <div><strong>Process Manager:</strong> <code>${processManager}</code></div>
                            <div><strong>Service Status:</strong> <code>${result.service_status}</code></div>
                            <div><strong>Port Open:</strong> <code>${result.port_open ? 'Yes' : 'No'}</code></div>
                        </div>
                        
                        ${processManager === 'PM2' ? `
                        <div style="margin-top: 12px; padding: 8px; background: rgba(0,123,255,0.1); border-radius: 4px; font-size: 12px;">
                            <strong>📊 PM2 Commands:</strong><br>
                            <code>pm2 status</code> - Check status<br>
                            <code>pm2 logs ${result.project_name || 'app'}</code> - View logs<br>
                            <code>pm2 restart ${result.project_name || 'app'}</code> - Restart app
                        </div>
                        ` : ''}
                        
                        ${result.deployment_logs ? `
                        <details style="margin-top: 12px; font-size: 12px;">
                            <summary style="cursor: pointer; font-weight: 600;">View Deployment Logs</summary>
                            <pre style="margin: 8px 0 0; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; overflow-x: auto; max-height: 200px;">${result.deployment_logs.join('\\n')}</pre>
                        </details>
                        ` : ''}
                    </div>
                `;
            }
        } else if (result.status === 'failed') {
            this.showDeploymentError(projectId, result.message, result.deployment_logs);
        }
    },
    
    async startDeploymentWithConfig(projectId, modal) {
        const form = document.getElementById('sshConfigForm');
        const formData = new FormData(form);
        
        // Validate required fields
        const required = ['ssh_host', 'ssh_username', 'ssh_password'];
        for (const field of required) {
            if (!formData.get(field)?.trim()) {
                alert(`Please fill in ${field.replace('ssh_', '').replace('_', ' ')}`);
                return;
            }
        }
        
        // Prepare config with PM2 support
        const config = {
            ssh_host: formData.get('ssh_host').trim(),
            ssh_port: parseInt(formData.get('ssh_port')) || 22,
            ssh_username: formData.get('ssh_username').trim(),
            ssh_password: formData.get('ssh_password'),
            remote_path: formData.get('remote_path').trim() || '/var/www/deployments',
            port: parseInt(formData.get('port')) || 8000,
            auto_install_deps: formData.get('auto_install_deps') === 'on',
            start_service: formData.get('start_service') === 'on',
            use_pm2: formData.get('use_pm2') === 'on'  // New PM2 option
        };
        
        // Remove modal-open class and close modal
        document.body.classList.remove('modal-open');
        document.body.removeChild(modal);
        
        // Show deployment progress with PM2 info
        this.showDeploymentProgressWithPM2(projectId, config);
        
        try {
            // Start deployment
            const response = await fetch(`/api/projects/${projectId}/deploy/ssh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                throw new Error('Deployment request failed');
            }
            
            const result = await response.json();
            this.updateDeploymentStatusWithPM2(projectId, result);
            
        } catch (error) {
            console.error('Deployment error:', error);
            this.showDeploymentError(projectId, error.message);
        }
    },
    


    showDeploymentProgress(projectId, config) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        if (deployBtn) {
            deployBtn.disabled = true;
            deployBtn.textContent = 'Deploying...';
            deployBtn.style.background = '#ffa500';
        }
        
        if (statusDiv) {
            statusDiv.style.display = 'block';
            statusDiv.innerHTML = `
                <div class="deployment-progress" style="
                    background: linear-gradient(135deg, #fff3cd 0%, #fef1e1 100%);
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 16px;
                    color: #856404;
                ">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                        <div style="
                            width: 20px; height: 20px; border: 2px solid #856404;
                            border-top: 2px solid transparent; border-radius: 50%;
                            animation: spin 1s linear infinite;
                        "></div>
                        <strong>Deploying to ${config.ssh_username}@${config.ssh_host}</strong>
                    </div>
                    <div style="font-size: 13px; line-height: 1.4;">
                        <div>📦 Creating project archive...</div>
                        <div>🔐 Connecting via SSH...</div>
                        <div>📤 Transferring files...</div>
                        <div>⚙️ Installing dependencies...</div>
                        <div>🚀 Starting service...</div>
                    </div>
                    <div style="margin-top: 8px; font-size: 12px; opacity: 0.8;">
                        This may take several minutes...
                    </div>
                </div>
            `;
        }
    },
    
    updateDeploymentStatus(projectId, result) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        if (result.status === 'deployed') {
            if (deployBtn) {
                deployBtn.disabled = false;
                deployBtn.textContent = 'Deployed ✓';
                deployBtn.style.background = '#28a745';
            }
            
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="deployment-success" style="
                        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                        border: 1px solid #c3e6cb;
                        border-radius: 6px;
                        padding: 16px;
                        color: #155724;
                    ">
                        <div style="margin-bottom: 12px;">
                            <strong>🎉 Deployment Successful!</strong>
                        </div>
                        <div style="margin: 8px 0;">
                            <strong>Application URL:</strong>
                            <a href="${result.deployment_url}" target="_blank" style="
                                color: #6f42c1; text-decoration: none; font-weight: 600;
                                padding: 4px 8px; background: rgba(111, 66, 193, 0.1);
                                border-radius: 4px; margin-left: 8px; transition: all 0.2s;
                            ">${result.deployment_url}</a>
                        </div>
                        <div style="font-size: 13px; margin-top: 8px;">
                            Service Status: <code>${result.service_status}</code>
                        </div>
                        ${result.deployment_logs ? `
                        <details style="margin-top: 12px; font-size: 12px;">
                            <summary style="cursor: pointer; font-weight: 600;">View Deployment Logs</summary>
                            <pre style="margin: 8px 0 0; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; overflow-x: auto; max-height: 150px;">${result.deployment_logs.join('\\n')}</pre>
                        </details>
                        ` : ''}
                    </div>
                `;
            }
        } else if (result.status === 'failed') {
            this.showDeploymentError(projectId, result.message, result.deployment_logs);
        }
    },
    
    showDeploymentError(projectId, errorMessage, logs = null) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        if (deployBtn) {
            deployBtn.disabled = false;
            deployBtn.textContent = 'Deploy Server';
            deployBtn.style.background = 'linear-gradient(135deg, #6f42c1 0%, #5a2d91 100%)';
        }
        
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="deployment-error" style="
                    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
                    border: 1px solid #f5c6cb;
                    border-radius: 6px;
                    padding: 16px;
                    color: #721c24;
                ">
                    <div style="margin-bottom: 8px;">
                        <strong>❌ Deployment Failed</strong>
                    </div>
                    <div style="margin: 8px 0; font-size: 14px;">
                        ${errorMessage}
                    </div>
                    ${logs ? `
                    <details style="margin-top: 12px; font-size: 12px;">
                        <summary style="cursor: pointer; font-weight: 600;">View Error Logs</summary>
                        <pre style="margin: 8px 0 0; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; overflow-x: auto; max-height: 150px;">${logs.join('\\n')}</pre>
                    </details>
                    ` : ''}
                </div>
            `;
        }
    }
};

const UI = {
    showLoading(mode = 'text') {
        elements.loading.style.display = 'block';
        elements.result.style.display = 'none';
        
        if (mode === 'text') {
            elements.generateTextBtn.disabled = true;
            elements.generateTextBtn.textContent = 'Using MCP Tools...';
        } else {
            elements.generateFilesBtn.disabled = true;
            elements.generateFilesBtn.textContent = 'Analyzing Files...';
        }
        
        AppState.isLoading = true;
    },
    
    hideLoading() {
        elements.loading.style.display = 'none';
        elements.generateTextBtn.disabled = false;
        elements.generateTextBtn.textContent = 'Generate Project with MCP Tools';
        elements.generateFilesBtn.disabled = false;
        elements.generateFilesBtn.textContent = 'Analyze & Generate Improved Project';
        AppState.isLoading = false;
    },
    
    showResult(data, type, mode = 'text') {
        elements.result.className = `result ${type}`;
        
        if (type === 'success') {
            const modeLabel = mode === 'files' ? 'File-Based' : 'Text-Based';
            const sourceInfo = data.source_files ? `
                <div class="source-files-info">
                    <h4>Source Files Analyzed:</h4>
                    <p><strong>Files:</strong> ${data.source_files.total_files}</p>
                    <p><strong>Total Size:</strong> ${this.formatFileSize(data.source_files.total_size)}</p>
                </div>
            ` : '';
            
            elements.result.innerHTML = `
                <div class="result-card">
                    <div class="result-card-header">
                        <div class="result-badge-circle">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                        <div class="result-card-titles">
                            <h3 class="result-card-title">Project Generated!</h3>
                            <span class="result-card-sub">Powered by MCP Tools</span>
                        </div>
                        <div class="result-card-badge">Success</div>
                    </div>

                    <div class="result-card-stats">
                        <div class="result-chip">
                            <span class="result-chip-icon">🏷️</span>
                            <span class="result-chip-label">Name</span>
                            <span class="result-chip-value">${data.project_name}</span>
                        </div>
                        <div class="result-chip">
                            <span class="result-chip-icon">📄</span>
                            <span class="result-chip-label">Files</span>
                            <span class="result-chip-value">${data.files.length}</span>
                        </div>
                        <div class="result-chip">
                            <span class="result-chip-icon">🕐</span>
                            <span class="result-chip-label">Created</span>
                            <span class="result-chip-value">${new Date(data.created_at).toLocaleString()}</span>
                        </div>
                    </div>

                    <div class="result-card-actions project-actions">
                        <button class="run-btn"
                                onclick="ProjectManager.toggleProjectRun('${data.project_id}', this)"
                                data-state="stopped">
                            ▶ Run Project
                        </button>
                        <button onclick="ProjectManager.deployProject('${data.project_id}')" class="deploy-btn">
                            🚀 Deploy
                        </button>
                        <button onclick="ProjectManager.openCodeAssistant('${data.project_id}')" class="code-assistant-btn">
                            🤖 Code Assistant
                        </button>
                        <button class="details-toggle-btn"
                                onclick="(function(btn){
                                    var panel = btn.closest('.result-card').querySelector('.result-card-details');
                                    var open = panel.style.display === 'block';
                                    panel.style.display = open ? 'none' : 'block';
                                    btn.classList.toggle('active', !open);
                                    btn.querySelector('.details-btn-text').textContent = open ? 'View Details' : 'Hide Details';
                                    btn.querySelector('.details-btn-arrow').style.transform = open ? 'rotate(0deg)' : 'rotate(180deg)';
                                })(this)">
                            <span class="details-btn-text">View Details</span>
                            <span class="details-btn-arrow">▾</span>
                        </button>
                    </div>

                    <div class="project-status" style="display: none;"></div>

                    <div class="result-card-details" style="display: none;">
                        <div class="result-detail-row">
                            <span class="result-detail-label">Project ID</span>
                            <code class="result-detail-code">${data.project_id}</code>
                        </div>
                        <div class="result-detail-row">
                            <span class="result-detail-label">Location</span>
                            <code class="result-detail-code">generated_projects/${data.project_name}_${data.project_id.slice(0, 8)}/</code>
                        </div>
                        ${sourceInfo}
                        <div class="result-instructions-block">
                            <div class="result-instructions-header">
                                <span>📋</span>
                                <span>Setup Instructions</span>
                            </div>
                            <pre class="result-instructions-body">${data.instructions}</pre>
                        </div>
                    </div>
                </div>
            `;
        } else {
            elements.result.innerHTML = `
                <h3>Error</h3>
                <p>${data.message || data.error || 'Unknown error occurred'}</p>
            `;
        }
        
        elements.result.style.display = 'block';
        elements.result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    renderProjects(projects) {
        console.log('Rendering projects with token usage:', projects.length);
    
        if (projects.length === 0) {
            elements.projectsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No MCP Projects Generated Yet</h3>
                    <p>Create your first MCP-powered project using text description or file upload!</p>
                </div>
            `;
            return;
        }
        
        // Sort projects by creation date (newest first)
        const sortedProjects = [...projects].sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
        );
        
        elements.projectsContainer.innerHTML = sortedProjects.map(project => {
            const createdDate = new Date(project.created_at);
            const isValidDate = !isNaN(createdDate);
            const displayDate = isValidDate ? 
                createdDate.toLocaleDateString() + ' ' + createdDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) :
                'Unknown';
            
            // Add token usage display if available
            const tokenUsageHtml = project.token_usage ? 
                TokenUI.renderTokenUsage(project.token_usage) : '';
            
            return `
                <div class="project-card" data-project-id="${project.project_id}">
                    <div class="project-header">
                        <h3>${project.project_name}</h3>
                        <span class="project-mode">FullStack Generated</span>
                    </div>
                    
                    <div class="project-meta">
                        <div class="meta-item">
                            <span class="meta-label">Files:</span>
                            <span class="meta-value">${project.file_count || 'N/A'}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Created:</span>
                            <span class="meta-value">${displayDate}</span>
                        </div>
                    </div>
                    
                    ${tokenUsageHtml}
                    
                    <div class="project-id">
                        <strong>ID:</strong> <code>${project.project_id}</code>
                    </div>
                    
                    <div class="project-actions">
                        <button onclick="ProjectManager.viewProject('${project.project_id}')" 
                                class="btn-secondary" title="View project details">
                            View Details
                        </button>
                        
                        <button id="toggleRunBtn-${project.project_id}"
                                class="run-btn"
                                onclick="ProjectManager.toggleProjectRun('${project.project_id}', this)"
                                data-state="stopped"
                                title="Run/Stop this project">
                            ▶ Run Project
                        </button>

                        <button id="deployBtn-${project.project_id}"
                                onclick="ProjectManager.deployProject('${project.project_id}')"
                                class="deploy-btn" title="Deploy this project to server">
                            🚀 Deploy Server
                        </button>

                        <button onclick="ProjectManager.openCodeAssistant('${project.project_id}')"
                                class="code-assistant-btn" title="Open Code Assistant for this project">
                            🤖 Code Assistant
                        </button>
                        
                        <button onclick="TokenUI.showTokenModal('${project.project_id}', '${project.project_name}')" 
                                class="token-usage-btn" title="View token usage details">
                            📊 Tokens
                        </button>
                        <button onclick="ProjectManager.downloadProject('${project.project_id}', '${project.project_name}')" 
                                class="download-btn" title="Download this project as ZIP">
                            ⬇️ Download
                        </button>
                    </div>
                    
                    <div id="projectStatus-${project.project_id}" class="project-status" style="display: none;"></div>
                </div>
            `;
        }).join('');
        
        console.log('Projects rendered successfully with token usage');
    },

    filterProjects(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        const projectCards = document.querySelectorAll('.project-card');
        
        let visibleCount = 0;
        
        projectCards.forEach(card => {
            const projectName = card.querySelector('h3').textContent.toLowerCase();
            const projectId = card.querySelector('.project-id code').textContent.toLowerCase();
            
            const isVisible = !term || 
                             projectName.includes(term) || 
                             projectId.includes(term);
            
            card.style.display = isVisible ? 'block' : 'none';
            if (isVisible) visibleCount++;
        });
        
        // Show "no results" message if needed
        if (term && visibleCount === 0) {
            const existingMessage = document.querySelector('.no-results-message');
            if (!existingMessage) {
                const noResultsDiv = document.createElement('div');
                noResultsDiv.className = 'no-results-message empty-state';
                noResultsDiv.innerHTML = `
                    <h3>No Projects Found</h3>
                    <p>No projects match your search for "${searchTerm}"</p>
                    <button onclick="document.getElementById('searchProjects').value=''; UI.filterProjects('');" class="btn-secondary">
                        Clear Search
                    </button>
                `;
                elements.projectsContainer.appendChild(noResultsDiv);
            }
        } else {
            // Remove "no results" message if it exists
            const existingMessage = document.querySelector('.no-results-message');
            if (existingMessage) {
                existingMessage.remove();
            }
        }
        
        console.log(`Filtered projects: ${visibleCount} visible out of ${projectCards.length}`);
    }
};

const originalShowResult = UI.showResult;
UI.showResult = function(data, type, mode = 'text') {
    // Call original function
    originalShowResult.call(this, data, type, mode);
    
    // Add token usage display if available
    if (type === 'success' && data.token_usage) {
        const resultContainer = elements.result;
        TokenUI.displayTokenUsageInResult(data.token_usage, resultContainer);
    }
};

const ProjectManager = {
    async loadProjects() {
        try {
            console.log('Loading all projects...');
            AppState.projects = await ApiService.getProjects();
            console.log('Projects loaded:', AppState.projects.length);
            
            // Show all projects, not just recent ones
            UI.renderProjects(AppState.projects);
        } catch (error) {
            console.error('Error loading projects:', error);
            elements.projectsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading Projects</h3>
                    <p>${error.message}</p>
                    <button onclick="ProjectManager.loadProjects()" class="btn-secondary">Retry</button>
                </div>
            `;
        }
    },

    async deployProject(projectId) {
        const statusDiv = document.getElementById(`projectStatus-${projectId}`);
        const deployBtn = document.getElementById(`deployBtn-${projectId}`);
        
        try {
            deployBtn.disabled = true;
            deployBtn.textContent = 'Deploying...';
            
            if (statusDiv) {
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = '<p>Starting deployment process...</p>';
            }
            
            const result = await ApiService.deployProject(projectId);
            
            if (result.status === 'deploy_initiated') {
                deployBtn.textContent = 'Deployed';
                deployBtn.disabled = false;
                deployBtn.style.background = '#28a745';
                
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="deployment-status">
                            <p><strong>Deployment Initiated!</strong></p>
                            <p><strong>Status:</strong> ${result.deployment_status}</p>
                            <p><strong>Project:</strong> ${result.project_name}</p>
                            <p><strong>Deployment URL:</strong> 
                                <a href="${result.deployment_url}" target="_blank" class="project-url">${result.deployment_url}</a>
                            </p>
                        </div>
                    `;
                }
            } else {
                deployBtn.textContent = 'Deploy Server';
                deployBtn.disabled = false;
                
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="error-status">
                            <p><strong>Deployment failed:</strong> ${result.message}</p>
                        </div>
                    `;
                }
            }
            
        } catch (error) {
            console.error('Error deploying project:', error);
            deployBtn.textContent = 'Deploy Server';
            deployBtn.disabled = false;
            
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="error-status">
                        <p><strong>Deployment Error:</strong> ${error.message}</p>
                    </div>
                `;
            }
        }
    },

    async loadAllProjectsFromDirectory() {
        try {
            // This would need a backend endpoint to scan the generated_projects directory
            const response = await fetch('/api/projects/scan-directory');
            if (response.ok) {
                const directoryProjects = await response.json();
                console.log('Directory projects found:', directoryProjects.length);
                return directoryProjects;
            }
        } catch (error) {
            console.warn('Could not scan directory for projects:', error);
        }
        return [];
    },

    async refreshAllProjects() {
        try {
            // Load from both API and directory scan
            const [apiProjects, directoryProjects] = await Promise.all([
                ApiService.getProjects(),
                this.loadAllProjectsFromDirectory()
            ]);

            // Merge and deduplicate projects
            const allProjects = new Map();
            
            // Add API projects first
            apiProjects.forEach(project => {
                allProjects.set(project.project_id, project);
            });

            // Add directory projects that might not be in the API
            directoryProjects.forEach(project => {
                if (!allProjects.has(project.project_id)) {
                    allProjects.set(project.project_id, project);
                }
            });

            AppState.projects = Array.from(allProjects.values());
            console.log('Total projects found:', AppState.projects.length);
            
            UI.renderProjects(AppState.projects);
        } catch (error) {
            console.error('Error refreshing projects:', error);
            // Fallback to regular loading
            await this.loadProjects();
        }
    },
    
    async runProject(projectId, btn) {
        const runBtn = btn || document.getElementById(`toggleRunBtn-${projectId}`);
        const statusDiv = runBtn
            ? (runBtn.closest('.project-actions')?.nextElementSibling?.classList.contains('project-status')
                ? runBtn.closest('.project-actions').nextElementSibling
                : runBtn.closest('.project-actions')?.querySelector('.project-status'))
            : document.getElementById(`projectStatus-${projectId}`);

        try {
            if (runBtn) {
                runBtn.disabled = true;
                runBtn.textContent = 'Starting Project...';
            }
            if (statusDiv) {
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = '<p>Installing dependencies and starting project...</p>';
            }

            const result = await ApiService.runProject(projectId);

            if (result.status === 'running') {
                if (runBtn) {
                    runBtn.textContent = '■ Stop Project';
                    runBtn.setAttribute('data-state', 'running');
                    runBtn.classList.remove('run-btn');
                    runBtn.classList.add('stop-btn');
                    runBtn.disabled = false;
                }
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="running-status">
                            <p><strong>Project is running!</strong></p>
                            <p><strong>Access your project:</strong>
                                <a href="${result.url}" target="_blank" class="project-url">${result.url}</a>
                            </p>
                            <p>Command: <code>${result.command}</code></p>
                            <p>Process ID: ${result.pid}</p>
                        </div>
                    `;
                }
            } else {
                if (runBtn) {
                    runBtn.textContent = '▶ Run Project';
                    runBtn.disabled = false;
                }
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="error-status">
                            <p><strong>Failed to start project:</strong></p>
                            <p>${result.message}</p>
                        </div>
                    `;
                }
            }

        } catch (error) {
            console.error('Error running project:', error);
            if (runBtn) {
                runBtn.textContent = '▶ Run Project';
                runBtn.disabled = false;
            }
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="error-status">
                        <p><strong>Error:</strong> ${error.message}</p>
                    </div>
                `;
            }
        }
    },

    async stopProject(projectId, btn) {
        const runBtn = btn || document.getElementById(`toggleRunBtn-${projectId}`);
        const statusDiv = runBtn
            ? (runBtn.closest('.project-actions')?.nextElementSibling?.classList.contains('project-status')
                ? runBtn.closest('.project-actions').nextElementSibling
                : runBtn.closest('.project-actions')?.querySelector('.project-status'))
            : document.getElementById(`projectStatus-${projectId}`);

        try {
            if (runBtn) {
                runBtn.disabled = true;
                runBtn.textContent = 'Stopping...';
            }

            const result = await ApiService.stopProject(projectId);

            if (result.status === 'stopped') {
                if (runBtn) {
                    runBtn.textContent = '▶ Run Project';
                    runBtn.setAttribute('data-state', 'stopped');
                    runBtn.classList.remove('stop-btn');
                    runBtn.classList.add('run-btn');
                    runBtn.disabled = false;
                }
                if (statusDiv) {
                    statusDiv.innerHTML = '<p>Project stopped successfully</p>';
                    setTimeout(() => {
                        statusDiv.style.display = 'none';
                    }, 3000);
                }
            } else {
                if (runBtn) runBtn.disabled = false;
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="error-status">
                            <p><strong>Failed to stop project:</strong> ${result.message}</p>
                        </div>
                    `;
                }
            }

        } catch (error) {
            console.error('Error stopping project:', error);
            if (runBtn) runBtn.disabled = false;
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="error-status">
                        <p><strong>Error:</strong> ${error.message}</p>
                    </div>
                `;
            }
        }
    },

    async toggleProjectRun(projectId, btn) {
        const toggleBtn = btn || document.getElementById(`toggleRunBtn-${projectId}`);
        const currentState = toggleBtn?.getAttribute('data-state');

        if (currentState === 'running') {
            await this.stopProject(projectId, toggleBtn);
        } else {
            await this.runProject(projectId, toggleBtn);
        }
    },
    
    async viewProject(projectId) {
        try {
            const project = await ApiService.getProject(projectId);
            this.showProjectModal(project);
        } catch (error) {
            console.error('Error fetching project:', error);
            alert('Error loading project details: ' + error.message);
        }
    },
    
    showProjectModal(project) {
        // Remove any existing modal
        const existingModal = document.querySelector('.project-details-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = document.createElement('div');
        modal.className = 'project-details-modal';
        
        // Calculate stats
        const totalLines = project.files.reduce((sum, file) => 
            sum + (file.content ? file.content.split('\n').length : 0), 0);
        
        const languageStats = {};
        project.files.forEach(file => {
            const ext = file.path.split('.').pop().toLowerCase();
            const langMap = {
                'py': 'Python', 'js': 'JavaScript', 'ts': 'TypeScript',
                'html': 'HTML', 'css': 'CSS', 'json': 'JSON',
                'md': 'Markdown', 'txt': 'Text', 'jsx': 'React JSX', 
                'tsx': 'React TSX', 'vue': 'Vue', 'java': 'Java',
                'cpp': 'C++', 'c': 'C', 'go': 'Go', 'rs': 'Rust'
            };
            const lang = langMap[ext] || ext.toUpperCase();
            languageStats[lang] = (languageStats[lang] || 0) + 1;
        });
        
        const createdDate = new Date(project.created_at);
        const formattedDate = createdDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        modal.innerHTML = `
            <div class="project-details-content">
                <!-- Header -->
                <div class="project-details-header">
                    <div class="header-main">
                        <div class="project-icon">🚀</div>
                        <div class="header-text">
                            <h2>${project.project_name}</h2>
                            <p class="project-subtitle">Project Details & Files</p>
                        </div>
                    </div>
                    <button class="close-details-btn" onclick="this.closest('.project-details-modal').remove()">
                        ✕
                    </button>
                </div>
                
                <!-- Body -->
                <div class="project-details-body">
                    <!-- Stats Overview -->
                    <div class="stats-overview">
                        <div class="stat-card">
                            <div class="stat-icon">📁</div>
                            <div class="stat-info">
                                <div class="stat-value">${project.files.length}</div>
                                <div class="stat-label">Files</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">📝</div>
                            <div class="stat-info">
                                <div class="stat-value">${totalLines.toLocaleString()}</div>
                                <div class="stat-label">Lines of Code</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">🔤</div>
                            <div class="stat-info">
                                <div class="stat-value">${Object.keys(languageStats).length}</div>
                                <div class="stat-label">Languages</div>
                            </div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-icon">📅</div>
                            <div class="stat-info">
                                <div class="stat-value">${formattedDate.split(',')[0]}</div>
                                <div class="stat-label">Created</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Project Info Grid -->
                    <div class="project-info-grid">
                        <div class="info-section">
                            <h3>🆔 Project Information</h3>
                            <div class="info-content">
                                <div class="info-row">
                                    <span class="info-key">Project ID:</span>
                                    <code class="info-value">${project.project_id}</code>
                                </div>
                                <div class="info-row">
                                    <span class="info-key">Created:</span>
                                    <span class="info-value">${formattedDate}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-key">Total Files:</span>
                                    <span class="info-value">${project.files.length} files</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-key">Total Lines:</span>
                                    <span class="info-value">${totalLines.toLocaleString()} lines</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="info-section">
                            <h3>🔤 Languages Used</h3>
                            <div class="info-content">
                                <div class="language-tags">
                                    ${Object.entries(languageStats).map(([lang, count]) => `
                                        <div class="language-tag">
                                            <span class="lang-name">${lang}</span>
                                            <span class="lang-count">${count}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Instructions Section -->
                    <div class="instructions-section">
                        <h3>📋 Setup Instructions</h3>
                        <div class="instructions-content">
                            <pre>${project.instructions || 'No instructions provided'}</pre>
                        </div>
                    </div>
                    
                    <!-- Files Section -->
                    <div class="files-section">
                        <h3>📂 Project Files (${project.files.length})</h3>
                        <div class="files-list-container">
                            ${project.files.map((file, index) => {
                                const lines = file.content ? file.content.split('\n').length : 0;
                                const size = new Blob([file.content]).size;
                                const sizeKB = (size / 1024).toFixed(2);
                                
                                return `
                                    <details class="file-item" ${index === 0 ? 'open' : ''}>
                                        <summary class="file-summary">
                                            <div class="file-info-left">
                                                <span class="file-icon">📄</span>
                                                <span class="file-name">${file.path}</span>
                                            </div>
                                            <div class="file-meta">
                                                <span class="file-lines">${lines} lines</span>
                                                <span class="file-size">${sizeKB} KB</span>
                                            </div>
                                        </summary>
                                        <div class="file-content-wrapper">
                                            <div class="file-actions">
                                                <button class="copy-code-btn" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent); this.textContent='✓ Copied!'; setTimeout(() => this.textContent='📋 Copy Code', 2000)">
                                                    📋 Copy Code
                                                </button>
                                            </div>
                                            <pre class="file-code"><code>${this.escapeHtml(file.content)}</code></pre>
                                        </div>
                                    </details>
                                `;
                            }).join('')}
                        </div>
                    </div>
                </div>
                
                <!-- Footer -->
                <div class="project-details-footer">
                    <div class="footer-info">
                        <span>💡 Tip: Click on any file to view its content</span>
                    </div>
                    <div class="footer-actions">
                        <button class="btn-secondary" onclick="this.closest('.project-details-modal').remove()">
                            Close
                        </button>
                        <button class="btn-primary" onclick="ProjectManager.openCodeAssistant('${project.project_id}'); this.closest('.project-details-modal').remove();">
                            🤖 Open Code Assistant
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Close on ESC key
        const handleKeyPress = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', handleKeyPress);
                modal.remove();
            }
        };
        document.addEventListener('keydown', handleKeyPress);
    },

    // Helper function to escape HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    openFolder(folderName) {
        alert(`Project saved in: generated_projects/${folderName}/\n\nYou can find this folder in your file system.`);
    },

    async openCodeAssistant(projectId) {
        console.log('Opening Code Assistant for project:', projectId);
        try {
            // Load project data first
            const project = await ApiService.getProject(projectId);
            
            // Hide generator section
            document.getElementById('generatorSection').style.display = 'none';
            const sidebar = document.getElementById('projectsSidebar');
            if (sidebar) {
                sidebar.style.display = 'none';
            }
            
            // Show code assistant section
            const codeAssistantSection = document.getElementById('codeAssistantSection');
            codeAssistantSection.style.display = 'block';
            
            // Update project name in badge
            document.getElementById('currentProjectName').textContent = project.project_name;
            
            // FIX: Set both ProjectManager AND CodeAssistant context
            this.currentProject = project;
            this.currentProjectId = projectId;

            // Store current project
            CodeAssistant.currentProject = project;
            CodeAssistant.currentProjectId = projectId;
            
            // Setup event listeners for this view
            this.setupFullPageCodeAssistant();
            await this.loadChatHistory(projectId);
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
        } catch (error) {
            console.error('Error opening Code Assistant:', error);
            alert('Error opening Code Assistant: ' + error.message);
        }
    },

    async loadChatHistory(projectId) {
        try {
            const chatContainer = document.getElementById('codeAssistantMessages');
            if (!chatContainer) return;
            
            // Clear old chat messages
            const oldMessages = chatContainer.querySelectorAll('.chat-message-full');
            oldMessages.forEach(msg => msg.remove());
            
            const welcomeMsg = chatContainer.querySelector('.welcome-message-full');
            
            const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
            
            const response = await fetch(`/api/projects/${projectId}/chat-history`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                console.warn('Failed to load chat history, starting fresh');
                // No history - SHOW quick suggestions
                if (welcomeMsg) welcomeMsg.style.display = 'block';
                return;
            }
            
            const data = await response.json();
            
            // Check if there are messages for this project
            const projectMessages = data.messages?.filter(msg => msg.project_id === projectId) || [];
            
            if (projectMessages.length > 0) {
                // Has history - HIDE quick suggestions
                if (welcomeMsg) welcomeMsg.style.display = 'none';
                
                // Show all history messages
                projectMessages.forEach(msg => {
                    this.showMessageFullPage(msg.message, msg.sender);
                });
                
                console.log(`Loaded ${projectMessages.length} messages - hiding quick suggestions`);
            } else {
                // No history - SHOW quick suggestions
                if (welcomeMsg) welcomeMsg.style.display = 'block';
                console.log(`No chat history - showing quick suggestions`);
            }
            
        } catch (error) {
            console.error('Error loading chat history:', error);
            const chatContainer = document.getElementById('codeAssistantMessages');
            if (chatContainer) {
                const oldMessages = chatContainer.querySelectorAll('.chat-message-full');
                oldMessages.forEach(msg => msg.remove());
                
                const welcomeMsg = chatContainer.querySelector('.welcome-message-full');
                // Error - SHOW suggestions
                if (welcomeMsg) welcomeMsg.style.display = 'block';
            }
        }
    },

    async downloadProject(projectId, projectName) {
        try {
            console.log('Downloading project:', projectId);
            
            // Show loading state
            const downloadBtn = document.querySelector(`button[onclick*="downloadProject('${projectId}"]`);
            if (downloadBtn) {
                downloadBtn.disabled = true;
                downloadBtn.textContent = '⏳ Downloading...';
            }
            
            // Call the backend API
            const response = await fetch(`/download_project/${projectId}`);
            
            if (!response.ok) {
                throw new Error('Failed to download project');
            }
            
            // Get the blob
            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${projectName || projectId}.zip`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Reset button state
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.textContent = '⬇️ Download';
            }
            
            console.log('Project downloaded successfully');
            
        } catch (error) {
            console.error('Download error:', error);
            alert('Failed to download project: ' + error.message);
            
            // Reset button state
            const downloadBtn = document.querySelector(`button[onclick*="downloadProject('${projectId}"]`);
            if (downloadBtn) {
                downloadBtn.disabled = false;
                downloadBtn.textContent = '⬇️ Download';
            }
        }
    },

    setupFullPageCodeAssistant() {
        console.log('Setup Full Page Code Assistant...');

        // Back to home button
        const backBtn = document.getElementById('backToHomeBtn');
        if (backBtn) {
            backBtn.onclick = () => {
                document.getElementById('codeAssistantSection').style.display = 'none';
                // Show generator section
                document.getElementById('generatorSection').style.display = 'block';
                
                // Show sidebar if it was open before
                const sidebar = document.getElementById('projectsSidebar');
                if (sidebar && ProjectHistoryView.isOpen) {
                    sidebar.style.display = 'flex';
                }
                window.scrollTo({ top: 0, behavior: 'smooth' });
            };
        }
        
        // Input handling
        const input = document.getElementById('codeAssistantInput');
        const sendBtn = document.getElementById('sendCodeAssistantBtn');
        
        if (input && sendBtn) {
            input.addEventListener('input', () => {
                sendBtn.disabled = input.value.trim().length === 0;
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (input.value.trim().length > 0) {
                        this.sendMessageFullPage()
                    }
                }
            });
            
            sendBtn.addEventListener('click', () => {
                this.sendMessageFullPage()
            });
        }
        
        // Quick tip buttons
        document.querySelectorAll('.quick-tip-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.textContent.replace(/"/g, '');
                input.focus();
                sendBtn.disabled = false;
            });
        });
    },

    async sendMessageFullPage() {
        console.log('Sending message from CodeAssistant...');
        const input = document.getElementById('codeAssistantInput');
        const message = input?.value.trim();
        
        console.log('Received message:', message);
        console.log('Current project ID:', this.currentProjectId);
        
        if (!message || !this.currentProjectId) {
            console.error('Missing message or project ID');
            return;
        }
        
        // Get authentication token
        const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
        
        if (!token) {
            this.showMessageFullPage('Authentication required. Please log in again.', 'assistant');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }
        
        // Show user message
        this.showMessageFullPage(message, 'user');
        
        // Clear input
        input.value = '';
        document.getElementById('sendCodeAssistantBtn').disabled = true;
        
        // Create MCP streaming container with beautiful progress
        this.createMCPStreamingContainer();
        
        // Add streaming messages with delays
        setTimeout(() => {
            this.addMCPStreamMessage('Analyzing your request...', 'status');
        }, 300);
        
        setTimeout(() => {
            this.addMCPStreamMessage('Detecting intent: Information vs Code Modification...', 'intent');
        }, 800);
        
        setTimeout(() => {
            this.addMCPStreamMessage('Gathering project information...', 'gathering');
        }, 1300);
        
        setTimeout(() => {
            this.addMCPStreamMessage('analyze_requirements - Understanding what you want to know', 'tool');
        }, 1800);
        
        try {
            const response = await fetch(`/api/projects/${this.currentProjectId}/enhanced-code-assistant`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`  // ✅ FIXED: Add authorization header
                },
                body: JSON.stringify({
                    project_id: this.currentProjectId,
                    message: message,
                    context: "User is working in full-page code assistant"
                })
            });
            
            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.addMCPStreamMessage('Session expired. Redirecting to login...', 'error');
                setTimeout(() => {
                    this.removeMCPStreamingContainer();
                    window.location.href = '/login';
                }, 1500);
                return;
            }
            
            if (!response.ok) {
                throw new Error('Failed to process request');
            }
            
            const result = await response.json();
            
            // Add completion message
            this.addMCPStreamMessage('Analysis complete, preparing response...', 'success');
            
            // Remove streaming container after brief delay
            setTimeout(() => {
                this.removeMCPStreamingContainer();
                
                // Show result
                if (result.is_information_request) {
                    this.showMessageFullPage(result.explanation, 'assistant');
                } else {
                    this.handleCodeModificationResult(result);
                }
            }, 800);
            
        } catch (error) {
            console.error('Error:', error);
            this.addMCPStreamMessage('Error: ' + error.message, 'error');
            
            setTimeout(() => {
                this.removeMCPStreamingContainer();
                this.showMessageFullPage('Error: ' + error.message, 'assistant');
            }, 1000);
        } finally {
            setTimeout(() => {
                document.getElementById('sendCodeAssistantBtn').disabled = false;
            }, 1000);
        }
    },

    async handleCodeModificationResult(result) {
        const shouldApply = await this.showConfirmationDialog(result);
        
        if (shouldApply) {
            this.showMessageFullPage(
                'Changes applied successfully! ' + result.explanation,
                'assistant'
            );
            // Reload project
            this.currentProject = await ApiService.getProject(this.currentProjectId);
        } else {
            this.showMessageFullPage(
                'Changes cancelled. No modifications were made.',
                'assistant'
            );
        }
    },

    createMCPStreamingContainer() {
        const chatContainer = document.getElementById('codeAssistantMessages');
        if (!chatContainer) return;
        
        const streamingDiv = document.createElement('div');
        streamingDiv.id = 'mcpStreamingOutput';
        streamingDiv.className = 'chat-message-full assistant-message-full streaming';
        
        streamingDiv.innerHTML = `
            <div class="message-content-full">
                <div class="mcp-streaming-header">
                    <span class="mcp-icon">📄</span>
                    <strong>MCP Code Modification in Progress...</strong>
                </div>
                <div class="mcp-stream-output" id="mcpStreamContent"></div>
                <div class="message-time-full">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        chatContainer.appendChild(streamingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return streamingDiv;
    },

    addMCPStreamMessage(message, type) {
        const streamContent = document.getElementById('mcpStreamContent');
        if (!streamContent) return;
        
        const timestamp = new Date().toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        
        const typeColors = {
            'status': '#3b82f6',      // Blue
            'mcp_analysis': '#3b82f6', // Blue
            'intent': '#a855f7',       // Purple
            'gathering': '#f59e0b',    // Yellow/Amber
            'tool': '#3b82f6',         // Blue
            'success': '#10b981',      // Green
            'error': '#ef4444'         // Red
        };
        
        const typeIcons = {
            'status': '🔄',
            'mcp_analysis': '🔍',
            'intent': '🎯',
            'gathering': '📦',
            'tool': '🔧',
            'success': '✅',
            'error': '❌'
        };
        
        const color = typeColors[type] || '#6b7280';
        const icon = typeIcons[type] || '•';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `mcp-stream-message mcp-stream-${type}`;
        messageDiv.style.cssText = `
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 10px 14px;
            margin: 6px 0;
            background: ${this.hexToRgba(color, 0.08)};
            border-left: 3px solid ${color};
            border-radius: 6px;
            animation: slideInLeft 0.3s ease;
        `;
        
        messageDiv.innerHTML = `
            <span class="mcp-timestamp" style="
                font-size: 11px;
                color: #6b7280;
                font-weight: 600;
                font-family: 'Monaco', 'Courier New', monospace;
                min-width: 60px;
                opacity: 0.8;
            ">${timestamp}</span>
            <span class="mcp-icon" style="font-size: 14px;">${icon}</span>
            <span class="mcp-message-text" style="
                flex: 1;
                font-size: 13px;
                color: #374151;
                line-height: 1.5;
                font-weight: 500;
            ">${message}</span>
        `;
        
        streamContent.appendChild(messageDiv);
        
        // Auto scroll
        const chatContainer = document.getElementById('codeAssistantMessages');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    },

    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },

    removeMCPStreamingContainer() {
        const streamingOutput = document.getElementById('mcpStreamingOutput');
        if (streamingOutput) {
            streamingOutput.style.opacity = '0';
            streamingOutput.style.transform = 'translateY(-10px)';
            streamingOutput.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                if (streamingOutput.parentNode) {
                    streamingOutput.remove();
                }
            }, 300);
        }
    },
    
    showMessageFullPage(content, type, isProcessing = false) {
        const messagesContainer = document.getElementById('codeAssistantMessages');
        if (!messagesContainer) return;
        
        // Hide welcome message when user sends first message
        if (type === 'user') {
            const welcomeMsg = messagesContainer.querySelector('.welcome-message-full');
            if (welcomeMsg) {
                welcomeMsg.style.display = 'none';
            }
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message-full ${type}-message-full`;
        
        if (isProcessing) {
            messageDiv.id = 'processingMessageFull';
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content-full';
        contentDiv.textContent = content;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time-full';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    },

    removeProcessingMessage() {
        const processing = document.getElementById('processingMessageFull');
        if (processing) {
            processing.remove();
        }
    }
};

ProjectManager.deployProject = function(projectId) {
    DeploymentManager.deployProject(projectId);
};

const FormHandler = {
    async handleTextSubmit(event) {
        event.preventDefault();
        
        if (AppState.isLoading) return;
        
        const formData = new FormData(elements.textForm);
        const prompt = formData.get('prompt').trim();
        const projectName = formData.get('project_name').trim();
        const autoRun = formData.get('auto_run') === 'on';
        
        if (!prompt) {
            alert('Please enter a project prompt');
            return;
        }
        
        UI.showLoading('text');
        
        try {
            const project = await ApiService.generateProjectFromText(prompt, projectName, autoRun);
            UI.showResult(project, 'success', 'text');
            
            await ProjectManager.loadProjects();
            elements.textForm.reset();
            
        } catch (error) {
            console.error('Text generation error:', error);
            UI.showResult({ message: error.message }, 'error', 'text');
        } finally {
            UI.hideLoading();
        }
    },
    
    async handleFileSubmit(event) {
        event.preventDefault();
        
        if (AppState.isLoading) return;
        
        if (AppState.selectedFiles.length === 0) {
            alert('Please select files to upload');
            return;
        }
        
        const formData = new FormData(elements.fileForm);
        const analysisPrompt = formData.get('analysis_prompt').trim();
        const projectName = formData.get('project_name').trim();
        const autoRun = formData.get('auto_run') === 'on';
        
        UI.showLoading('files');
        
        try {
            const project = await ApiService.generateProjectFromFiles(
                AppState.selectedFiles, 
                analysisPrompt, 
                projectName, 
                autoRun
            );
            UI.showResult(project, 'success', 'files');
            
            await ProjectManager.loadProjects();
            elements.fileForm.reset();
            FileManager.clearFiles();
            
        } catch (error) {
            console.error('File generation error:', error);
            UI.showResult({ message: error.message }, 'error', 'files');
        } finally {
            UI.hideLoading();
        }
    }
};

const TokenUI = {
    // Add token usage display to project cards
    renderTokenUsage(tokenUsage) {
        if (!tokenUsage) return '';
        
        const { input_tokens, output_tokens, total_tokens, cost_estimate } = tokenUsage;
        
        return `
            <div class="token-usage-display">
                <div class="token-stats">
                    <span class="token-stat">
                        <span class="token-label">Tokens:</span>
                        <span class="token-value">${total_tokens.toLocaleString()}</span>
                    </span>
                    <span class="token-stat">
                        <span class="token-label">Cost:</span>
                        <span class="token-value">~$${cost_estimate.toFixed(4)}</span>
                    </span>
                </div>
                <div class="token-breakdown">
                    <div class="token-bar">
                        <div class="input-tokens" style="width: ${(input_tokens/total_tokens)*100}%" 
                             title="Input: ${input_tokens.toLocaleString()}"></div>
                        <div class="output-tokens" style="width: ${(output_tokens/total_tokens)*100}%" 
                             title="Output: ${output_tokens.toLocaleString()}"></div>
                    </div>
                </div>
            </div>
        `;
    },
    
    // Create token usage modal
    showTokenModal(projectId, projectName) {
        const modal = document.createElement('div');
        modal.className = 'token-modal';
        modal.innerHTML = `
            <div class="modal-content token-modal-content">
                <div class="modal-header">
                    <h3>📊 Token Usage - ${projectName}</h3>
                    <button class="close-modal" onclick="this.closest('.token-modal').remove()">✕</button>
                </div>
                <div class="modal-body">
                    <div id="tokenLoadingSpinner" class="loading-spinner">
                        <div class="spinner"></div>
                        <p>Loading token usage data...</p>
                    </div>
                    <div id="tokenContent" style="display: none;"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.loadProjectTokenUsage(projectId);
    },
    
    // Load project-specific token usage
    async loadProjectTokenUsage(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/token-usage`);
            const tokenData = await response.json();
            
            const loadingSpinner = document.getElementById('tokenLoadingSpinner');
            const tokenContent = document.getElementById('tokenContent');
            
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (tokenContent) {
                tokenContent.style.display = 'block';
                tokenContent.innerHTML = this.renderProjectTokenDetails(tokenData);
            }
            
        } catch (error) {
            console.error('Error loading token usage:', error);
            const tokenContent = document.getElementById('tokenContent');
            if (tokenContent) {
                tokenContent.innerHTML = '<p class="error">Failed to load token usage data</p>';
                tokenContent.style.display = 'block';
            }
            const loadingSpinner = document.getElementById('tokenLoadingSpinner');
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        }
    },
    
    // Render detailed project token usage
    renderProjectTokenDetails(data) {
        const { total_tokens, input_tokens, output_tokens, cost_estimate, operations_count, operations_breakdown } = data;
        
        if (total_tokens === 0) {
            return '<div class="no-token-usage">No token usage recorded for this project yet.</div>';
        }
        
        let operationsHtml = '';
        if (operations_breakdown && Object.keys(operations_breakdown).length > 0) {
            operationsHtml = `
                <div class="operations-breakdown">
                    <h4>Operations Breakdown</h4>
                    <div class="operations-grid">
                        ${Object.entries(operations_breakdown).map(([opType, opData]) => `
                            <div class="operation-card">
                                <div class="operation-type">${this.formatOperationType(opType)}</div>
                                <div class="operation-stats">
                                    <span>${opData.count} calls</span>
                                    <span>${opData.tokens.toLocaleString()} tokens</span>
                                    <span>~$${opData.cost.toFixed(4)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="project-token-details">
                <div class="token-overview">
                    <div class="token-summary-cards">
                        <div class="token-card">
                            <div class="token-card-header">Total Tokens</div>
                            <div class="token-card-value">${total_tokens.toLocaleString()}</div>
                        </div>
                        <div class="token-card">
                            <div class="token-card-header">Estimated Cost</div>
                            <div class="token-card-value">$${cost_estimate.toFixed(4)}</div>
                        </div>
                        <div class="token-card">
                            <div class="token-card-header">Operations</div>
                            <div class="token-card-value">${operations_count}</div>
                        </div>
                    </div>
                    
                    <div class="token-distribution">
                        <h4>Token Distribution</h4>
                        <div class="distribution-chart">
                            <div class="distribution-bar">
                                <div class="input-portion" 
                                     style="width: ${(input_tokens/total_tokens)*100}%"
                                     title="Input Tokens: ${input_tokens.toLocaleString()}">
                                </div>
                                <div class="output-portion" 
                                     style="width: ${(output_tokens/total_tokens)*100}%"
                                     title="Output Tokens: ${output_tokens.toLocaleString()}">
                                </div>
                            </div>
                            <div class="distribution-legend">
                                <div class="legend-item">
                                    <span class="legend-color input-color"></span>
                                    <span>Input: ${input_tokens.toLocaleString()} (${((input_tokens/total_tokens)*100).toFixed(1)}%)</span>
                                </div>
                                <div class="legend-item">
                                    <span class="legend-color output-color"></span>
                                    <span>Output: ${output_tokens.toLocaleString()} (${((output_tokens/total_tokens)*100).toFixed(1)}%)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                ${operationsHtml}
            </div>
        `;
    },
    
    // Format operation type for display
    formatOperationType(opType) {
        const typeMap = {
            'project_generation': '🚀 Project Generation',
            'code_assistant': '🤖 Code Assistant',
            'file_analysis': '📋 File Analysis',
            'ast_analysis': '🌳 AST Analysis'
        };
        return typeMap[opType] || opType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    },
    
    // Add token usage indicator to result section
    displayTokenUsageInResult(tokenUsage, container) {
        if (!tokenUsage || !container) return;
        
        const tokenDisplay = document.createElement('div');
        tokenDisplay.className = 'token-usage-result';
        tokenDisplay.innerHTML = `
            <div class="token-usage-header">
                <span class="token-icon">📊</span>
                <strong>Token Usage:</strong>
                <span class="token-total">${tokenUsage.total_tokens.toLocaleString()} tokens</span>
                <span class="token-cost">~$${tokenUsage.cost_estimate.toFixed(4)}</span>
            </div>
            <div class="token-usage-details">
                <span>Input: ${tokenUsage.input_tokens.toLocaleString()}</span>
                <span>•</span>
                <span>Output: ${tokenUsage.output_tokens.toLocaleString()}</span>
            </div>
        `;
        
        container.appendChild(tokenDisplay);
    },

    // Global token usage dashboard
    async showGlobalTokenDashboard() {
        const modal = document.createElement('div');
        modal.className = 'token-dashboard-modal';
        modal.innerHTML = `
            <div class="modal-content token-dashboard-content">
                <div class="modal-header">
                    <h3>📈 Global Token Usage Dashboard</h3>
                    <button class="close-modal" onclick="this.closest('.token-dashboard-modal').remove()">✕</button>
                </div>
                <div class="modal-body">
                    <div id="dashboardLoadingSpinner" class="loading-spinner">
                        <div class="spinner"></div>
                        <p>Loading usage dashboard...</p>
                    </div>
                    <div id="dashboardContent" style="display: none;"></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        await this.loadGlobalTokenDashboard();
    },
    
    async loadGlobalTokenDashboard() {
        try {
            const [summaryResponse, dailyResponse] = await Promise.all([
                fetch('/api/token-usage/summary'),
                fetch('/api/token-usage/daily?days=7')
            ]);
            
            const summaryData = await summaryResponse.json();
            const dailyData = await dailyResponse.json();
            
            const loadingSpinner = document.getElementById('dashboardLoadingSpinner');
            const dashboardContent = document.getElementById('dashboardContent');
            
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (dashboardContent) {
                dashboardContent.style.display = 'block';
                dashboardContent.innerHTML = this.renderGlobalDashboard(summaryData, dailyData);
            }
            
        } catch (error) {
            console.error('Error loading token dashboard:', error);
            const dashboardContent = document.getElementById('dashboardContent');
            if (dashboardContent) {
                dashboardContent.innerHTML = '<p class="error">Failed to load dashboard data</p>';
                dashboardContent.style.display = 'block';
            }
            const loadingSpinner = document.getElementById('dashboardLoadingSpinner');
            if (loadingSpinner) loadingSpinner.style.display = 'none';
        }
    },
    
    renderGlobalDashboard(summaryData, dailyData) {
        const { today, last_7_days, total } = summaryData;
        
        // Prepare daily chart data
        const dailyUsage = dailyData.daily_usage;
        const sortedDates = Object.keys(dailyUsage).sort();
        const chartData = sortedDates.map(date => ({
            date,
            tokens: dailyUsage[date].total_tokens || 0,
            cost: dailyUsage[date].cost_estimate || 0.0
        }));
        
        return `
            <div class="global-token-dashboard">
                <div class="dashboard-summary">
                    <div class="summary-cards">
                        <div class="summary-card today">
                            <div class="card-header">Today</div>
                            <div class="card-stats">
                                <div class="stat-value">${today.tokens.toLocaleString()}</div>
                                <div class="stat-label">tokens (~$${today.cost.toFixed(4)})</div>
                            </div>
                        </div>
                        <div class="summary-card week">
                            <div class="card-header">Last 7 Days</div>
                            <div class="card-stats">
                                <div class="stat-value">${last_7_days.tokens.toLocaleString()}</div>
                                <div class="stat-label">tokens (~$${last_7_days.cost.toFixed(4)})</div>
                            </div>
                        </div>
                        <div class="summary-card total">
                            <div class="card-header">Total (${total.projects} projects)</div>
                            <div class="card-stats">
                                <div class="stat-value">${total.tokens.toLocaleString()}</div>
                                <div class="stat-label">tokens (~$${total.cost.toFixed(4)})</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="daily-usage-chart">
                    <h4>Daily Usage (Last 7 Days)</h4>
                    <div class="chart-container">
                        ${this.renderDailyChart(chartData)}
                    </div>
                </div>
                
                <div class="dashboard-actions">
                    <button onclick="TokenUI.exportTokenData()" class="export-btn">
                        📊 Export Data
                    </button>
                    <button onclick="TokenUI.cleanupTokenData()" class="cleanup-btn">
                        🧹 Cleanup Old Data
                    </button>
                </div>
            </div>
        `;
    },
    
    renderDailyChart(chartData) {
        const maxTokens = Math.max(...chartData.map(d => d.tokens));
        
        return `
            <div class="daily-chart">
                ${chartData.map(day => `
                    <div class="chart-bar-container">
                        <div class="chart-bar" 
                             style="height: ${maxTokens > 0 ? (day.tokens / maxTokens) * 100 : 0}%"
                             title="${day.date}: ${day.tokens.toLocaleString()} tokens (~$${day.cost.toFixed(4)})">
                        </div>
                        <div class="chart-label">${new Date(day.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}</div>
                    </div>
                `).join('')}
            </div>
        `;
    },
    
    async exportTokenData() {
        try {
            const response = await fetch('/api/token-usage/daily?days=30');
            const data = await response.json();
            
            const csvContent = this.convertToCSV(data.daily_usage);
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `token-usage-${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Export failed:', error);
            alert('Failed to export token data');
        }
    },
    
    convertToCSV(dailyUsage) {
        const headers = ['Date', 'Total Tokens', 'Input Tokens', 'Output Tokens', 'Cost Estimate'];
        const rows = [headers];
        
        Object.entries(dailyUsage).forEach(([date, data]) => {
            rows.push([
                date,
                data.total_tokens || 0,
                data.input_tokens || 0,
                data.output_tokens || 0,
                (data.cost_estimate || 0).toFixed(4)
            ]);
        });
        
        return rows.map(row => row.join(',')).join('\n');
    },
    
    async cleanupTokenData() {
        if (confirm('This will remove token usage data older than 30 days. Continue?')) {
            try {
                await fetch('/api/token-usage/cleanup', { method: 'POST' });
                alert('Token usage data cleaned up successfully');
                this.loadGlobalTokenDashboard(); // Refresh dashboard
            } catch (error) {
                console.error('Cleanup failed:', error);
                alert('Failed to cleanup token data');
            }
        }
    }
};



const CodeAssistant = {
    currentProjectId: null,
    currentProject: null,
    isOpen: false,
    isProcessing: false,
    
    init() {
        this.setupEventListeners();
    },
    
    setupEventListeners() {
        // Panel controls
        document.getElementById('closePanelBtn')?.addEventListener('click', () => {
            this.closePanel();
        });
        
        document.getElementById('togglePanelSize')?.addEventListener('click', () => {
            this.togglePanelSize();
        });
        
        // Enhanced chat functionality
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendChatBtn');
        
        if (!chatInput || !sendButton) {
            console.error('Chat elements not found');
            return;
        }
        
        // Auto-resize textarea and update send button
        chatInput.addEventListener('input', () => {
            this.autoResizeTextarea(chatInput);
            this.updateSendButton();
        });
        
        // Enhanced send message with intelligent processing
        sendButton.addEventListener('click', () => {
            this.sendIntelligentMessage();
        });
        
        // Enter key to send (Shift+Enter for new line)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendIntelligentMessage();
            }
        });
        
        // Remove old quick action buttons - we don't need them anymore!
        // The LLM will understand intent from natural language
        const quickActions = document.querySelector('.quick-actions');
        if (quickActions) {
            quickActions.innerHTML = `
                <div class="enhanced-tips">
                    <p><strong>💡 Just tell me what you want to do!</strong></p>
                    <div class="tip-examples">
                        <span class="tip">"Add a login form"</span>
                        <span class="tip">"Fix the bug in authentication"</span>
                        <span class="tip">"Delete the old contact page"</span>
                        <span class="tip">"Explain how this component works"</span>
                        <span class="tip">"Add dark mode feature"</span>
                    </div>
                </div>
            `;
        }
    },
    
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    },
    
    updateSendButton() {
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendChatBtn');
        
        if (!chatInput || !sendButton) return;
        
        const hasMessage = chatInput.value.trim().length > 0;
        const hasProject = this.currentProject !== null;
        const notProcessing = !this.isProcessing;
        
        sendButton.disabled = !(hasMessage && hasProject && notProcessing);
        
        if (this.isProcessing) {
            sendButton.textContent = 'Processing...';
        } else {
            sendButton.textContent = 'Send';
        }
    },
    
    async openPanel(projectId) {
        this.currentProjectId = projectId;
        this.isOpen = true;
        
        console.log('Opening enhanced panel for project:', projectId);
        
        // Show panel
        const panel = document.getElementById('codeModificationPanel');
        if (!panel) {
            console.error('Code modification panel not found!');
            return;
        }
        
        panel.style.display = 'flex';
        
        // Load project first
        await this.loadProject();
        
        // Show enhanced initial message
        this.showEnhancedInitialMessage();
        
        // Animate panel in
        setTimeout(() => {
            panel.classList.add('panel-open');
        }, 10);
        
        // Update send button state
        this.updateSendButton();
    },
    
    closePanel() {
        const panel = document.getElementById('codeModificationPanel');
        panel.classList.remove('panel-open');
        
        setTimeout(() => {
            panel.style.display = 'none';
            this.isOpen = false;
            this.currentProjectId = null;
            this.currentProject = null;
            this.isProcessing = false;
        }, 300);
    },
    
    togglePanelSize() {
        const panel = document.getElementById('codeModificationPanel');
        panel.classList.toggle('panel-expanded');
    },

    async loadProject() {
        try {
            console.log('Loading project:', this.currentProjectId);
            
            const response = await fetch(`/api/projects/${this.currentProjectId}`);
            if (!response.ok) {
                throw new Error('Failed to load project');
            }
            
            this.currentProject = await response.json();
            console.log('Project loaded:', this.currentProject.project_name);
            
            return true;
            
        } catch (error) {
            console.error('Error loading project:', error);
            this.showChatMessage('Error loading project details. Please try again.', 'system');
            return false;
        }
    },
    
    updateProjectOverview() {
        if (!this.currentProject) return;
        
        const fileAnalysisDiv = document.getElementById('fileAnalysis');
        const contentDiv = document.getElementById('fileAnalysisContent');
        
        if (!fileAnalysisDiv || !contentDiv) {
            console.error('Project overview elements not found');
            return;
        }
        
        const totalLines = this.currentProject.files.reduce((sum, file) => 
            sum + (file.content ? file.content.split('\n').length : 0), 0);
        
        const languageStats = {};
        this.currentProject.files.forEach(file => {
            const ext = file.path.split('.').pop().toLowerCase();
            const langMap = {
                'py': 'Python', 'js': 'JavaScript', 'ts': 'TypeScript',
                'html': 'HTML', 'css': 'CSS', 'json': 'JSON',
                'md': 'Markdown', 'txt': 'Text', 'jsx': 'React JSX', 'tsx': 'React TSX'
            };
            const lang = langMap[ext] || ext.toUpperCase();
            languageStats[lang] = (languageStats[lang] || 0) + 1;
        });
        
        contentDiv.innerHTML = `
            <div class="analysis-grid">
                <div class="analysis-item">
                    <span class="label">Project:</span>
                    <span class="value">${this.currentProject.project_name}</span>
                </div>
                <div class="analysis-item">
                    <span class="label">Files:</span>
                    <span class="value">${this.currentProject.files.length}</span>
                </div>
                <div class="analysis-item">
                    <span class="label">Lines:</span>
                    <span class="value">${totalLines.toLocaleString()}</span>
                </div>
                <div class="analysis-item">
                    <span class="label">Languages:</span>
                    <span class="value">${Object.keys(languageStats).length}</span>
                </div>
            </div>
            
            <div class="files-breakdown">
                <h5>🗂️ File Types:</h5>
                <ul>
                    ${Object.entries(languageStats).map(([lang, count]) => 
                        `<li><code>${lang}</code>: ${count} file${count > 1 ? 's' : ''}</li>`
                    ).join('')}
                </ul>
            </div>
            
            <div class="files-list">
                <h5>📁 Project Files:</h5>
                <ul>
                    ${this.currentProject.files.slice(0, 8).map(file => 
                        `<li><code>${file.path}</code></li>`
                    ).join('')}
                    ${this.currentProject.files.length > 8 ? 
                        `<li><em>... and ${this.currentProject.files.length - 8} more files</em></li>` : ''}
                </ul>
            </div>
        `;
        
        fileAnalysisDiv.style.display = 'block';
    },
    
    showEnhancedInitialMessage() {
        const welcomeMsg = `🤖 **Enhanced Code Assistant Ready!**

I can understand natural language commands and automatically:

✨ **CREATE** - "Add a login form", "Create a new component"
🔧 **UPDATE** - "Fix the authentication bug", "Add validation to the form"  
🗑️ **DELETE** - "Remove the old contact page", "Delete unused functions"
📚 **EXPLAIN** - "How does this work?", "Explain the database connection"
🚀 **FEATURES** - "Add dark mode", "Implement user profiles"

**Just tell me what you want to do in plain English!**

No need for specific commands - I'll figure out the best approach and execute it using the right tools.

What would you like to work on in "${this.currentProject.project_name}"?`;
        
        this.showChatMessage(welcomeMsg, 'system');
    },
    
    showChatMessage(content, type = 'assistant', isProcessing = false) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) {
            console.error('Chat messages container not found!');
            return;
        }
        
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}-message`;
        
        if (isProcessing) {
            messageDiv.classList.add('processing');
            messageDiv.id = 'processingMessage';
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        
        // Handle different content types
        if (type === 'system') {
            textDiv.innerHTML = this.formatSystemMessage(content);
        } else if (isProcessing) {
            textDiv.innerHTML = `
                <div class="processing-indicator">
                    <div class="processing-dots">
                        <span></span><span></span><span></span>
                    </div>
                    ${content}
                </div>
            `;
        } else {
            textDiv.innerHTML = this.formatMessage(content);
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);
        
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageDiv;
    },
    
    formatSystemMessage(content) {
        // Convert markdown-style formatting to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    },
    
    formatMessage(content) {
        // Format regular messages with basic markdown support
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    },
    
    removeProcessingMessage() {
        const processing = document.getElementById('processingMessage');
        if (processing) {
            processing.remove();
        }
    },

    showConfirmationDialog(result) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'confirmation-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            
            const content = document.createElement('div');
            content.className = 'confirmation-content';
            content.style.cssText = `
                background: white;
                border-radius: 12px;
                width: 90%;
                max-width: 800px;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            `;
            
            content.innerHTML = `
                <div class="confirm-header" style="padding: 24px 24px 16px; border-bottom: 1px solid #e1e5e9;">
                    <h2 style="margin: 0; color: #1a202c; font-size: 20px; display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                            ${result.action_taken === 'create' ? '+' : result.action_taken === 'delete' ? '-' : '~'}
                        </div>
                        Confirm Code Changes
                    </h2>
                    <p style="margin: 8px 0 0 52px; color: #718096; font-size: 14px;">
                        Review the changes before applying them to your project
                    </p>
                </div>
                
                <div class="confirm-body" style="padding: 24px;">
                    <div class="changes-summary" style="background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 12px; color: #2d3748; font-size: 16px;">Changes to be applied:</h3>
                        <ul style="margin: 0; padding-left: 20px; color: #4a5568;">
                            ${result.changes_summary.map(change => `<li style="margin: 6px 0; line-height: 1.5;">${change}</li>`).join('')}
                        </ul>
                    </div>
                    
                    ${this.generateFileChanges(result)}
                    
                    <div class="explanation" style="background: #edf2f7; border-left: 4px solid #4299e1; padding: 16px; border-radius: 0 6px 6px 0; margin-top: 20px;">
                        <h4 style="margin: 0 0 8px; color: #2b6cb0; font-size: 14px;">What will happen:</h4>
                        <p style="margin: 0; color: #2d3748; line-height: 1.5;">${result.explanation}</p>
                    </div>
                </div>
                
                <div class="confirm-footer" style="padding: 20px 24px; background: #f7fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; border-radius: 0 0 12px 12px;">
                    <div class="safety-note" style="display: flex; align-items: center; gap: 8px; color: #718096; font-size: 13px;">
                        <span>🛡️</span>
                        <span>Backups will be created automatically</span>
                    </div>
                    <div class="buttons" style="display: flex; gap: 12px;">
                        <button id="cancelBtn" style="
                            padding: 10px 20px;
                            border: 1px solid #cbd5e0;
                            background: white;
                            color: #4a5568;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 500;
                            transition: all 0.2s;
                        ">Cancel</button>
                        <button id="confirmBtn" style="
                            padding: 10px 20px;
                            border: none;
                            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                            color: white;
                            border-radius: 6px;
                            cursor: pointer;
                            font-weight: 600;
                            transition: all 0.2s;
                            box-shadow: 0 2px 4px rgba(72, 187, 120, 0.2);
                        ">Apply Changes</button>
                    </div>
                </div>
            `;
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            // Add button hover effects
            const cancelBtn = content.querySelector('#cancelBtn');
            const confirmBtn = content.querySelector('#confirmBtn');
            
            cancelBtn.addEventListener('mouseenter', () => {
                cancelBtn.style.background = '#f7fafc';
                cancelBtn.style.borderColor = '#a0aec0';
            });
            
            cancelBtn.addEventListener('mouseleave', () => {
                cancelBtn.style.background = 'white';
                cancelBtn.style.borderColor = '#cbd5e0';
            });
            
            confirmBtn.addEventListener('mouseenter', () => {
                confirmBtn.style.transform = 'translateY(-1px)';
                confirmBtn.style.boxShadow = '0 4px 8px rgba(72, 187, 120, 0.3)';
            });
            
            confirmBtn.addEventListener('mouseleave', () => {
                confirmBtn.style.transform = 'translateY(0)';
                confirmBtn.style.boxShadow = '0 2px 4px rgba(72, 187, 120, 0.2)';
            });
            
            // Event listeners
            cancelBtn.addEventListener('click', () => {
                document.body.removeChild(modal);
                resolve(false);
            });
            
            confirmBtn.addEventListener('click', () => {
                document.body.removeChild(modal);
                resolve(true);
            });
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(false);
                }
            });
        });
    },
    
    generateFileChanges(result) {
        let html = '';
        
        if (result.new_files.length > 0) {
            html += `
                <div class="file-section" style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px; color: #38a169; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 16px; height: 16px; background: #38a169; border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold;">+</span>
                        New Files (${result.new_files.length})
                    </h4>
                    <div style="background: #f0fff4; border: 1px solid #9ae6b4; border-radius: 6px; padding: 12px;">
                        ${result.new_files.map(file => `
                            <div style="font-family: 'Monaco', monospace; font-size: 13px; color: #22543d; margin: 4px 0;">📄 ${file}</div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        if (result.affected_files.length > 0) {
            html += `
                <div class="file-section" style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px; color: #d69e2e; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 16px; height: 16px; background: #d69e2e; border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold;">~</span>
                        Modified Files (${result.affected_files.length})
                    </h4>
                    <div style="background: #fffaf0; border: 1px solid #fbd38d; border-radius: 6px; padding: 12px;">
                        ${result.affected_files.map(file => `
                            <div style="font-family: 'Monaco', monospace; font-size: 13px; color: #744210; margin: 4px 0;">📝 ${file}</div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        if (result.deleted_files.length > 0) {
            html += `
                <div class="file-section" style="margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px; color: #e53e3e; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <span style="width: 16px; height: 16px; background: #e53e3e; border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold;">-</span>
                        Deleted Files (${result.deleted_files.length})
                    </h4>
                    <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 6px; padding: 12px;">
                        ${result.deleted_files.map(file => `
                            <div style="font-family: 'Monaco', monospace; font-size: 13px; color: #742a2a; margin: 4px 0;">🗑️ ${file}</div>
                        `).join('')}
                        <div style="margin-top: 8px; padding: 8px; background: #fed7d7; border-radius: 4px; font-size: 12px; color: #742a2a;">
                            ⚠️ Files will be backed up before deletion
                        </div>
                    </div>
                </div>
            `;
        }
        
        return html;
    },

    
    async sendIntelligentMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput?.value.trim();
        
        if (!message || !this.currentProject || this.isProcessing) {
            return;
        }
        
        // Get authentication token
        const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
        
        if (!token) {
            this.showChatMessage('Authentication required. Please log in again.', 'assistant');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }
        
        this.isProcessing = true;
        this.updateSendButton();
        
        this.showChatMessage(message, 'user');
        chatInput.value = '';
        chatInput.style.height = 'auto';
        
        // Create a streaming output container
        const streamingContainer = this.createStreamingOutputContainer();
        
        try {
            const response = await fetch(`/api/projects/${this.currentProjectId}/enhanced-code-assistant`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`  // ✅ FIXED: Add authorization header
                },
                body: JSON.stringify({
                    project_id: this.currentProjectId,
                    message: message,
                    context: "User is working in the code assistant interface"
                })
            });
            
            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.removeStreamingContainer();
                this.showChatMessage('Session expired. Redirecting to login...', 'assistant');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to process request');
            }
            
            const result = await response.json();
                
            // Remove streaming container
            this.removeStreamingContainer();
            
            // Check if this is an information request
            if (result.is_information_request) {
                // Just show the explanation, no confirmation dialog
                this.showChatMessage(result.explanation, 'assistant');
                
                if (!result.success) {
                    this.showChatMessage(
                        'I encountered an error while analyzing the project. Please try rephrasing your question.',
                        'assistant'
                    );
                }
            } else {
                // This is a code modification request - show confirmation dialog
                if (result.success) {
                    const shouldApply = await this.showConfirmationDialog(result);
                    
                    if (shouldApply) {
                        this.showChatMessage(
                            'Changes applied successfully! ' + 
                            (result.new_files.length > 0 ? `Created ${result.new_files.length} new files. ` : '') +
                            (result.affected_files.length > 0 ? `Modified ${result.affected_files.length} existing files. ` : '') +
                            (result.deleted_files.length > 0 ? `Deleted ${result.deleted_files.length} files. ` : ''),
                            'assistant'
                        );
                        
                        // Reload project to get updated content
                        if (result.affected_files.length > 0 || result.new_files.length > 0) {
                            await this.loadProject();
                            this.updateProjectOverview();
                        }
                    } else {
                        this.showChatMessage(
                            'Changes cancelled. No modifications were made to your project.',
                            'assistant'
                        );
                    }
                } else {
                    this.showChatMessage(
                        `Error: ${result.explanation}`,
                        'assistant'
                    );
                }
            }
            
        } catch (error) {
            console.error('Error in intelligent message processing:', error);
            this.removeStreamingContainer();
            this.showChatMessage(
                `Error: ${error.message}\n\nPlease try rephrasing your request or check the server logs.`,
                'assistant'
            );
        } finally {
            this.isProcessing = false;
            this.updateSendButton();
        }
    },

    createStreamingOutputContainer() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const streamingDiv = document.createElement('div');
        streamingDiv.id = 'streamingOutput';
        streamingDiv.className = 'chat-message assistant-message streaming';
        
        streamingDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">
                    <div class="streaming-header">
                        <strong>🔄 MCP Code Modification in Progress...</strong>
                    </div>
                    <div class="stream-output" id="streamContent">
                        <div class="stream-message stream-status">
                            <span class="stream-timestamp">${new Date().toLocaleTimeString()}</span>
                            Initializing MCP-enhanced code assistant...
                        </div>
                    </div>
                </div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        chatContainer.appendChild(streamingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Start simulated streaming (since we're not using real streaming from backend)
        this.simulateMCPStreaming();
        
        return streamingDiv;
    },
    
    simulateMCPStreaming() {
        const streamContent = document.getElementById('streamContent');
        if (!streamContent) return;
        
        // Different streaming steps for information requests
        const streamingSteps = [
            { delay: 500, type: 'status', message: 'Analyzing your request...' },
            { delay: 1000, type: 'mcp_analysis', message: 'Detecting intent: Information vs Code Modification...' },
            { delay: 1500, type: 'llm_call', message: 'Gathering project information...' },
            { delay: 2000, type: 'tool', message: 'analyze_requirements - Understanding what you want to know' },
            { delay: 2500, type: 'success', message: 'Analysis complete, preparing response...' }
        ];
        
        let currentStep = 0;
        
        const addStreamMessage = () => {
            if (currentStep >= streamingSteps.length) return;
            
            const step = streamingSteps[currentStep];
            const timestamp = new Date().toLocaleTimeString();
            
            const cssClass = `stream-${step.type}`;
            const messageHTML = `
                <div class="stream-message ${cssClass}">
                    <span class="stream-timestamp">${timestamp}</span>
                    ${step.message}
                </div>
            `;
            
            streamContent.insertAdjacentHTML('beforeend', messageHTML);
            
            // Auto scroll to bottom
            const chatContainer = document.getElementById('chatMessages');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            currentStep++;
            
            if (currentStep < streamingSteps.length) {
                setTimeout(addStreamMessage, streamingSteps[currentStep].delay - step.delay);
            }
        };
        
        // Start the streaming simulation
        setTimeout(addStreamMessage, streamingSteps[0].delay);
    },
    
    removeStreamingContainer() {
        const streamingOutput = document.getElementById('streamingOutput');
        if (streamingOutput) {
            streamingOutput.remove();
        }
    },
    
    // Enhanced confirmation dialog with MCP-style information
    async showConfirmationDialog(result) {
        return new Promise((resolve) => {
            // Remove any existing modal first
            const existingModal = document.querySelector('.confirmation-modal');
            if (existingModal) {
                existingModal.remove();
            }
    
            const modal = document.createElement('div');
            modal.className = 'confirmation-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                backdrop-filter: blur(2px);
            `;
            
            const content = document.createElement('div');
            content.className = 'confirmation-content';
            content.style.cssText = `
                background: white;
                border-radius: 12px;
                width: 90%;
                max-width: 800px;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                display: flex;
                flex-direction: column;
            `;
            
            content.innerHTML = `
                <div class="confirm-header" style="padding: 24px 24px 16px; border-bottom: 1px solid #e1e5e9; flex-shrink: 0;">
                    <h2 style="margin: 0; color: #1a202c; font-size: 20px; display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                            ${result.action_taken === 'create' ? '+' : result.action_taken === 'delete' ? '-' : '~'}
                        </div>
                        Confirm Code Changes
                    </h2>
                    <p style="margin: 8px 0 0 52px; color: #718096; font-size: 14px;">
                        Review the changes before applying them to your project
                    </p>
                </div>
                
                <div class="confirm-body" style="padding: 24px; flex: 1; overflow-y: auto;">
                    <div class="changes-summary" style="background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 12px; color: #2d3748; font-size: 16px;">Changes to be applied:</h3>
                        <ul style="margin: 0; padding-left: 20px; color: #4a5568;">
                            ${result.changes_summary.map(change => `<li style="margin: 6px 0; line-height: 1.5;">${change}</li>`).join('')}
                        </ul>
                    </div>
                    
                    ${this.generateFileChanges(result)}
                    
                    <div class="explanation" style="background: #edf2f7; border-left: 4px solid #4299e1; padding: 16px; border-radius: 0 6px 6px 0; margin-top: 20px;">
                        <h4 style="margin: 0 0 8px; color: #2b6cb0; font-size: 14px;">What will happen:</h4>
                        <p style="margin: 0; color: #2d3748; line-height: 1.5;">${result.explanation}</p>
                    </div>
                </div>
                
                <div class="confirm-footer" style="
                    padding: 20px 24px; 
                    background: #f7fafc; 
                    border-top: 1px solid #e2e8f0; 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    border-radius: 0 0 12px 12px;
                    flex-shrink: 0;
                    min-height: 80px;
                ">
                    <div class="safety-note" style="display: flex; align-items: center; gap: 8px; color: #718096; font-size: 13px;">
                        <span>🛡️</span>
                        <span>Backups will be created automatically</span>
                    </div>
                    <div class="buttons" style="display: flex; gap: 12px;">
                        <button id="cancelBtn" style="
                            padding: 12px 24px;
                            border: 2px solid #cbd5e0;
                            background: white;
                            color: #4a5568;
                            border-radius: 8px;
                            cursor: pointer;
                            font-weight: 600;
                            font-size: 14px;
                            transition: all 0.2s;
                            min-width: 100px;
                        ">Cancel</button>
                        <button id="confirmBtn" style="
                            padding: 12px 24px;
                            border: none;
                            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                            color: white;
                            border-radius: 8px;
                            cursor: pointer;
                            font-weight: 600;
                            font-size: 14px;
                            transition: all 0.2s;
                            box-shadow: 0 2px 4px rgba(72, 187, 120, 0.2);
                            min-width: 120px;
                        ">Apply Changes</button>
                    </div>
                </div>
            `;
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            // Get button references after DOM insertion
            const cancelBtn = content.querySelector('#cancelBtn');
            const confirmBtn = content.querySelector('#confirmBtn');
            
            if (!cancelBtn || !confirmBtn) {
                console.error('Buttons not found in modal');
                resolve(false);
                return;
            }
            
            // Add hover effects
            cancelBtn.addEventListener('mouseenter', () => {
                cancelBtn.style.background = '#f7fafc';
                cancelBtn.style.borderColor = '#a0aec0';
                cancelBtn.style.transform = 'translateY(-1px)';
            });
            
            cancelBtn.addEventListener('mouseleave', () => {
                cancelBtn.style.background = 'white';
                cancelBtn.style.borderColor = '#cbd5e0';
                cancelBtn.style.transform = 'translateY(0)';
            });
            
            confirmBtn.addEventListener('mouseenter', () => {
                confirmBtn.style.transform = 'translateY(-1px)';
                confirmBtn.style.boxShadow = '0 4px 8px rgba(72, 187, 120, 0.3)';
            });
            
            confirmBtn.addEventListener('mouseleave', () => {
                confirmBtn.style.transform = 'translateY(0)';
                confirmBtn.style.boxShadow = '0 2px 4px rgba(72, 187, 120, 0.2)';
            });
            
            // Event listeners
            cancelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                document.body.removeChild(modal);
                resolve(false);
            });
            
            confirmBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                document.body.removeChild(modal);
                resolve(true);
            });
            
            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(false);
                }
            });
            
            // Close on ESC key
            const handleKeyPress = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', handleKeyPress);
                    if (document.body.contains(modal)) {
                        document.body.removeChild(modal);
                        resolve(false);
                    }
                }
            };
            document.addEventListener('keydown', handleKeyPress);
            
            // Focus management
            setTimeout(() => {
                cancelBtn.focus();
            }, 100);
        });
    },
    
    generateMCPChangesDisplay(result) {
        let html = '<div class="mcp-operations">';
        
        // Show MCP calls made
        if (result.mcp_calls_made.length > 0) {
            html += '<h4>🔧 MCP Operations Executed:</h4>';
            html += '<ul class="mcp-calls-list">';
            result.mcp_calls_made.forEach(call => {
                const status = call.success ? '✅' : '❌';
                html += `<li>${status} <strong>${call.tool}</strong>: ${call.description || 'Operation completed'}</li>`;
            });
            html += '</ul>';
        }
        
        // Show changes summary
        html += '<h4>📋 Changes Made:</h4>';
        html += '<ul class="changes-list">';
        result.changes_summary.forEach(change => {
            html += `<li>• ${change}</li>`;
        });
        html += '</ul>';
        
        // Show file operations
        if (result.new_files.length > 0) {
            html += '<h4>📁 New Files Created:</h4>';
            html += '<ul class="file-operations new-files">';
            result.new_files.forEach(file => {
                html += `<li><code>+ ${file}</code></li>`;
            });
            html += '</ul>';
        }
        
        if (result.affected_files.length > 0) {
            html += '<h4>✏️ Files Modified:</h4>';
            html += '<ul class="file-operations modified-files">';
            result.affected_files.forEach(file => {
                html += `<li><code>~ ${file}</code></li>`;
            });
            html += '</ul>';
        }
        
        if (result.deleted_files.length > 0) {
            html += '<h4>🗑️ Files Deleted:</h4>';
            html += '<ul class="file-operations deleted-files">';
            result.deleted_files.forEach(file => {
                html += `<li><code>- ${file}</code></li>`;
            });
            html += '</ul>';
        }
        
        html += '</div>';
        return html;
    },

    formatSuccessResponse(result) {
        let responseText = `${result.explanation}\n\n`;
        
        if (result.changes_summary.length > 0) {
            responseText += `**📋 Changes Made:**\n`;
            result.changes_summary.forEach(change => {
                responseText += `• ${change}\n`;
            });
            responseText += '\n';
        }
        
        if (result.new_files.length > 0) {
            responseText += `**📁 New Files Created:** ${result.new_files.join(', ')}\n\n`;
        }
        
        if (result.affected_files.length > 0) {
            responseText += `**✏️ Files Modified:** ${result.affected_files.join(', ')}\n\n`;
        }
        
        if (result.deleted_files.length > 0) {
            responseText += `**🗑️ Files Deleted:** ${result.deleted_files.join(', ')}\n\n`;
        }
        
        if (result.next_steps.length > 0) {
            responseText += `**🎯 Suggested Next Steps:**\n`;
            result.next_steps.forEach(step => {
                responseText += `• ${step}\n`;
            });
        }
        
        return responseText;
    },
    
    showSuccessResponse(result) {
        const actionEmojis = {
            'create': '✨',
            'update': '🔧', 
            'delete': '🗑️',
            'explain': '📚',
            'add_feature': '🚀',
            'error': '❌'
        };
        
        const emoji = actionEmojis[result.action_taken] || '✅';
        
        let responseText = `${emoji} **Action: ${result.action_taken.replace('_', ' ').toUpperCase()}**\n\n`;
        responseText += `${result.explanation}\n\n`;
        
        // Show what was changed
        if (result.changes_summary.length > 0) {
            responseText += `**📋 Changes Made:**\n`;
            result.changes_summary.forEach(change => {
                responseText += `• ${change}\n`;
            });
            responseText += '\n';
        }
        
        // Show affected files
        if (result.new_files.length > 0) {
            responseText += `**📁 New Files Created:** ${result.new_files.join(', ')}\n\n`;
        }
        
        if (result.affected_files.length > 0) {
            responseText += `**✏️ Files Modified:** ${result.affected_files.join(', ')}\n\n`;
        }
        
        if (result.deleted_files.length > 0) {
            responseText += `**🗑️ Files Deleted:** ${result.deleted_files.join(', ')}\n\n`;
        }
        
        // Show next steps
        if (result.next_steps.length > 0) {
            responseText += `**🎯 Suggested Next Steps:**\n`;
            result.next_steps.forEach(step => {
                responseText += `• ${step}\n`;
            });
        }
        
        this.showChatMessage(responseText, 'assistant');
        
        // Show MCP calls made (for debugging - can be removed in production)
        if (result.mcp_calls_made.length > 0) {
            const debugInfo = `🔧 **Debug Info**: Made ${result.mcp_calls_made.length} MCP tool calls`;
            this.showChatMessage(debugInfo, 'system');
        }
    }
};

const ProjectHistoryView = {
    isOpen: false,
    
    async open() {
        this.isOpen = true;
        
        // Hide main generator section
        document.getElementById('generatorSection').style.display = 'none';
        document.getElementById('codeAssistantSection').style.display = 'none';
        
        // Show sidebar with all projects
        const sidebar = document.getElementById('projectsSidebar');
        sidebar.style.display = 'flex';
        sidebar.classList.add('history-view');
        
        // Update back button visibility
        const backBtn = sidebar.querySelector('.your-project-back button');
        if (backBtn) {
            backBtn.style.display = 'block';
            backBtn.onclick = () => this.close();
        }
        
        // Update sidebar title
        const sidebarTitle = sidebar.querySelector('.sidebar-title');
        if (sidebarTitle) {
            sidebarTitle.textContent = 'Your Projects';
        }
        
        // Load all projects
        await ProjectManager.loadProjects();
    },
    
};

function initializeEventListeners() {
    // Mode switchers
    elements.textModeBtn.addEventListener('click', ModeManager.switchToTextMode);
    elements.fileModeBtn.addEventListener('click', ModeManager.switchToFileMode);
    
    // Form handlers
    elements.textForm.addEventListener('submit', FormHandler.handleTextSubmit);
    elements.fileForm.addEventListener('submit', FormHandler.handleFileSubmit);
    
    // Other existing handlers...
    elements.refreshBtn.addEventListener('click', () => {
        ProjectManager.loadProjects();
    });
    
    elements.searchInput.addEventListener('input', (e) => {
        UI.filterProjects(e.target.value);
    });
}

function logout() {
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('authToken');
    window.location.href = '/login';
}

const historyBtn = document.querySelector('.project-history-btn');
if (historyBtn) {
    historyBtn.addEventListener('click', () => {
        ProjectHistoryView.open();
    });
}

function goHome() {
    // Hide code assistant section
    const codeAssistantSection = document.getElementById('codeAssistantSection');
    if (codeAssistantSection) codeAssistantSection.style.display = 'none';

    // Hide token dashboard (if it exists)
    const tokenDashboard = document.getElementById('tokenDashboard');
    if (tokenDashboard) tokenDashboard.style.display = 'none';

    // Hide project history section (important fix!)
    const historySection = document.getElementById('projectHistorySection');
    if (historySection) historySection.style.display = 'none';

    // Show generator section
    const generatorSection = document.getElementById('generatorSection');
    if (generatorSection) generatorSection.style.display = 'block';

    // Show sidebar again if available
    const sidebar = document.getElementById('projectsSidebar');
    if (sidebar) sidebar.style.display = 'none';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

const modalCSS = `
.confirmation-modal {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.confirmation-modal * {
    box-sizing: border-box;
}

.confirmation-modal button:focus {
    outline: 2px solid #4299e1;
    outline-offset: 2px;
}

@media (max-width: 768px) {
    .confirmation-modal .confirmation-content {
        width: 95%;
        max-height: 95vh;
        margin: 10px;
    }
    
    .confirmation-modal .confirm-footer {
        flex-direction: column;
        gap: 12px;
        align-items: stretch;
    }
    
    .confirmation-modal .buttons {
        order: -1;
        justify-content: stretch;
    }
    
    .confirmation-modal .buttons button {
        flex: 1;
        min-width: auto;
    }
}
`;

// Inject the CSS if it doesn't exist
if (!document.getElementById('confirmation-modal-styles')) {
    const style = document.createElement('style');
    style.id = 'confirmation-modal-styles';
    style.textContent = modalCSS;
    document.head.appendChild(style);
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Dual-Input MCP Project Generator initialized');
    initializeEventListeners();
    FileManager.init();
    ProjectManager.loadProjects();
    CodeAssistant.init();
    const navTokenBtn = document.querySelector('.token-dashboard-btn');
    if (navTokenBtn) {
        navTokenBtn.addEventListener('click', () => TokenUI.showGlobalTokenDashboard());
    }
});

window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});

const originalInitializeEventListeners = initializeEventListeners;
initializeEventListeners = function() {
    originalInitializeEventListeners();
    CodeAssistant.init();
};