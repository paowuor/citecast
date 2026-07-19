/**
 * CiteCast Main JavaScript
 * Handles upload form, progress tracking, and job management
 */

// Upload form handling
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the upload page
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        initUploadForm();
    }
    
    // Check if we're on the viewer page
    if (document.getElementById('player-container')) {
        initViewer();
    }
});

function initUploadForm() {
    const form = document.getElementById('upload-form');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const submitBtn = document.getElementById('submit-btn');
    
    // Drag and drop handling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateFileDisplay(fileInput.files[0].name);
        }
    });
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            updateFileDisplay(fileInput.files[0].name);
        }
    });
    
    function updateFileDisplay(filename) {
        const content = dropZone.querySelector('.drop-zone-content');
        content.innerHTML = `
            <i class="fas fa-file-pdf" style="color: #4CAF50;"></i>
            <p><strong>${filename}</strong></p>
            <p class="drop-hint">Click to change file</p>
        `;
    }
    
    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!fileInput.files.length) {
            showNotification('Please select a file first.', 'warning');
            return;
        }
        
        const formData = new FormData(form);
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        try {
            const response = await fetch('/api/jobs', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showNotification('Job created successfully!', 'success');
                showResult(data);
            } else {
                showNotification(data.detail || 'Upload failed', 'error');
            }
        } catch (error) {
            showNotification('Error: ' + error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-rocket"></i> Generate Media';
        }
    });
}

function showResult(data) {
    const resultDiv = document.getElementById('job-result');
    const viewerLink = document.getElementById('viewer-link');
    const jobIdDisplay = document.getElementById('job-id-display');
    
    if (resultDiv && viewerLink && jobIdDisplay) {
        viewerLink.href = data.viewer_url || `/viewer/${data.job_id}`;
        jobIdDisplay.textContent = data.job_id;
        resultDiv.style.display = 'block';
    }
}

function initViewer() {
    // Check if CiteCastPlayer is available
    if (typeof CiteCastPlayer === 'function') {
        const playerConfig = {
            container: document.getElementById('player-container'),
            sidebar: document.getElementById('citation-sidebar'),
            scenes: window.sceneData || [],
            autoPlay: false
        };
        window.player = new CiteCastPlayer(playerConfig);
    }
}

// Notification system
function showNotification(message, type = 'info') {
    const colors = {
        success: '#4CAF50',
        error: '#F44336',
        warning: '#FF9800',
        info: '#2196F3'
    };
    
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${colors[type] || '#333'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100px); opacity: 0; }
    }
`;
document.head.appendChild(style);