// Global variables
let selectedFiles = [];
let sessionId = null;
let downloadUrl = null;

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const uploadSection = document.getElementById('uploadSection');
const filesSection = document.getElementById('filesSection');
const resultSection = document.getElementById('resultSection');
const errorSection = document.getElementById('errorSection');
const filesList = document.getElementById('filesList');
const fileCount = document.getElementById('fileCount');
const clearBtn = document.getElementById('clearBtn');
const mergeBtn = document.getElementById('mergeBtn');
const downloadBtn = document.getElementById('downloadBtn');
const newMergeBtn = document.getElementById('newMergeBtn');
const retryBtn = document.getElementById('retryBtn');
const errorMessage = document.getElementById('errorMessage');

// Event listeners
browseBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileSelect);
clearBtn.addEventListener('click', clearFiles);
mergeBtn.addEventListener('click', mergePDFs);
downloadBtn.addEventListener('click', downloadMergedPDF);
newMergeBtn.addEventListener('click', resetApp);
retryBtn.addEventListener('click', hideError);

// Drag and drop events
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files).filter(file => file.type === 'application/pdf');
    if (files.length > 0) {
        handleFiles(files);
    } else {
        showError('Please drop only PDF files');
    }
});

uploadArea.addEventListener('click', () => fileInput.click());

// Handle file selection
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    handleFiles(files);
}

// Handle files
function handleFiles(files) {
    if (files.length === 0) return;
    
    // Validate files
    const validFiles = files.filter(file => {
        if (file.type !== 'application/pdf') {
            showError(`${file.name} is not a PDF file`);
            return false;
        }
        if (file.size > 50 * 1024 * 1024) {
            showError(`${file.name} is too large (max 50MB)`);
            return false;
        }
        return true;
    });
    
    if (validFiles.length === 0) return;
    
    selectedFiles = [...selectedFiles, ...validFiles];
    updateFilesList();
    showFilesSection();
}

// Update files list display
function updateFilesList() {
    filesList.innerHTML = '';
    fileCount.textContent = selectedFiles.length;
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">PDF</div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
            </div>
            <button class="file-remove" onclick="removeFile(${index})" title="Remove file">
                ×
            </button>
        `;
        filesList.appendChild(fileItem);
    });
    
    mergeBtn.disabled = selectedFiles.length < 2;
}

// Remove file from list
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFilesList();
    
    if (selectedFiles.length === 0) {
        hideFilesSection();
    }
}

// Clear all files
function clearFiles() {
    selectedFiles = [];
    fileInput.value = '';
    hideFilesSection();
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Show files section
function showFilesSection() {
    uploadSection.style.display = 'none';
    filesSection.style.display = 'block';
}

// Hide files section
function hideFilesSection() {
    uploadSection.style.display = 'block';
    filesSection.style.display = 'none';
}

// Merge PDFs
async function mergePDFs() {
    if (selectedFiles.length < 2) {
        showError('Please select at least 2 PDF files');
        return;
    }
    
    // Show loading state
    mergeBtn.disabled = true;
    mergeBtn.querySelector('.btn-text').style.display = 'none';
    mergeBtn.querySelector('.btn-loader').style.display = 'block';
    
    try {
        // Upload files
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files[]', file);
        });
        
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.error || 'Upload failed');
        }
        
        const uploadData = await uploadResponse.json();
        sessionId = uploadData.session_id;
        
        // Merge files
        const mergeResponse = await fetch('/api/merge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        if (!mergeResponse.ok) {
            const error = await mergeResponse.json();
            throw new Error(error.error || 'Merge failed');
        }
        
        const mergeData = await mergeResponse.json();
        downloadUrl = mergeData.download_url;
        
        // Show success
        showSuccess();
        
    } catch (error) {
        showError(error.message);
    } finally {
        // Reset button state
        mergeBtn.disabled = false;
        mergeBtn.querySelector('.btn-text').style.display = 'block';
        mergeBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

// Download merged PDF
function downloadMergedPDF() {
    if (downloadUrl) {
        window.location.href = downloadUrl;
    }
}

// Show success section
function showSuccess() {
    filesSection.style.display = 'none';
    resultSection.style.display = 'block';
    errorSection.style.display = 'none';
}

// Show error section
function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    setTimeout(() => {
        errorSection.style.display = 'none';
    }, 5000);
}

// Hide error section
function hideError() {
    errorSection.style.display = 'none';
}

// Reset app
function resetApp() {
    selectedFiles = [];
    sessionId = null;
    downloadUrl = null;
    fileInput.value = '';
    
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
    uploadSection.style.display = 'block';
    filesSection.style.display = 'none';
    
    // Cleanup session
    if (sessionId) {
        fetch(`/api/cleanup/${sessionId}`, { method: 'DELETE' });
    }
}

// Initialize app
window.addEventListener('load', () => {
    console.log('PDF Merger App initialized');
});