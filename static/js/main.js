// Global variables
let currentJobId = null;
let statusInterval = null;

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const referenceFile = document.getElementById('referenceFile');
const syllabusFile = document.getElementById('syllabusFile');
const generateButton = document.getElementById('generateButton');
const progressSection = document.getElementById('progressSection');
const resultSection = document.getElementById('resultSection');
const errorSection = document.getElementById('errorSection');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeFileUploads();
    initializeDragAndDrop();
    initializeForm();
});

// File upload handling
function initializeFileUploads() {
    referenceFile.addEventListener('change', function(e) {
        updateFileName('referenceName', e.target.files[0]);
        updateUploadCard('referenceUpload', e.target.files[0]);
    });

    syllabusFile.addEventListener('change', function(e) {
        updateFileName('syllabusName', e.target.files[0]);
        updateUploadCard('syllabusUpload', e.target.files[0]);
    });
}

// Drag and Drop Implementation
function initializeDragAndDrop() {
    // Reference upload area
    const referenceUploadArea = document.getElementById('referenceUpload');
    const syllabusUploadArea = document.getElementById('syllabusUpload');
    
    setupDragAndDrop(referenceUploadArea, referenceFile, 'referenceName', 'Reference Book');
    setupDragAndDrop(syllabusUploadArea, syllabusFile, 'syllabusName', 'Syllabus');
}

function setupDragAndDrop(dropArea, fileInput, fileNameId, fileType) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => highlight(dropArea), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => unhighlight(dropArea), false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', (e) => handleDrop(e, fileInput, fileNameId, fileType), false);
    
    // Add click handler for the entire drop area
    dropArea.addEventListener('click', (e) => {
        if (!e.target.matches('button')) {
            fileInput.click();
        }
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(dropArea) {
    dropArea.closest('.upload-card').classList.add('drag-over');
}

function unhighlight(dropArea) {
    dropArea.closest('.upload-card').classList.remove('drag-over');
}

function handleDrop(e, fileInput, fileNameId, fileType) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
        const file = files[0];
        
        // Validate file type
        if (file.type !== 'application/pdf') {
            showError(`${fileType} must be a PDF file. Selected file type: ${file.type}`);
            return;
        }

        // Set the file to the input element
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;

        // Update UI
        updateFileName(fileNameId, file);
        updateUploadCard(fileInput.id.replace('File', 'Upload'), file);
        
        // Show success feedback
        showDropSuccess(fileInput.id.replace('File', 'Upload'), fileType);
    }
}

function showDropSuccess(uploadId, fileType) {
    const uploadArea = document.getElementById(uploadId);
    const originalText = uploadArea.querySelector('h3').textContent;
    
    uploadArea.querySelector('h3').textContent = `${fileType} Uploaded! ✓`;
    uploadArea.querySelector('h3').style.color = 'var(--accent-primary)';
    
    setTimeout(() => {
        uploadArea.querySelector('h3').textContent = originalText;
        uploadArea.querySelector('h3').style.color = 'var(--text-primary)';
    }, 2000);
}

function updateFileName(elementId, file) {
    const nameElement = document.getElementById(elementId);
    if (file) {
        nameElement.textContent = `Selected: ${file.name}`;
        nameElement.style.color = 'var(--accent-primary)';
    } else {
        nameElement.textContent = '';
    }
}

function updateUploadCard(cardId, file) {
    const card = document.getElementById(cardId).closest('.upload-card');
    if (file) {
        card.style.borderColor = 'var(--accent-primary)';
        card.style.backgroundColor = 'rgba(16, 163, 127, 0.1)';
    } else {
        card.style.borderColor = 'var(--border-color)';
        card.style.backgroundColor = 'var(--bg-secondary)';
    }
}

// Form handling
function initializeForm() {
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        startProcessing();
    });
}

function validateForm() {
    const referenceFile = document.getElementById('referenceFile').files[0];
    const syllabusFile = document.getElementById('syllabusFile').files[0];
    
    if (!referenceFile) {
        showError('Please select a reference book PDF file.');
        return false;
    }
    
    if (!syllabusFile) {
        showError('Please select a syllabus PDF file.');
        return false;
    }
    
    if (referenceFile.type !== 'application/pdf') {
        showError('Reference book must be a PDF file.');
        return false;
    }
    
    if (syllabusFile.type !== 'application/pdf') {
        showError('Syllabus must be a PDF file.');
        return false;
    }
    
    return true;
}

function startProcessing() {
    hideAllSections();
    showLoadingState();
    
    const formData = new FormData(uploadForm);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentJobId = data.job_id;
        showProgressSection();
        startStatusPolling();
    })
    .catch(error => {
        console.error('Upload error:', error);
        showError(error.message || 'Failed to upload files. Please try again.');
        resetLoadingState();
    });
}

function showLoadingState() {
    generateButton.disabled = true;
    document.querySelector('.button-text').style.display = 'none';
    document.querySelector('.loading-spinner').style.display = 'block';
}

function resetLoadingState() {
    generateButton.disabled = false;
    document.querySelector('.button-text').style.display = 'block';
    document.querySelector('.loading-spinner').style.display = 'none';
}

function showProgressSection() {
    progressSection.style.display = 'block';
    updateProgress(0, 'Starting processing...');
}

function updateProgress(percentage, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = percentage + '%';
    progressText.textContent = message;
}

function startStatusPolling() {
    if (!currentJobId) return;
    
    statusInterval = setInterval(() => {
        fetch(`/api/status/${currentJobId}`)
        .then(response => response.json())
        .then(data => {
            handleStatusUpdate(data);
        })
        .catch(error => {
            console.error('Status polling error:', error);
            clearInterval(statusInterval);
            showError('Lost connection to server. Please refresh and try again.');
        });
    }, 2000);
}

function handleStatusUpdate(status) {
    switch(status.status) {
        case 'queued':
            updateProgress(5, 'Request queued...');
            break;
        case 'processing':
            updateProgress(15, status.current_step || 'Extracting text from PDFs...');
            break;
        case 'detecting_modules':
            updateProgress(25, status.current_step || 'Analyzing syllabus to detect modules...');
            break;
        case 'generating_questions':
            if (status.total_modules && status.completed_modules) {
                const moduleProgress = 30 + (status.completed_modules / status.total_modules) * 60;
                const message = `Generating questions for ${status.current_module || 'modules'} (${status.completed_modules}/${status.total_modules})`;
                updateProgress(moduleProgress, message);
                
                // Show module list if available
                if (status.modules && status.modules.length > 0) {
                    showModuleList(status.modules, status.completed_modules);
                }
            } else {
                updateProgress(50, status.current_step || 'Generating questions...');
            }
            break;
        case 'creating_excel':
            updateProgress(95, status.current_step || 'Creating Excel file...');
            break;
        case 'completed':
            updateProgress(100, 'Complete!');
            clearInterval(statusInterval);
            setTimeout(() => {
                showSuccess(status);
                resetLoadingState();
            }, 1000);
            break;
        case 'error':
            clearInterval(statusInterval);
            showError(status.error || 'An error occurred during processing.');
            resetLoadingState();
            break;
    }
}

function showModuleList(modules, completedCount) {
    const progressCard = document.querySelector('.progress-card');
    
    // Check if module list already exists
    let moduleList = progressCard.querySelector('.module-list');
    if (!moduleList) {
        moduleList = document.createElement('div');
        moduleList.className = 'module-list';
        moduleList.innerHTML = '<h4>Detected Modules:</h4>';
        progressCard.appendChild(moduleList);
    }
    
    // Update module list
    const moduleItems = modules.map((module, index) => {
        const status = index < completedCount ? '✅' : (index === completedCount ? '🔄' : '⏳');
        return `<div class="module-item ${index < completedCount ? 'completed' : index === completedCount ? 'current' : 'pending'}">
            ${status} ${module.module_id}: ${module.title}
        </div>`;
    }).join('');
    
    moduleList.innerHTML = '<h4>Detected Modules:</h4>' + moduleItems;
}

function showSuccess(status) {
    hideAllSections();
    resultSection.style.display = 'block';
    
    // Update success message with module info
    const resultCard = resultSection.querySelector('.result-card');
    if (status.modules && status.modules.length > 0) {
        const moduleCount = status.modules.length;
        const totalQuestions = status.total_modules * (parseInt(document.getElementById('mcqCount').value) + 
                                                      parseInt(document.getElementById('shortCount').value) + 
                                                      parseInt(document.getElementById('longCount').value));
        
        resultCard.querySelector('p').textContent = 
            `Your question bank has been created with ${moduleCount} modules and organized into separate Excel sheets for easy access.`;
    }
    
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.onclick = () => downloadFile(currentJobId);
    
    // Add celebration animation
    setTimeout(() => {
        resultCard.style.transform = 'scale(1.02)';
        setTimeout(() => {
            resultCard.style.transform = 'scale(1)';
        }, 200);
    }, 100);
}
function showSuccess() {
    hideAllSections();
    resultSection.style.display = 'block';
    
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.onclick = () => downloadFile(currentJobId);
    
    setTimeout(() => {
        const resultCard = document.querySelector('.result-card.success');
        resultCard.style.transform = 'scale(1.02)';
        setTimeout(() => {
            resultCard.style.transform = 'scale(1)';
        }, 200);
    }, 100);
}

function showError(message) {
    hideAllSections();
    errorSection.style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
    
    const errorCard = document.querySelector('.result-card.error');
    errorCard.style.animation = 'shake 0.5s ease-in-out';
    setTimeout(() => {
        errorCard.style.animation = '';
    }, 500);
}

function hideAllSections() {
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
}

function downloadFile(jobId) {
    const downloadUrl = `/api/download/${jobId}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'question_bank.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    const downloadButton = document.getElementById('downloadButton');
    const originalText = downloadButton.textContent;
    downloadButton.textContent = 'Downloaded! ✓';
    downloadButton.style.backgroundColor = 'var(--success-color)';
    
    setTimeout(() => {
        downloadButton.textContent = originalText;
        downloadButton.style.backgroundColor = 'var(--accent-primary)';
    }, 2000);
}

function resetForm() {
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
    
    uploadForm.reset();
    currentJobId = null;
    
    hideAllSections();
    resetLoadingState();
    
    document.getElementById('referenceName').textContent = '';
    document.getElementById('syllabusName').textContent = '';
    
    const uploadCards = document.querySelectorAll('.upload-card');
    uploadCards.forEach(card => {
        card.style.borderColor = 'var(--border-color)';
        card.style.backgroundColor = 'var(--bg-secondary)';
    });
    
    scrollToUpload();
}

function scrollToUpload() {
    document.getElementById('upload').scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    .upload-card.drag-over {
        border-color: var(--accent-primary) !important;
        background-color: rgba(16, 163, 127, 0.2) !important;
        transform: scale(1.02);
    }
    
    .upload-area {
        cursor: pointer;
    }
`;
document.head.appendChild(style);

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add scroll effects to navbar
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.backgroundColor = 'rgba(0, 0, 0, 0.95)';
    } else {
        navbar.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    }
});
