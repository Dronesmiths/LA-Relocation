/**
 * LA Relocation CRM - Google Apps Script Integration
 * Handles modal logic and form POST submissions for Inbound, Outbound, and Services leads.
 */

const CRM_WEBAPP_URL = "YOUR_GOOGLE_APPS_SCRIPT_URL_HERE"; // User will provide this

// Elements
const modalOverlay = document.getElementById("relocationModalOverlay");
const inboundForm = document.getElementById("inboundFormContainer");
const outboundForm = document.getElementById("outboundFormContainer");
const serviceForm = document.getElementById("serviceFormContainer");

/** Open specific relocation modal */
function openRelocationModal(type) {
    if (!modalOverlay) return;

    // Hide all first
    inboundForm.style.display = 'none';
    outboundForm.style.display = 'none';
    serviceForm.style.display = 'none';

    // Show requested
    if (type === 'inbound') inboundForm.style.display = 'block';
    if (type === 'outbound') outboundForm.style.display = 'block';
    if (type === 'services') serviceForm.style.display = 'block';

    modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden'; // prevent bg scroll
}

/** Close Modal */
function closeRelocationModal() {
    if (!modalOverlay) return;
    modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

/** Handle Form Submission via Fetch API */
async function handleRelocationSubmit(event, formType) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerText;

    // Loading State
    submitBtn.innerText = "Sending...";
    submitBtn.disabled = true;

    // Build Payload
    const formData = new FormData(form);
    const payload = { formType: formType };
    formData.forEach((value, key) => {
        payload[key] = value;
    });

    try {
        const response = await fetch(CRM_WEBAPP_URL, {
            method: 'POST',
            redirect: 'follow', // App Scripts require follow for CORS redirect
            headers: {
                'Content-Type': 'text/plain;charset=utf-8' // required for App script bypassing Preflight
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.status === 'success') {
            form.innerHTML = `<div class="success-message"><h3>Success!</h3><p>Your request has been securely sent directly to Carol Anderson. She will be in touch shortly!</p></div>`;
            setTimeout(closeRelocationModal, 4000);
        } else {
            alert("Error sending request: " + result.message);
            submitBtn.innerText = originalText;
            submitBtn.disabled = false;
        }

    } catch (error) {
        console.error("CRM Error:", error);
        alert("Network error connecting to the secure CRM. Please try again or call the office directly.");
        submitBtn.innerText = originalText;
        submitBtn.disabled = false;
    }
}

// Global Exports
window.openRelocationModal = openRelocationModal;
window.closeRelocationModal = closeRelocationModal;
window.handleRelocationSubmit = handleRelocationSubmit;

// 📊 HUD FILTER LOGIC (Algorithmic Matcher)
function hudFilter(category, btnElement) {
    // 1. Update Active state on buttons
    document.querySelectorAll('.hud-filter').forEach(btn => btn.classList.remove('matcher-active'));
    btnElement.classList.add('matcher-active');

    // 2. Filter Grid Items
    const items = document.querySelectorAll('.hud-item');
    items.forEach(item => {
        // Reset states
        item.classList.remove('dimmed', 'highlighted');

        if (category === 'all') {
            // Do nothing, leave default
        } else {
            // Check if item has the correct target class (e.g. hud-commute)
            if (item.classList.contains('hud-' + category)) {
                item.classList.add('highlighted');
            } else {
                item.classList.add('dimmed');
            }
        }
    });
}
window.hudFilter = hudFilter;

// 📊 LIVE TELEMETRY TICKER MOCKUP
document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => {
        document.querySelectorAll('.crypto-ticker').forEach(ticker => {
            let currentVal = parseInt(ticker.innerText);
            if (isNaN(currentVal)) return;
            // Randomly tick up, down, or stay the same (-1, 0, 1)
            let change = Math.floor(Math.random() * 3) - 1;
            if (currentVal + change > 0) {
                ticker.innerText = currentVal + change;
            }
        });
    }, 2500); // Ticks every 2.5 seconds
});

// 📈 RELOCATION MORTGAGE API CALCULATOR LOGIC
function calculateAPI() {
    // 1. Get Values
    const price = parseInt(document.getElementById('home-price').value);
    const downPercent = parseInt(document.getElementById('down-payment').value);
    const rate = parseFloat(document.getElementById('interest-rate').value);

    // 2. Math
    const downPaymentAmount = price * (downPercent / 100);
    const principal = price - downPaymentAmount;

    // Monthly Interest Rate
    const r = (rate / 100) / 12;
    // 30 Year Fixed = 360 months
    const n = 360;

    // M = P [ i(1 + i)^n ] / [ (1 + i)^n - 1 ]
    let monthlyPI = 0;
    if (r > 0) {
        monthlyPI = principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    } else {
        monthlyPI = principal / n;
    }

    // Property Tax (Estimated 1.25% in LA County)
    const annualTax = price * 0.0125;
    const monthlyTax = annualTax / 12;

    const totalMonthly = monthlyPI + monthlyTax;

    // 3. Update DOM Displays
    document.getElementById('price-display').innerText = '$' + price.toLocaleString();
    document.getElementById('down-display').innerText = `${downPercent}% ($${downPaymentAmount.toLocaleString()})`;
    document.getElementById('rate-display').innerText = rate.toFixed(1) + '%';

    // Update Big Numbers
    document.getElementById('monthly-payment').innerText = '$' + Math.round(totalMonthly).toLocaleString();
    document.getElementById('pi-breakdown').innerText = '$' + Math.round(monthlyPI).toLocaleString();
    document.getElementById('tax-breakdown').innerText = '$' + Math.round(monthlyTax).toLocaleString();
}

// Run once on load to populate defaults
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('home-price')) {
        calculateAPI();
    }
});
