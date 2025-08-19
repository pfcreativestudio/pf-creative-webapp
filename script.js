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
    const BACKEND_URL = 'https://pfsystem-api-902383636494.asia-southeast1.run.app';
    // --- End Configuration Area ---

    generateBtn.addEventListener('click', async () => {
        // [!!] 安全更新：检查用户是否已登录
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            alert('Please log in to generate a script.');
            // 可选：跳转到登录页面
            // window.location.href = '/login.html'; 
            return;
        }

        const brandName = document.getElementById('brandName').value;
        const productName = document.getElementById('productName').value;
        const targetAudience = document.getElementById('targetAudience').value;

        if (!brandName || !productName || !targetAudience) {
            alert('Please fill in all project information!');
            return;
        }

        // [!!] 修正：后端现在只需要核心信息，由它来组装完整的 prompt。
        // 我们只发送用户输入的核心数据。
        const projectInfo = `Brand Name: ${brandName}\nProduct Name: ${productName}\nTarget Audience: ${targetAudience}`;

        loadingDiv.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            // [!!] 逻辑修正：使用正确的 API 端点
            const apiUrl = `${BACKEND_URL}/generate-script`;
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    // [!!] 安全更新：在请求头中附带 JWT 令牌
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ project_info: projectInfo }),
            });

            const data = await response.json();

            if (!response.ok) {
                // 后端可能会返回具体的错误信息，如 "Active subscription required"
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            // [!!] 逻辑修正：根据后端 /generate-script 的返回格式，结果在 data.script 中
            resultDiv.textContent = data.script;
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
