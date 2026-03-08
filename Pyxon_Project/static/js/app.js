document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const statusMsg = document.getElementById('upload-status');
    const queryInput = document.getElementById('query-input');
    const fileSelect = document.getElementById('file-select');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');

    // --- Upload Handlers ---
    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    function handleFileUpload(file) {
        statusMsg.textContent = 'Uploading and processing ' + file.name + '...';
        statusMsg.className = 'status-msg';

        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                statusMsg.textContent = `✅ ${file.name} processed successfully! (${data.total_chunks} chunks stored)`;
                statusMsg.className = 'status-msg success';

                // Refresh the dropdown so the new file is immediately clickable
                fetchDocuments();
            })
            .catch(err => {
                statusMsg.textContent = `❌ Error: ${err.message}`;
                statusMsg.className = 'status-msg error';
            });
    }

    // --- Search Handlers ---
    function fetchDocuments() {
        fetch('/documents')
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);

                // Clear existing options except 'All Files'
                fileSelect.innerHTML = '<option value="All Files">All Files</option>';

                data.documents.forEach(doc => {
                    const option = document.createElement('option');
                    option.value = doc;
                    option.textContent = doc;
                    fileSelect.appendChild(option);
                });
            })
            .catch(err => console.error("Could not fetch documents for dropdown:", err));
    }

    function performSearch() {
        const query = queryInput.value.trim();
        const selectedFile = fileSelect.value;

        if (!query) {
            alert('Please enter a question to search for.');
            return;
        }

        searchBtn.textContent = 'Searching...';
        searchBtn.disabled = true;
        resultsContainer.innerHTML = '<div class="placeholder-text">Searching knowledge base...</div>';

        fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                filter_file: selectedFile
            })
        })
            .then(response => response.json())
            .then(data => {
                searchBtn.textContent = 'Search';
                searchBtn.disabled = false;

                if (data.error) throw new Error(data.error);
                renderResults(data.results, data.quality_score);
            })
            .catch(err => {
                searchBtn.textContent = 'Search';
                searchBtn.disabled = false;
                resultsContainer.innerHTML = `<div class="status-msg error">❌ Search Failed: ${err.message}</div>`;
            });
    }

    function renderResults(results, qualityScore) {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<div class="placeholder-text">No relevant answers found. Try rephrasing your question.</div>';
            return;
        }

        resultsContainer.innerHTML = `
            <div class="quality-badge">Overall Chunk Quality: ${qualityScore}%</div>
        `;

        results.forEach((res, index) => {
            const card = document.createElement('div');
            card.className = 'result-card';

            // Format text beautifully, handling raw newlines
            const formattedText = res.text.replace(/\\n/g, '<br>');

            card.innerHTML = `
                <div class="result-meta">
                    <span>Result #${index + 1}</span>
                    <span>📄 ${res.filename} (Chunk ${res.chunk_index})</span>
                </div>
                <!-- dir="auto" is the magic that handles Arabic RTL alignment cleanly inline -->
                <div class="result-content" dir="auto">
                    ${formattedText}
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    }

    searchBtn.addEventListener('click', performSearch);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // Load documents on startup
    fetchDocuments();
});
