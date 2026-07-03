const fileInput = document.getElementById('resume-file');
const analyzeBtn = document.getElementById('analyze-btn');
const resetBtn = document.getElementById('reset-btn');
const fileNameBox = document.getElementById('file-name');
const uploadTitle = document.getElementById('upload-title');
const uploadText = document.getElementById('upload-text');
const uploadIcon = document.getElementById('upload-icon');
const uploadArea = document.getElementById('drop-zone');
const selectionStatus = document.getElementById('selection-status');
const uploadForm = document.getElementById('ats-upload-form');
const loadingPanel = document.getElementById('loading-panel');
const loadingText = document.getElementById('loading-text');
const progressBar = document.getElementById('progress-bar');

const loadingSteps = [
    'Scanning Resume...',
    'Reading Sections...',
    'Matching Keywords...',
    'Calculating ATS Score...',
    'Generating Suggestions...'
];

function updateUploadUI() {
    if (!fileInput) return;

    if (fileInput.files && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        fileNameBox.textContent = `${file.name} selected`;
        fileNameBox.classList.remove('hidden');
        uploadTitle.textContent = 'Resume selected';
        uploadText.textContent = 'You can change the file before analyzing.';
        uploadIcon.textContent = 'OK';
        uploadArea.classList.add('selected');
        selectionStatus.textContent = `${file.name} selected`;
        analyzeBtn.disabled = false;
    } else {
        fileNameBox.textContent = 'No file selected';
        fileNameBox.classList.add('hidden');
        uploadTitle.textContent = 'Drag and drop your resume';
        uploadText.textContent = 'or choose a PDF/DOCX file up to 5 MB';
        uploadIcon.textContent = 'DOC';
        uploadArea.classList.remove('selected');
        selectionStatus.textContent = 'No resume selected';
        analyzeBtn.disabled = true;
    }
}

if (fileInput) {
    fileInput.addEventListener('change', updateUploadUI);
}

if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        setTimeout(updateUploadUI, 0);
    });
}

if (uploadArea) {
    ['dragenter', 'dragover'].forEach((eventName) => {
        uploadArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadArea.classList.add('dragging');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        uploadArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadArea.classList.remove('dragging');
        });
    });

    uploadArea.addEventListener('drop', (event) => {
        if (event.dataTransfer.files.length) {
            fileInput.files = event.dataTransfer.files;
            updateUploadUI();
        }
    });
}

if (uploadForm) {
    uploadForm.addEventListener('submit', () => {
        loadingPanel.classList.remove('hidden');
        loadingPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        let step = 0;
        loadingText.textContent = loadingSteps[0];
        progressBar.style.width = '8%';

        setInterval(() => {
            step = Math.min(step + 1, loadingSteps.length - 1);
            loadingText.textContent = loadingSteps[step];
            progressBar.style.width = `${20 + step * 20}%`;
        }, 650);
    });
}

updateUploadUI();
