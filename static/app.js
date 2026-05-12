/* ============================================================
   ClearPass AI — Frontend Application Logic
   Handles multi-step form, camera capture, API calls, results
   ============================================================ */

const API = window.location.origin;

// --- State ---
let currentStep = 1;
let selfieB64 = null;
let cameraStream = null;

// --- Sample transaction data ---
const SAMPLE_TRANSACTIONS = [
    { amount: 150000, date: "2025-01-15", status: "successful", narration: "Salary January", type: "credit" },
    { amount: 45000,  date: "2025-01-20", status: "successful", narration: "Rent payment", type: "debit" },
    { amount: 160000, date: "2025-02-15", status: "successful", narration: "Salary February", type: "credit" },
    { amount: 12000,  date: "2025-02-18", status: "failed",     narration: "Loan repayment to QuickCredit", type: "debit" },
    { amount: 30000,  date: "2025-02-25", status: "successful", narration: "Groceries and utilities", type: "debit" },
    { amount: 155000, date: "2025-03-15", status: "successful", narration: "Salary March", type: "credit" },
    { amount: 50000,  date: "2025-03-20", status: "successful", narration: "Borrow from friend repay", type: "debit" },
    { amount: 170000, date: "2025-04-15", status: "successful", narration: "Salary April", type: "credit" },
    { amount: 8000,   date: "2025-04-22", status: "successful", narration: "Data subscription", type: "debit" },
    { amount: 165000, date: "2025-05-15", status: "successful", narration: "Salary May credit alert", type: "credit" },
];

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    checkServer();
    addTransaction();
    addTransaction();
    addTransaction();

    // Auto-generate device ID
    const devInput = document.getElementById("deviceId");
    if (devInput && !devInput.value) {
        devInput.value = "DEV-" + Math.random().toString(36).substring(2, 10).toUpperCase();
    }
});

async function checkServer() {
    const dot = document.getElementById("serverDot");
    const txt = document.getElementById("serverStatus");
    try {
        const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) });
        const d = await r.json();
        dot.className = "status-dot online";
        txt.textContent = "Models loaded";
    } catch {
        dot.className = "status-dot offline";
        txt.textContent = "Server offline";
    }
}

// ============================================================
// STEP NAVIGATION
// ============================================================
function goToStep(n) {
    // Validate before advancing
    if (n > currentStep) {
        if (currentStep === 1 && !validateStep1()) return;
        if (currentStep === 2 && !validateStep2()) return;
    }

    document.querySelectorAll(".step-panel").forEach(p => p.classList.remove("active"));
    document.getElementById(`step${n}`).classList.add("active");

    document.querySelectorAll(".steps-bar .step").forEach(s => {
        const sn = parseInt(s.dataset.step);
        s.classList.remove("active", "done");
        if (sn === n) s.classList.add("active");
        else if (sn < n) s.classList.add("done");
    });

    currentStep = n;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function validateStep1() {
    const bvn = document.getElementById("bvn").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const address = document.getElementById("address").value.trim();
    if (!bvn || bvn.length < 10) { shakeField("bvn"); return false; }
    if (!phone || phone.length < 10) { shakeField("phone"); return false; }
    if (!address) { shakeField("address"); return false; }
    return true;
}

function validateStep2() {
    if (!selfieB64) { alert("Please capture or upload a selfie."); return false; }
    return true;
}

function shakeField(id) {
    const el = document.getElementById(id);
    el.style.borderColor = "var(--red)";
    el.style.animation = "shake 0.4s ease";
    el.focus();
    setTimeout(() => { el.style.borderColor = ""; el.style.animation = ""; }, 600);
}

// ============================================================
// CAMERA & IMAGE HANDLING
// ============================================================
async function startCamera() {
    try {
        let constraints = { video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 640 } } };
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (err) {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        }
        const video = document.getElementById("cameraFeed");
        video.srcObject = cameraStream;
        video.style.display = "block";
        try { await video.play(); } catch (e) { console.log("Play error:", e); }
        document.getElementById("selfiePreview").style.display = "none";
        document.getElementById("selfiePlaceholder").style.display = "none";
        document.getElementById("cameraBox").onclick = null; // disable click-to-upload while camera active
        document.getElementById("startCameraBtn").style.display = "none";
        document.getElementById("uploadSelfieBtn").style.display = "none";
        document.getElementById("captureBtn").style.display = "inline-flex";
        document.getElementById("retakeBtn").style.display = "none";
        document.getElementById("cameraOverlay").style.display = "flex";
    } catch (err) {
        console.error("Camera start error:", err);
        alert("Camera error: " + (err.name || "Unknown") + " - " + (err.message || "Access denied or not available."));
    }
}

function capturePhoto() {
    const video = document.getElementById("cameraFeed");
    const canvas = document.getElementById("cameraCanvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    selfieB64 = canvas.toDataURL("image/png").split(",")[1];

    const preview = document.getElementById("selfiePreview");
    preview.src = canvas.toDataURL("image/png");
    preview.style.display = "block";
    video.style.display = "none";
    document.getElementById("cameraOverlay").style.display = "none";

    // Stop camera
    if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());

    document.getElementById("captureBtn").style.display = "none";
    document.getElementById("retakeBtn").style.display = "inline-flex";
}

function retakePhoto() {
    selfieB64 = null;
    document.getElementById("selfiePreview").style.display = "none";
    document.getElementById("cameraFeed").style.display = "none";
    document.getElementById("cameraOverlay").style.display = "none";
    document.getElementById("selfiePlaceholder").style.display = "flex";
    document.getElementById("cameraBox").onclick = () => document.getElementById("selfieUpload").click();
    document.getElementById("retakeBtn").style.display = "none";
    document.getElementById("captureBtn").style.display = "none";
    document.getElementById("uploadSelfieBtn").style.display = "inline-flex";
    document.getElementById("startCameraBtn").style.display = "inline-flex";
    document.getElementById("selfieUpload").value = "";
    if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
}

function handleSelfieUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    fileToBase64(file, (b64, dataUrl) => {
        selfieB64 = b64;
        const preview = document.getElementById("selfiePreview");
        preview.src = dataUrl;
        preview.style.display = "block";
        document.getElementById("selfiePlaceholder").style.display = "none";
        document.getElementById("cameraFeed").style.display = "none";
        document.getElementById("cameraOverlay").style.display = "none";
        document.getElementById("cameraBox").onclick = null;
        document.getElementById("startCameraBtn").style.display = "none";
        document.getElementById("uploadSelfieBtn").style.display = "none";
        document.getElementById("captureBtn").style.display = "none";
        document.getElementById("retakeBtn").style.display = "inline-flex";
        if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());
    });
}


function fileToBase64(file, cb) {
    const reader = new FileReader();
    reader.onload = () => {
        const dataUrl = reader.result;
        const b64 = dataUrl.split(",")[1];
        cb(b64, dataUrl);
    };
    reader.readAsDataURL(file);
}

// ============================================================
// TRANSACTION MANAGEMENT
// ============================================================
let txCount = 0;

function addTransaction(data = null) {
    txCount++;
    const id = txCount;
    const list = document.getElementById("txList");
    const row = document.createElement("div");
    row.className = "tx-row";
    row.id = `tx-${id}`;
    row.innerHTML = `
        <div class="form-group">
            <label>Narration</label>
            <input type="text" class="tx-narration" placeholder="Salary, Rent..." value="${data?.narration || ""}">
        </div>
        <div class="form-group">
            <label>Amount (₦)</label>
            <input type="number" class="tx-amount" placeholder="150000" value="${data?.amount || ""}">
        </div>
        <div class="form-group">
            <label>Date</label>
            <input type="date" class="tx-date" value="${data?.date || ""}">
        </div>
        <div class="form-group">
            <label>Type</label>
            <select class="tx-type">
                <option value="credit" ${data?.type === "credit" ? "selected" : ""}>Credit</option>
                <option value="debit" ${data?.type === "debit" ? "selected" : ""}>Debit</option>
            </select>
        </div>
        <div class="form-group">
            <label>Status</label>
            <select class="tx-status">
                <option value="successful" ${data?.status === "successful" ? "selected" : ""}>OK</option>
                <option value="failed" ${data?.status === "failed" ? "selected" : ""}>Failed</option>
            </select>
        </div>
        <button class="tx-remove" onclick="removeTx(${id})">✕</button>
    `;
    list.appendChild(row);
}

function removeTx(id) {
    const el = document.getElementById(`tx-${id}`);
    if (el) el.remove();
}

function getTransactions() {
    // Check JSON tab first
    const jsonTab = document.getElementById("tab-json");
    if (jsonTab.classList.contains("active")) {
        try {
            return JSON.parse(document.getElementById("jsonInput").value);
        } catch {
            alert("Invalid JSON format");
            return null;
        }
    }

    // Manual entry
    const rows = document.querySelectorAll("#txList .tx-row");
    const txs = [];
    rows.forEach(row => {
        const narration = row.querySelector(".tx-narration").value.trim();
        const amount = parseFloat(row.querySelector(".tx-amount").value);
        const date = row.querySelector(".tx-date").value;
        const type = row.querySelector(".tx-type").value;
        const status = row.querySelector(".tx-status").value;
        if (narration && amount && date) {
            txs.push({ amount, date, status, narration, type });
        }
    });
    return txs;
}

function loadSampleData() {
    switchTab("manual");
    document.getElementById("txList").innerHTML = "";
    txCount = 0;
    SAMPLE_TRANSACTIONS.forEach(tx => addTransaction(tx));
}

function switchTab(name) {
    document.querySelectorAll(".tabs .tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    document.querySelector(`.tab-panel#tab-${name}`).classList.add("active");
    // Find matching button
    const tabs = document.querySelectorAll(".tabs .tab");
    const map = { manual: 0, json: 1, sample: 2 };
    if (map[name] !== undefined) tabs[map[name]].classList.add("active");
}

// ============================================================
// VERIFICATION API CALL
// ============================================================
async function runVerification() {
    const transactions = getTransactions();
    if (!transactions || transactions.length === 0) {
        alert("Please add at least one transaction.");
        return;
    }

    const payload = {
        bvn: document.getElementById("bvn").value.trim(),
        phone: document.getElementById("phone").value.trim(),
        device_id: document.getElementById("deviceId").value.trim(),
        address: document.getElementById("address").value.trim(),
        live_image_b64: selfieB64,
        transactions: transactions,
    };

    // Toggle loading state
    const btn = document.getElementById("verifyBtn");
    btn.querySelector(".btn-content").style.display = "none";
    btn.querySelector(".btn-loading").style.display = "flex";
    btn.disabled = true;

    try {
        const resp = await fetch(`${API}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await resp.json();

        if (resp.ok) {
            renderResults(data);
            goToStep(4);
        } else {
            renderError(data, resp.status);
            goToStep(4);
        }
    } catch (err) {
        renderError({ detail: err.message }, 0);
        goToStep(4);
    } finally {
        btn.querySelector(".btn-content").style.display = "flex";
        btn.querySelector(".btn-loading").style.display = "none";
        btn.disabled = false;
    }
}

// ============================================================
// RESULTS RENDERING
// ============================================================
function renderResults(data) {
    const score = data.trust_score ?? 0;
    const verdict = data.verdict ?? "BLOCK";
    const explanation = data.explanation ?? {};
    const faceScore = data.face_match_score;
    const timeMs = data.processing_time_ms;
    const cached = data.cached;

    // Determine color
    const colorMap = { PASS: "var(--green)", REVIEW: "var(--amber)", BLOCK: "var(--red)" };
    const color = colorMap[verdict] || "var(--text-muted)";

    // Score ring circumference
    const r = 80, circ = 2 * Math.PI * r;
    const offset = circ - (score / 100) * circ;

    // Model scores from explanation
    const behavior = explanation.behavior || [];
    const anomaly = explanation.anomaly || {};
    const graph = explanation.graph || {};

    const container = document.getElementById("resultsContent");
    container.innerHTML = `
        <div class="result-hero">
            <div class="score-ring">
                <svg viewBox="0 0 180 180">
                    <circle class="score-track" cx="90" cy="90" r="${r}"/>
                    <circle class="score-fill" cx="90" cy="90" r="${r}"
                        stroke="${color}"
                        stroke-dasharray="${circ}"
                        stroke-dashoffset="${circ}"
                        id="scoreArc"/>
                </svg>
                <div class="score-value">
                    <div class="score-number" style="color:${color}" id="scoreNum">0</div>
                    <div class="score-label">Trust Score</div>
                </div>
            </div>
            <div class="verdict-badge verdict-${verdict}">
                ${verdict === "PASS" ? "✅" : verdict === "REVIEW" ? "⚠️" : "🚫"}
                ${verdict}
            </div>
        </div>

        <div class="result-details">
            <div class="detail-card">
                <h4>🧠 Behavior Model</h4>
                <ul>
                    ${behavior.map(r => `<li>${r}</li>`).join("") || "<li>No data</li>"}
                </ul>
            </div>
            <div class="detail-card">
                <h4>👻 Ghost Borrower</h4>
                <div class="detail-score">${anomaly.anomaly_score?.toFixed(1) ?? "—"}<span style="font-size:0.5em;color:var(--text-muted)">/100</span></div>
                <span class="tag ${anomaly.is_ghost_borrower ? "tag-danger" : "tag-safe"}">
                    ${anomaly.is_ghost_borrower ? "⚠ GHOST DETECTED" : "✓ Legitimate"}
                </span>
            </div>
            <div class="detail-card">
                <h4>🔗 Fraud Graph</h4>
                <div class="detail-score">${graph.cluster_size ?? 1}</div>
                <p style="font-size:0.82rem;color:var(--text-dim)">Connected identities</p>
                <span class="tag ${graph.is_fraud_ring ? "tag-danger" : "tag-safe"}" style="margin-top:8px;display:inline-block">
                    ${graph.is_fraud_ring ? "⚠ FRAUD RING" : "✓ No ring detected"}
                </span>
            </div>
        </div>

        ${faceScore != null ? `
        <div class="result-meta" style="margin-top:20px">
            <span>🔍 Face Match: <strong>${(faceScore * 100).toFixed(1)}%</strong></span>
            <span>⏱ ${timeMs?.toFixed(0) ?? "—"}ms</span>
            ${cached ? '<span>📦 Cached</span>' : ''}
        </div>` : `
        <div class="result-meta" style="margin-top:20px">
            <span>⏱ ${timeMs?.toFixed(0) ?? "—"}ms</span>
            ${cached ? '<span>📦 Cached</span>' : ''}
        </div>`}
    `;

    // Animate score
    setTimeout(() => {
        document.getElementById("scoreArc").style.strokeDashoffset = offset;
        animateNumber("scoreNum", 0, score, 1200);
    }, 200);
}

function renderError(data, status) {
    const detail = data.detail ?? JSON.stringify(data);
    const reason = data.reason ?? "";
    const container = document.getElementById("resultsContent");

    if (reason === "biometric_mismatch" || (typeof detail === "string" && detail.includes("face"))) {
        container.innerHTML = `
            <div class="result-hero">
                <div class="score-ring">
                    <svg viewBox="0 0 180 180">
                        <circle class="score-track" cx="90" cy="90" r="80"/>
                    </svg>
                    <div class="score-value">
                        <div class="score-number" style="color:var(--red)">0</div>
                        <div class="score-label">Trust Score</div>
                    </div>
                </div>
                <div class="verdict-badge verdict-BLOCK">🚫 BLOCK</div>
            </div>
            <div class="error-box">
                <h3>Biometric Verification Failed</h3>
                <p>${detail}</p>
                <p style="margin-top:12px;font-size:0.82rem">Ensure both photos contain a clearly visible face.</p>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="error-box">
                <h3>Verification Error (${status})</h3>
                <p>${typeof detail === "string" ? detail : JSON.stringify(detail)}</p>
            </div>
        `;
    }
}

function animateNumber(id, from, to, duration) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = performance.now();
    function update(now) {
        const t = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(from + (to - from) * ease);
        if (t < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ============================================================
// RESET
// ============================================================
function resetForm() {
    selfieB64 = null;
    document.getElementById("bvn").value = "";
    document.getElementById("phone").value = "";
    document.getElementById("address").value = "";
    document.getElementById("deviceId").value = "DEV-" + Math.random().toString(36).substring(2, 10).toUpperCase();
    document.getElementById("selfiePreview").style.display = "none";
    document.getElementById("selfiePlaceholder").style.display = "flex";
    document.getElementById("cameraBox").onclick = () => document.getElementById("selfieUpload").click();
    document.getElementById("uploadSelfieBtn").style.display = "inline-flex";
    document.getElementById("startCameraBtn").style.display = "inline-flex";
    document.getElementById("captureBtn").style.display = "none";
    document.getElementById("retakeBtn").style.display = "none";
    document.getElementById("cameraFeed").style.display = "none";
    document.getElementById("cameraOverlay").style.display = "none";
    document.getElementById("selfieUpload").value = "";
    document.getElementById("txList").innerHTML = "";
    txCount = 0;
    addTransaction();
    addTransaction();
    addTransaction();
    goToStep(1);
}
