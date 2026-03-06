const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadSection = document.querySelector('.upload-section');
const processingSection = document.getElementById('processing-section');
const resultsSection = document.getElementById('results-section');
const resultsBody = document.getElementById('results-body');
const processingStatus = document.getElementById('processing-status');
const exportExcelBtn = document.getElementById('export-excel-btn');

let extractedData = [];
const API_BASE = 'http://127.0.0.1:8000';

// Event Listeners for Drag and Drop
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
    if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        handleFiles(fileInput.files);
    }
});

async function handleFiles(files) {
    uploadSection.classList.add('hidden');
    processingSection.classList.remove('hidden');
    
    // Convert object to array
    const filesArray = Array.from(files);
    let completedCount = 0;
    
    // We process each file sequentially or in parallel
    for (let i = 0; i < filesArray.length; i++) {
        const file = filesArray[i];
        
        processingStatus.innerText = `Analyzing card ${i + 1} of ${filesArray.length}...`;
        
        try {
            await processSingleFile(file);
            completedCount++;
        } catch (error) {
            console.error('Error processing file:', file.name, error);
            // Show the actual error message from the backend
            alert(`Failed to process ${file.name}\n\nError: ${error.message}\n\nCheck the backend console for more details.`);
        }
    }
    
    if (completedCount > 0) {
        processingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        renderTable();
    } else {
        // If all failed, go back
        processingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
    }
}

async function processSingleFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/extract`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        let msg = await response.text();
        throw new Error(msg || response.statusText);
    }
    
    const data = await response.json();
    
    // Create local object URL for preview
    const objectUrl = URL.createObjectURL(file);
    data._previewUrl = objectUrl;
    
    extractedData.push(data);
}

function renderTable() {
    resultsBody.innerHTML = '';
    
    extractedData.forEach((row, index) => {
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td>
                <img src="${row._previewUrl}" alt="Card Preview" class="preview-img" onclick="window.open('${row._previewUrl}', '_blank')" />
            </td>
            <td>${escapeHtml(row['Company name'] || '-')}</td>
            <td>${escapeHtml(row['Company owner name'] || '-')}</td>
            <td>${escapeHtml(row['phone number'] || '-')}</td>
            <td>${escapeHtml(row['email'] || '-')}</td>
            <td>${escapeHtml(row['Company address'] || '-')}</td>
            <td>${escapeHtml(row['city'] || '-')}</td>
            <td>${escapeHtml(row['state'] || '-')}</td>
            <td>${escapeHtml(row['pincode'] || '-')}</td>
            <td class="extra-col" title="${escapeHtml(row['extra'] || '')}">${escapeHtml(row['extra'] || '-')}</td>
        `;
        
        resultsBody.appendChild(tr);
    });
}

function escapeHtml(unsafe) {
    return (unsafe || '').toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Export to Excel
exportExcelBtn.addEventListener('click', async () => {
    try {
        const exportData = extractedData.map(item => {
            // copy item but remove internal fields
            const obj = { ...item };
            delete obj._previewUrl;
            delete obj._filename;
            return obj;
        });

        const response = await fetch(`${API_BASE}/export-excel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ data: exportData })
        });
        
        if (!response.ok) throw new Error('Export failed');
        
        // Handle Blob
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'visiting_cards.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
    } catch (error) {
        console.error('Export error:', error);
        alert('Failed to export to Excel.');
    }
});
