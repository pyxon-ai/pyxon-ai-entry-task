// API Base URL
const API_BASE = window.location.origin;

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const documentsList = document.getElementById('documentsList');
const refreshBtn = document.getElementById('refreshBtn');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const topKSelect = document.getElementById('topK');
const searchResults = document.getElementById('searchResults');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
    
    // Refresh button
    refreshBtn.addEventListener('click', loadDocuments);
    
    // Search button
    searchBtn.addEventListener('click', performSearch);
    
    // Search on Enter
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

// Handle file selection
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

// Upload file
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showStatus('Uploading and processing document...', 'loading');
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        showStatus(`✅ Success! Processed ${data.total_chunks} chunks using ${data.chunking_strategy} strategy`, 'success');
        
        // Reload documents
        setTimeout(() => {
            loadDocuments();
            fileInput.value = '';
        }, 1500);
        
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Show upload status
function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `upload-status ${type}`;
    uploadStatus.style.display = 'block';
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 5000);
    }
}

// Load documents
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/api/documents/`);
        const documents = await response.json();
        
        if (documents.length === 0) {
            documentsList.innerHTML = '<p class="empty-state">No documents yet. Upload one to get started!</p>';
            return;
        }
        
        documentsList.innerHTML = documents.map(doc => `
            <div class="document-item">
                <div class="document-header">
                    <div>
                        <div class="document-title">📄 ${doc.filename}</div>
                        <div class="document-meta">
                            <span class="meta-badge">🌐 ${doc.language}</span>
                            <span class="meta-badge">📊 ${doc.total_chunks} chunks</span>
                            <span class="meta-badge">🔧 ${doc.chunking_strategy}</span>
                            <span class="meta-badge">📏 ${formatFileSize(doc.file_size)}</span>
                        </div>
                    </div>
                    <button class="btn-delete" onclick="deleteDocument('${doc.id}')">🗑️ Delete</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading documents:', error);
        documentsList.innerHTML = '<p class="empty-state">Error loading documents</p>';
    }
}

// Delete document
async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/${documentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadDocuments();
        } else {
            alert('Failed to delete document');
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        alert('Error deleting document');
    }
}

// Perform search
async function performSearch() {
    const query = searchInput.value.trim();
    
    if (!query) {
        alert('Please enter a search query');
        return;
    }
    
    searchResults.innerHTML = '<div class="spinner"></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/query/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topKSelect.value)
            })
        });
        
        const data = await response.json();
        
        if (data.results.length === 0) {
            searchResults.innerHTML = '<p class="empty-state">No results found</p>';
            return;
        }
        
        searchResults.innerHTML = `
            <div style="margin-bottom: 1rem; color: var(--text-secondary);">
                Found ${data.total_results} results in ${data.processing_time}s
            </div>
            ${data.results.map((result, index) => `
                <div class="result-item">
                    <div class="result-header">
                        <div>
                            <strong>📄 ${result.document_name}</strong>
                            <span style="color: var(--text-secondary); margin-left: 1rem;">Chunk #${result.chunk_index + 1}</span>
                        </div>
                        <div class="result-score">${(result.similarity_score * 100).toFixed(1)}%</div>
                    </div>
                    <div class="result-text">${highlightText(result.chunk_text, query)}</div>
                </div>
            `).join('')}
        `;
        
    } catch (error) {
        console.error('Error searching:', error);
        searchResults.innerHTML = '<p class="empty-state">Error performing search</p>';
    }
}

// Highlight search terms
function highlightText(text, query) {
    // Simple highlighting - can be improved
    const words = query.split(' ').filter(w => w.length > 2);
    let highlighted = text;
    
    words.forEach(word => {
        const regex = new RegExp(`(${word})`, 'gi');
        highlighted = highlighted.replace(regex, '<mark style="background: rgba(99, 102, 241, 0.3); padding: 2px 4px; border-radius: 3px;">$1</mark>');
    });
    
    return highlighted;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
