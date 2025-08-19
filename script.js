// script.js - fixed full version

const BACKEND_URL = "https://asia-southeast1-pf-studio-prod.cloudfunctions.net/pfsystem-api";

// Utility: get stored JWT
function getAuthHeaders() {
    const token = localStorage.getItem("jwtToken");
    const headers = {
        "Content-Type": "application/json"
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

// Example: Generate Script button click
async function generateScript(promptText) {
    try {
        const response = await fetch(`${BACKEND_URL}/generate-script`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ prompt: promptText })
        });

        if (!response.ok) {
            throw new Error("Failed to generate script: " + response.status);
        }

        const data = await response.json();
        console.log("Generated script:", data);
        // 在页面显示结果
        document.getElementById("scriptOutput").textContent = data.script || "No script generated.";
    } catch (err) {
        console.error("Error generating script:", err);
        alert("Error generating script. Please try again.");
    }
}

// Example: Payment (保持原样)
async function createPaymentPlan(planId) {
    try {
        const response = await fetch(`${BACKEND_URL}/create-bill`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ planId })
        });

        if (!response.ok) {
            throw new Error("Payment request failed: " + response.status);
        }

        const data = await response.json();
        if (data.url) {
            window.location.href = data.url;
        } else {
            alert("Error creating payment link.");
        }
    } catch (err) {
        console.error("Error creating payment:", err);
        alert("Error creating payment. Please try again.");
    }
}

// DOM 绑定示例
document.addEventListener("DOMContentLoaded", () => {
    const genBtn = document.getElementById("generateBtn");
    if (genBtn) {
        genBtn.addEventListener("click", () => {
            const promptText = document.getElementById("promptInput").value;
            generateScript(promptText);
        });
    }

    const payBtns = document.querySelectorAll(".payBtn");
    payBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const planId = btn.dataset.plan;
            createPaymentPlan(planId);
        });
    });
});
