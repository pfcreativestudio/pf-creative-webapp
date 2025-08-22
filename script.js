// PF Creative WebApp - Script Generator Logic
console.log("PF Creative WebApp loaded.");

document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const resultDiv = document.getElementById('result');
    const resultContainer = document.getElementById('result-container');
    const loadingDiv = document.getElementById('loading');

    // --- Configuration Area ---
    const BACKEND_URL = 'https://pfsystem-api-902383636494.asia-southeast1.run.app';
    // --- End Configuration Area ---

    generateBtn.addEventListener('click', async () => {
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            alert('Please log in to generate a script.');
            return;
        }

        const brandName = document.getElementById('brandName').value;
        const productName = document.getElementById('productName').value;
        const targetAudience = document.getElementById('targetAudience').value;

        // Simple validation
        if (!brandName || !productName || !targetAudience) {
            alert('Please fill in all project information!');
            return;
        }

        loadingDiv.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            // ==========================================================
            // === START: MODIFICATIONS FOR NEW MULTI-AGENT WORKFLOW ===
            // ==========================================================
            const apiUrl = `${BACKEND_URL}/v1/projects`;
            
            // Create the structured payload required by the new endpoint
            const payload = {
                "project_title": `Video for ${productName}`,
                "video_length_sec": 30, // Using a default value, can be an input field later
                "user_input": {
                    "brandName": brandName,
                    "productName": productName,
                    "targetAudience": targetAudience
                }
            };

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload),
            });
            // ========================================================
            // === END: MODIFICATIONS FOR NEW MULTI-AGENT WORKFLOW ===
            // ========================================================

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.detail || `HTTP error! status: ${response.status}`);
            }

            // ==========================================================
            // === START: MODIFICATIONS FOR NEW RESPONSE FORMAT ===
            // ==========================================================
            // The new response is an object with a 'creative_options' array.
            // We need to format this array into a readable string.
            const options = data.creative_options;
            let formattedResponse = `Project ID: ${data.project_id}\n\nHere are your 3 creative options:\n\n`;
            options.forEach((opt, index) => {
                formattedResponse += `----------------------------------------\n`;
                formattedResponse += `OPTION ${index + 1}: ${opt.title}\n`;
                formattedResponse += `----------------------------------------\n`;
                formattedResponse += `Logline: ${opt.logline}\n`;
                formattedResponse += `Why it works: ${opt.why_it_works}\n\n`;
            });

            resultDiv.textContent = formattedResponse;
            resultContainer.classList.remove('hidden');
            // ========================================================
            // === END: MODIFICATIONS FOR NEW RESPONSE FORMAT ===
            // ========================================================

        } catch (error) {
            resultDiv.textContent = 'Error occurred:\n' + error.message;
            resultContainer.classList.remove('hidden');
        } finally {
            loadingDiv.classList.add('hidden');
            generateBtn.disabled = false;
            generateBtn.textContent = '🚀 Generate My Veo 3 Script';
        }
    });

    copyBtn.addEventListener('click', () => {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(resultDiv.textContent).then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = '📋 Copy Script'; }, 2000);
            }).catch(err => {
                alert('Copy failed: ', err);
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = resultDiv.textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            copyBtn.textContent = 'Copied!';
            setTimeout(() => { copyBtn.textContent = '📋 Copy Script'; }, 2000);
        }
    });
});