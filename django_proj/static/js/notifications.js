/**
 * Real-time notifications via Socket.io (Express server).
 * Broadcasts item events to every connected client.
 */
(function () {
    const EXPRESS_URL = window.EXPRESS_URL || 'http://localhost:3000';

    // ── Toast rendering ────────────────────────────────────────
    function escapeHtml(str) {
        return String(str ?? '').replace(/[&<>"']/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    function showToast(title, message, type) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type || 'info'}`;
        toast.innerHTML = `<strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('toast-hide');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // ── Socket connection ──────────────────────────────────────
    let socket;
    try {
        socket = io(EXPRESS_URL, { transports: ['websocket', 'polling'] });
    } catch (err) {
        console.warn('[notifications] Socket.io not available:', err);
        return;
    }

    socket.on('connect', () => console.log('[notifications] connected'));
    socket.on('connect_error', (err) => console.warn('[notifications] error:', err.message));

    // ── Event handlers ────────────────────────────────────────
    socket.on('item_reported', (data) => {
        const kind = data.type === 'lost' ? 'Lost' : 'Found';
        showToast('New Item Reported',
            `${kind}: "${data.name}" at ${data.location}`, 'info');
    });

    socket.on('item_claimed', (data) => {
        showToast('Item Claimed',
            `"${data.name}" was claimed by ${data.claimed_by || 'a user'}`, 'warning');
    });

    socket.on('item_resolved', (data) => {
        showToast('Item Resolved',
            `"${data.name}" has been resolved`, 'success');
    });

        socket.on('claim_requested', (data) => {
        showToast('New Claim Request', `${data.requester} wants to claim "${data.name}"`, 'warning');
    });

    socket.on('claim_approved', (data) => {
        showToast('Claim Approved', `The claim for "${data.name}" was approved!`, 'success');
    });

    socket.on('claim_declined', (data) => {
        showToast('Claim Declined', `The claim for "${data.name}" was declined.`, 'error');
    });
})();