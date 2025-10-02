/**
 * Audit Logs Logic for AYUSH Terminology Bridge
 * Handles: Log viewing, filtering, export, pagination
 */

const API_BASE_URL = 'http://localhost:8000';

let currentLogs = [];
let currentPage = 1;
let logsPerPage = 50;
let filteredLogs = [];

// ============= INITIALIZATION =============

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication and permissions
    if (!requireAuth()) {
        return;
    }
    
    const userInfo = getUserInfo();
    if (!hasPermission('auditor')) {
        showNotification('You do not have permission to view audit logs', 'error');
        setTimeout(() => window.location.href = 'index.html', 2000);
        return;
    }
    
    // Set default dates
    setDefaultDates();
    
    // Load audit logs
    await loadAuditLogs();
});

// ============= SET DEFAULT DATES =============

function setDefaultDates() {
    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    
    document.getElementById('filter-date-to').valueAsDate = today;
    document.getElementById('filter-date-from').valueAsDate = weekAgo;
}

// ============= LOAD AUDIT LOGS =============

async function loadAuditLogs() {
    const limit = document.getElementById('filter-limit').value;
    const logsLoading = document.getElementById('logs-loading');
    const logsContainer = document.getElementById('logs-container');
    
    logsLoading.style.display = 'block';
    logsContainer.style.display = 'none';
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/audit/recent?limit=${limit}`);
        const data = await response.json();
        
        if (response.ok) {
            currentLogs = data.logs || [];
            filteredLogs = currentLogs;
            displayLogs();
        } else {
            showNotification('Failed to load audit logs', 'error');
        }
    } catch (error) {
        console.error('Audit logs load error:', error);
        showNotification('Network error loading logs', 'error');
    } finally {
        logsLoading.style.display = 'none';
        logsContainer.style.display = 'block';
    }
}

async function refreshLogs() {
    showNotification('Refreshing audit logs...', 'info');
    await loadAuditLogs();
    showNotification('Logs refreshed!', 'success');
}

// ============= APPLY FILTERS =============

function applyFilters() {
    const userFilter = document.getElementById('filter-user').value.toLowerCase();
    const actionFilter = document.getElementById('filter-action').value.toLowerCase();
    const dateFrom = document.getElementById('filter-date-from').value;
    const dateTo = document.getElementById('filter-date-to').value;
    
    filteredLogs = currentLogs.filter(log => {
        // User filter
        if (userFilter && !log.user_id?.toLowerCase().includes(userFilter)) {
            return false;
        }
        
        // Action filter
        if (actionFilter && !log.action_type?.toLowerCase().includes(actionFilter)) {
            return false;
        }
        
        // Date filters
        if (dateFrom || dateTo) {
            const logDate = new Date(log.timestamp);
            
            if (dateFrom) {
                const fromDate = new Date(dateFrom);
                if (logDate < fromDate) return false;
            }
            
            if (dateTo) {
                const toDate = new Date(dateTo);
                toDate.setHours(23, 59, 59);
                if (logDate > toDate) return false;
            }
        }
        
        return true;
    });
    
    currentPage = 1;
    displayLogs();
    
    showNotification(`Found ${filteredLogs.length} matching logs`, 'success');
}

// ============= DISPLAY LOGS =============

function displayLogs() {
    const tbody = document.getElementById('audit-table-body');
    const noLogs = document.getElementById('no-logs');
    const pagination = document.getElementById('pagination');
    
    if (filteredLogs.length === 0) {
        tbody.innerHTML = '';
        noLogs.style.display = 'block';
        pagination.style.display = 'none';
        return;
    }
    
    noLogs.style.display = 'none';
    pagination.style.display = 'flex';
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * logsPerPage;
    const endIndex = Math.min(startIndex + logsPerPage, filteredLogs.length);
    const pageLogs = filteredLogs.slice(startIndex, endIndex);
    
    // Display logs
    let html = '';
    pageLogs.forEach(log => {
        const statusClass = log.response_status < 400 ? 'status-success' : 'status-error';
        const timestamp = formatDateTime(log.timestamp);
        
        html += `
            <tr onclick="showLogDetails(${JSON.stringify(log).replace(/"/g, '&quot;')})">
                <td>${timestamp}</td>
                <td>${log.user_id || 'N/A'}</td>
                <td>${log.user_role || 'N/A'}</td>
                <td>${formatActionType(log.action_type)}</td>
                <td><code style="font-size: 0.75rem;">${log.endpoint || 'N/A'}</code></td>
                <td>${log.method || 'N/A'}</td>
                <td><span class="status-badge ${statusClass}">${log.response_status || 'N/A'}</span></td>
                <td>${log.response_time_ms ? log.response_time_ms.toFixed(0) + 'ms' : 'N/A'}</td>
                <td><code style="font-size: 0.75rem;">${log.ip_address || 'N/A'}</code></td>
                <td><button class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">View</button></td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    
    // Update pagination
    updatePagination();
}

// ============= PAGINATION =============

function updatePagination() {
    const totalPages = Math.ceil(filteredLogs.length / logsPerPage);
    
    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage >= totalPages;
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        displayLogs();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredLogs.length / logsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        displayLogs();
    }
}

// ============= LOG DETAILS MODAL =============

function showLogDetails(log) {
    const modal = document.getElementById('log-details-modal');
    const content = document.getElementById('log-details-content');
    
    let html = `
        <div class="log-details-grid">
            <div class="log-detail-row">
                <span class="log-detail-label">Timestamp:</span>
                <span class="log-detail-value">${formatDateTime(log.timestamp)}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">User ID:</span>
                <span class="log-detail-value">${log.user_id || 'N/A'}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">User Role:</span>
                <span class="log-detail-value">${log.user_role || 'N/A'}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">Action:</span>
                <span class="log-detail-value">${formatActionType(log.action_type)}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">Endpoint:</span>
                <span class="log-detail-value"><code>${log.endpoint || 'N/A'}</code></span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">Method:</span>
                <span class="log-detail-value">${log.method || 'N/A'}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">Response Status:</span>
                <span class="log-detail-value">${log.response_status || 'N/A'}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">Response Time:</span>
                <span class="log-detail-value">${log.response_time_ms ? log.response_time_ms.toFixed(0) + 'ms' : 'N/A'}</span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">IP Address:</span>
                <span class="log-detail-value"><code>${log.ip_address || 'N/A'}</code></span>
            </div>
            <div class="log-detail-row">
                <span class="log-detail-label">User Agent:</span>
                <span class="log-detail-value">${log.user_agent || 'N/A'}</span>
            </div>
        </div>
    `;
    
    if (log.metadata) {
        html += `
            <div class="log-metadata">
                <h3>Metadata</h3>
                <pre>${JSON.stringify(log.metadata, null, 2)}</pre>
            </div>
        `;
    }
    
    content.innerHTML = html;
    modal.style.display = 'block';
}

function closeLogDetailsModal() {
    document.getElementById('log-details-modal').style.display = 'none';
}

// ============= EXPORT FUNCTIONS =============

function exportToJSON() {
    const dataStr = JSON.stringify(filteredLogs, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    showNotification('Logs exported as JSON', 'success');
}

function exportToCSV() {
    if (filteredLogs.length === 0) {
        showNotification('No logs to export', 'warning');
        return;
    }
    
    // CSV headers
    const headers = ['Timestamp', 'User ID', 'User Role', 'Action', 'Endpoint', 'Method', 'Status', 'Response Time (ms)', 'IP Address'];
    
    // CSV rows
    const rows = filteredLogs.map(log => [
        formatDateTime(log.timestamp),
        log.user_id || '',
        log.user_role || '',
        log.action_type || '',
        log.endpoint || '',
        log.method || '',
        log.response_status || '',
        log.response_time_ms ? log.response_time_ms.toFixed(0) : '',
        log.ip_address || ''
    ]);
    
    // Create CSV content
    let csvContent = headers.join(',') + '\n';
    rows.forEach(row => {
        csvContent += row.map(field => `"${field}"`).join(',') + '\n';
    });
    
    // Download
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    showNotification('Logs exported as CSV', 'success');
}

// ============= UTILITY FUNCTIONS =============

function formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatActionType(actionType) {
    if (!actionType) return 'N/A';
    return actionType.replace(/_/g, ' ').replace(/GET |POST |PUT |DELETE /g, '');
}