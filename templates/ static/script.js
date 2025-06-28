document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    
    if (!file) {
        alert("Please select a CSV file!");
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending...";
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    const resultsTable = document.getElementById('resultsTable');
    resultsTable.innerHTML = '<tr><td colspan="3">Sending messages...</td></tr>';
    
    try {
        const response = await fetch('/send_messages', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Clear loading message
        resultsTable.innerHTML = '';
        
        // Display each result
        data.results.forEach(result => {
            const row = document.createElement('tr');
            
            const phoneCell = document.createElement('td');
            phoneCell.textContent = result.phone;
            
            const statusCell = document.createElement('td');
            statusCell.textContent = result.status;
            statusCell.className = result.status.includes('✅') ? 'status-success' : 'status-failed';
            
            const messageCell = document.createElement('td');
            messageCell.textContent = result.message;
            
            row.appendChild(phoneCell);
            row.appendChild(statusCell);
            row.appendChild(messageCell);
            resultsTable.appendChild(row);
        });
        
    } catch (error) {
        alert("Error: " + error.message);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send WhatsApp Messages";
    }
});