/**
 * Dashboard Logic for AYUSH Terminology Bridge
 * Handles: Analytics, Charts, Statistics Display
 */

const API_BASE_URL = 'http://localhost:8000';

let usageChart = null;
let successChart = null;

// ============= INITIALIZATION =============

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication and permissions
    if (!requireAuth()) {
        return;
    }
    
    const userInfo = getUserInfo();
    if (!hasPermission('researcher')) {
        showNotification('You do not have permission to view this page', 'error');
        setTimeout(() => window.location.href = 'index.html', 2000);
        return;
    }
    
    // Load all dashboard data
    await loadDashboardData();
});

// ============= LOAD DASHBOARD DATA =============

async function loadDashboardData() {
    showLoadingSpinner();
    
    try {
        await Promise.all([
            loadStatistics(),
            loadPopularSearches(),
            loadPopularCodes(),
            loadRecentActivity(),
            loadTranslationStats()
        ]);
        
        // Initialize charts after data loads
        initializeCharts();
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

// ============= LOAD STATISTICS =============

async function loadStatistics() {
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/dashboard-stats`);
        const data = await response.json();
        
        if (response.ok) {
            // Update stat cards
            document.getElementById('total-searches').textContent = formatNumber(data.total_searches || 0);
            document.getElementById('total-translations').textContent = formatNumber(data.total_translations || 0);
            document.getElementById('total-users').textContent = formatNumber(data.total_users || 0);
            
            // Calculate average response time
            const avgTime = data.translation_stats?.average_response_time || 0;
            document.getElementById('avg-response-time').textContent = `${avgTime.toFixed(0)}ms`;
        }
    } catch (error) {
        console.error('Stats load error:', error);
    }
}

// ============= LOAD POPULAR SEARCHES =============

async function loadPopularSearches() {
    const container = document.getElementById('popular-searches');
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/popular-searches?limit=10`);
        const data = await response.json();
        
        if (response.ok && data.popular_searches.length > 0) {
            let html = '';
            data.popular_searches.forEach((item, index) => {
                html += `
                    <div class="list-item">
                        <div>
                            <div class="list-item-title">${index + 1}. ${item.query}</div>
                            <div class="list-item-meta">Last searched: ${formatDate(item.last_searched)}</div>
                        </div>
                        <span class="list-item-count">${item.count}</span>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="no-data"><p>No search data available</p></div>';
        }
    } catch (error) {
        console.error('Popular searches load error:', error);
        container.innerHTML = '<div class="alert alert-error">Failed to load data</div>';
    }
}

// ============= LOAD POPULAR CODES =============

async function loadPopularCodes() {
    const container = document.getElementById('popular-codes');
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/dashboard-stats`);
        const data = await response.json();
        
        if (response.ok && data.popular_codes && data.popular_codes.length > 0) {
            let html = '';
            data.popular_codes.forEach((item, index) => {
                html += `
                    <div class="list-item">
                        <div>
                            <div class="list-item-title">${item.code}</div>
                            <div class="list-item-meta">${item.display || 'NAMASTE Code'}</div>
                        </div>
                        <span class="list-item-count">${item.count}</span>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="no-data"><p>No translation data available</p></div>';
        }
    } catch (error) {
        console.error('Popular codes load error:', error);
        container.innerHTML = '<div class="alert alert-error">Failed to load data</div>';
    }
}

// ============= LOAD RECENT ACTIVITY =============

async function loadRecentActivity() {
    const container = document.getElementById('recent-activity');
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/dashboard-stats`);
        const data = await response.json();
        
        if (response.ok && data.recent_activity && data.recent_activity.length > 0) {
            let html = '';
            data.recent_activity.forEach(activity => {
                const icon = getActivityIcon(activity.action_type);
                const iconClass = getActivityIconClass(activity.action_type);
                
                html += `
                    <div class="activity-item">
                        <div class="activity-icon ${iconClass}">${icon}</div>
                        <div class="activity-content">
                            <div class="activity-title">${formatActivityTitle(activity)}</div>
                            <div class="activity-meta">
                                ${activity.user_id || 'Unknown User'} • ${activity.endpoint || 'N/A'}
                            </div>
                        </div>
                        <div class="activity-time">${formatRelativeTime(activity.timestamp)}</div>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="no-data"><p>No recent activity</p></div>';
        }
    } catch (error) {
        console.error('Recent activity load error:', error);
        container.innerHTML = '<div class="alert alert-error">Failed to load data</div>';
    }
}

// ============= LOAD TRANSLATION STATS =============

async function loadTranslationStats() {
    const container = document.getElementById('translation-stats');
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/analytics/translation-stats`);
        const data = await response.json();
        
        if (response.ok) {
            let html = '';
            
            const stats = [
                { label: 'Total Translations', value: data.total_translations || 0 },
                { label: 'Successful', value: data.successful_translations || 0 },
                { label: 'Failed', value: data.failed_translations || 0 },
                { label: 'Avg Confidence', value: `${((data.average_confidence || 0) * 100).toFixed(1)}%` },
                { label: 'Avg Response Time', value: `${(data.average_response_time || 0).toFixed(0)}ms` },
                { label: 'Unique Codes Translated', value: data.unique_codes_translated || 0 }
            ];
            
            stats.forEach(stat => {
                html += `
                    <div class="stat-detail-item">
                        <div class="stat-detail-label">${stat.label}</div>
                        <div class="stat-detail-value">${stat.value}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Translation stats load error:', error);
        container.innerHTML = '<div class="alert alert-error">Failed to load data</div>';
    }
}

// ============= INITIALIZE CHARTS =============

function initializeCharts() {
    initializeUsageChart();
    initializeSuccessChart();
}

function initializeUsageChart() {
    const ctx = document.getElementById('usage-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (usageChart) {
        usageChart.destroy();
    }
    
    // Generate mock data for last 7 days
    const labels = getLast7Days();
    const searchData = generateMockData(7, 10, 50);
    const translationData = generateMockData(7, 5, 30);
    
    usageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Searches',
                    data: searchData,
                    borderColor: 'rgb(37, 99, 235)',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Translations',
                    data: translationData,
                    borderColor: 'rgb(22, 163, 74)',
                    backgroundColor: 'rgba(22, 163, 74, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function initializeSuccessChart() {
    const ctx = document.getElementById('success-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (successChart) {
        successChart.destroy();
    }
    
    successChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Successful', 'Failed', 'Partial'],
            datasets: [{
                data: [85, 10, 5],
                backgroundColor: [
                    'rgb(22, 163, 74)',
                    'rgb(220, 38, 38)',
                    'rgb(245, 158, 11)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ============= UTILITY FUNCTIONS =============

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatRelativeTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(timestamp);
}

function getActivityIcon(actionType) {
    if (actionType.includes('SEARCH')) return '🔍';
    if (actionType.includes('TRANSLATE')) return '🔄';
    if (actionType.includes('FHIR')) return '📋';
    if (actionType.includes('LOGIN')) return '🔐';
    if (actionType.includes('LOGOUT')) return '🚪';
    return '📊';
}

function getActivityIconClass(actionType) {
    if (actionType.includes('SEARCH')) return 'search';
    if (actionType.includes('TRANSLATE')) return 'translate';
    if (actionType.includes('FHIR')) return 'fhir';
    if (actionType.includes('LOGIN')) return 'login';
    return '';
}

function formatActivityTitle(activity) {
    const action = activity.action_type;
    if (action.includes('SEARCH')) return 'Search performed';
    if (action.includes('TRANSLATE')) return 'Code translated';
    if (action.includes('FHIR')) return 'FHIR resource created';
    if (action.includes('LOGIN')) return 'User logged in';
    if (action.includes('LOGOUT')) return 'User logged out';
    return action.replace(/_/g, ' ');
}

function getLast7Days() {
    const days = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));
    }
    return days;
}

function generateMockData(count, min, max) {
    const data = [];
    for (let i = 0; i < count; i++) {
        data.push(Math.floor(Math.random() * (max - min + 1)) + min);
    }
    return data;
}