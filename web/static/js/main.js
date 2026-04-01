/**
 * Aether Tickets Web UI - Main JavaScript
 */

// Utility Functions

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    const toastHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.querySelector('main') || document.body;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = toastHtml;
    container.insertBefore(wrapper.firstElementChild, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}

/**
 * Make an API request
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(endpoint, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'API request failed');
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Update ticket status via AJAX
 */
async function updateTicketStatus(ticketId, newStatus, reason = '') {
    try {
        const result = await apiRequest(
            `/api/tickets/${ticketId}/status`,
            'POST',
            { status: newStatus, reason: reason }
        );

        showToast(result.message || 'Ticket updated successfully', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showToast(error.message || 'Failed to update ticket', 'danger');
    }
}

/**
 * Claim a ticket via AJAX
 */
async function claimTicket(ticketId) {
    try {
        const result = await apiRequest(
            `/api/tickets/${ticketId}/claim`,
            'POST'
        );

        showToast(result.message || 'Ticket claimed successfully', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showToast(error.message || 'Failed to claim ticket', 'danger');
    }
}

/**
 * Unclaim a ticket via AJAX
 */
async function unclaimTicket(ticketId) {
    try {
        const result = await apiRequest(
            `/api/tickets/${ticketId}/unclaim`,
            'POST'
        );

        showToast(result.message || 'Ticket unclaimed successfully', 'success');
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        showToast(error.message || 'Failed to unclaim ticket', 'danger');
    }
}

/**
 * Format date to readable format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('en-US', options);
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

    return formatDate(dateString);
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy', 'danger');
    });
}

/**
 * Debounce function for search
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Initialize tooltips and popovers
 */
function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Event Listeners

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Bootstrap components
    initializeBootstrapComponents();

    // Real-time search filter (if present)
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function () {
            // Optional: Implement real-time filtering without form submission
            // For now, submit the form on Enter
        }, 300));
    }

    // Copy ID to clipboard on click
    document.querySelectorAll('[data-copy]').forEach(element => {
        element.style.cursor = 'pointer';
        element.addEventListener('click', function () {
            copyToClipboard(this.getAttribute('data-copy'));
        });
    });

    // Close alert messages
    document.querySelectorAll('.alert').forEach(alert => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                alert.remove();
            });
        }
    });
});

// Export functions for use in templates
window.Aether = {
    updateTicketStatus,
    claimTicket,
    unclaimTicket,
    showToast,
    copyToClipboard,
    formatDate,
    formatRelativeTime,
    apiRequest
};
