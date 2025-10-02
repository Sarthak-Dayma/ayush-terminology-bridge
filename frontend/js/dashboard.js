/**
 * Dashboard Logic for AYUSH Terminology Bridge
 * Handles: Analytics, Charts, Statistics Display
 */

// ============= INITIALIZATION =============

document.addEventListener('DOMContentLoaded', async () => {
    if (!requireAuth()) return;

    const userInfo = getUserInfo();
    if (!hasPermission('researcher')) {
        showNotification('You do not have permission to view this page', 'error');
        setTimeout(() => window.location.href = 'index.html', 2000);
        return;
    }

    if (hasPermission('auditor')) {
        const auditLink = document.getElementById('audit-link-dash');
        if (auditLink) auditLink.style.display = 'inline-block';
    }

    await loadDashboardData();
});

// ============= DATA LOADING & REFRESH =============

async function loadDashboardData() {
    showLoadingSpinner();
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/dashboard-stats`);
        const data = await response.json();

        if (response.ok) {
            populateDashboard(data);
        } else {
            showNotification('Failed to load dashboard data', 'error');
        }
    } catch (error) {
        console.error('Dashboard load error:', error);
        showNotification('Failed to load dashboard data', 'error');
    } finally {
        hideLoadingSpinner();
    }
}

async function refreshDashboard() {
    showNotification('Refreshing dashboard...', 'info');
    await loadDashboardData();
    showNotification('Dashboard refreshed!', 'success');
}

// ============= DOM POPULATION =============

function populateDashboard(data) {
    // Update main statistic cards
    document.getElementById('total-searches').textContent = formatNumber(data.total_searches || 0);
    document.getElementById('total-translations').textContent = formatNumber(data.total_translations || 0);
    document.getElementById('total-users').textContent = formatNumber(data.unique_users || 0);
    document.getElementById('avg-response-time').textContent = `${(data.avg_response_time_ms || 0).toFixed(0)}ms`;

    // Populate popular searches list
    populateList('popular-searches', data.top_searches, (item, index) => `
        <div class="list-item">
            <div><div class="list-item-title">${index + 1}. ${item.query}</div></div>
            <span class="list-item-count">${item.count}</span>
        </div>
    `, 'No search data available');

    // Populate most translated codes list
    populateList('popular-codes', data.top_translations, (item) => `
        <div class="list-item">
            <div><div class="list-item-title">${item.code}</div></div>
            <span class="list-item-count">${item.count}</span>
        </div>
    `, 'No translation data available');
}

function populateList(containerId, items, renderer, noDataMessage) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    if (items && items.length > 0) {
        container.innerHTML = items.map((item, index) => renderer(item, index)).join('');
    } else {
        container.innerHTML = `<div class="no-data"><p>${noDataMessage}</p></div>`;
    }
}

// ============= UTILITY FUNCTIONS =============

function formatNumber(num) {
    return num.toLocaleString();
}