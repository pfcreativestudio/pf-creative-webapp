// PF Creative WebApp - Script Generator Logic
console.log("PF Creative WebApp loaded.");

document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const copyBtn = document.getElementById('copyBtn');
    const resultDiv = document.getElementById('result');
    const resultContainer = document.getElementById('result-container');
    const loadingDiv = document.getElementById('loading');

    // --- Configuration Area ---
    // The backend URL configured with the deployed Google Cloud Function
    const BACKEND_URL = 'https://asia-southeast1-pf-studio-prod.cloudfunctions.net/pfsystem-api';
    // --- End Configuration Area ---

    generateBtn.addEventListener('click', async () => {
        const brandName = document.getElementById('brandName').value;
        const productName = document.getElementById('productName').value;
        const targetAudience = document.getElementById('targetAudience').value;

        if (!brandName || !productName || !targetAudience) {
            alert('Please fill in all project information!');
            return;
        }

        const projectInfo = `

Part 3: [YOUR PROJECT INFORMATION]
Brand Name: [${brandName}]

Product Name: [${productName}]

Target Audience: [${targetAudience}]

Target Culture (Optional): []

Core Advantages: []

Offer & CTA: []

Avatar Concept (if applicable): []

Director's Vision (Overall Tone & Mood): []
`;

        loadingDiv.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_info: projectInfo }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            resultDiv.textContent = data.result;
            resultContainer.classList.remove('hidden');

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

