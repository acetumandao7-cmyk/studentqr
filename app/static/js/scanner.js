let html5QrScanner = null;
let isProcessingScan = false;
let lastScannedPayload = null;
let lastScanTimestamp = 0;
const SCAN_COOLDOWN_MS = 2500; 

function startScanner() {
    if (html5QrScanner) {
        html5QrScanner.clear();
    }

    const config = {
        fps: 15,
        qrbox: { width: 260, height: 260 },
        aspectRatio: 1.0,
        experimentalFeatures: {
            useBarCodeDetectorIfSupported: true
        }
    };

    html5QrScanner = new Html5QrcodeScanner("reader", config,  false);
    html5QrScanner.render(onScanSuccess, onScanFailure);
}

function onScanFailure(error) {

}

function onScanSuccess(decodedText, decodedResult) {
    const now = Date.now();

    if (decodedText === lastScannedPayload && (now - lastScanTimestamp) < SCAN_COOLDOWN_MS) {
        return;
    }

    if (isProcessingScan) return;

    lastScannedPayload = decodedText;
    lastScanTimestamp = now;

    processAttendancePayload(decodedText, false);
}

async function processAttendancePayload(payload, isManual) {
    const sessionSelect = document.getElementById('session-select');
    const sessionId = sessionSelect ? sessionSelect.value : null;

    if (!sessionId) {
        showStatusCard({
            success: false,
            title: 'Missing Session',
            message: 'Please choose an attendance session schedule above.',
            type: 'warning'
        });
        AudioFeedback.playWarning();
        return;
    }

    isProcessingScan = true;
    updateScanningIndicator(true);

    try {
        const response = await fetch('/attendance/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                qr_payload: payload,
                session_id: parseInt(sessionId, 10),
                manual_override: isManual
            })
        });

        const data = await response.json();

        if (response.status === 201 && data.success) {

            AudioFeedback.playSuccess();
            showStatusCard({
                success: true,
                title: `${data.status.toUpperCase()}`,
                message: data.message,
                student: data.student,
                timestamp: data.timestamp,
                status: data.status
            });
            prependToRecentScans(data);
        } else if (response.status === 409) {

            AudioFeedback.playWarning();
            showStatusCard({
                success: false,
                title: 'DUPLICATE ENTRY',
                message: data.message,
                student: data.student,
                status: 'Duplicate',
                type: 'warning'
            });
        } else {

            AudioFeedback.playWarning();
            showStatusCard({
                success: false,
                title: 'SCAN REJECTED',
                message: data.message || 'Student QR Code invalid or inactive.',
                type: 'danger'
            });
        }
    } catch (err) {
        console.error('Scan API Network Error:', err);
        AudioFeedback.playWarning();
        showStatusCard({
            success: false,
            title: 'Connection Error',
            message: 'Unable to reach the server. Please check your network.',
            type: 'danger'
        });
    } finally {
        isProcessingScan = false;
        updateScanningIndicator(false);
    }
}

function updateScanningIndicator(active) {
    const indicator = document.getElementById('scan-indicator');
    if (indicator) {
        indicator.textContent = active ? 'Processing scan...' : 'Camera active. Position QR code inside the box.';
        indicator.style.color = active ? '#34d399' : '#94a3b8';
    }
}

function showStatusCard(options) {
    const resultBox = document.getElementById('scan-result-box');
    if (!resultBox) return;

    if (options.success) {
        const statusClass = options.status.toLowerCase() === 'present' ? 'badge-present' : 'badge-late';
        resultBox.innerHTML = `
            <div style="border-left: 4px solid var(--success); padding: 1.25rem; background: #f0fdf4; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span class="badge ${statusClass}" style="font-size: 0.85rem;">${options.title}</span>
                    <span style="font-size: 0.8rem; color: #64748b; font-weight: 600;">${options.timestamp}</span>
                </div>
                <h3 style="font-size: 1.15rem; font-weight: 800; color: #0f172a; margin-bottom: 0.25rem;">
                    ${options.student ? options.student.full_name : 'Verified'}
                </h3>
                <div style="font-size: 0.85rem; color: #475569; margin-bottom: 0.5rem;">
                    <strong>ID:</strong> ${options.student ? options.student.student_id : 'N/A'} &bull; 
                    <strong>Section:</strong> ${options.student ? options.student.section : 'N/A'}
                </div>
                <p style="font-size: 0.85rem; color: #166534; font-weight: 500;">
                    ${options.message}
                </p>
            </div>
        `;
    } else {
        const borderCol = options.type === 'warning' ? '#f59e0b' : '#ef4444';
        const bgCol = options.type === 'warning' ? '#fffbeb' : '#fef2f2';
        const textCol = options.type === 'warning' ? '#92400e' : '#991b1b';
        const badgeClass = options.type === 'warning' ? 'badge-late' : 'badge-absent';

        resultBox.innerHTML = `
            <div style="border-left: 4px solid ${borderCol}; padding: 1.25rem; background: ${bgCol}; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span class="badge ${badgeClass}" style="font-size: 0.85rem;">${options.title}</span>
                </div>
                ${options.student ? `
                    <h4 style="font-size: 1rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem;">
                        ${options.student.full_name} (${options.student.student_id})
                    </h4>
                ` : ''}
                <p style="font-size: 0.875rem; color: ${textCol}; font-weight: 600;">
                    ${options.message}
                </p>
            </div>
        `;
    }
}

function prependToRecentScans(data) {
    const tbody = document.getElementById('recent-scans-body');
    if (!tbody) return;

    const emptyRow = document.getElementById('no-scans-row');
    if (emptyRow) emptyRow.remove();

    const row = document.createElement('tr');
    const badgeClass = data.status.toLowerCase() === 'present' ? 'badge-present' : 'badge-late';

    row.innerHTML = `
        <td style="font-weight: 600;">${data.timestamp}</td>
        <td style="font-family: monospace; font-size: 0.85rem;">${data.student.student_id}</td>
        <td style="font-weight: 700;">${data.student.full_name}</td>
        <td>${data.student.section}</td>
        <td><span class="badge ${badgeClass}">${data.status}</span></td>
    `;

    row.style.backgroundColor = '#dcfce7';
    tbody.insertBefore(row, tbody.firstChild);

    setTimeout(() => {
        row.style.transition = 'background-color 1.5s ease';
        row.style.backgroundColor = '';
    }, 1500);

    while (tbody.children.length > 10) {
        tbody.removeChild(tbody.lastChild);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    startScanner();

    const manualForm = document.getElementById('manual-scan-form');
    if (manualForm) {
        manualForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('manual-id-input');
            const val = input ? input.value.trim() : '';
            if (val) {
                processAttendancePayload(val, true);
                input.value = '';
            }
        });
    }
});
