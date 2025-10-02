/**
 * Authentication Module for AYUSH Terminology Bridge
 * Handles: Login, Logout, Token Management, Session Storage
 */

const API_BASE_URL = 'http://localhost:8000';

// ============= TOKEN MANAGEMENT =============

function getAuthToken() {
    return localStorage.getItem('auth_token');
}

function setAuthToken(token) {
    localStorage.setItem('auth_token', token);
}

function removeAuthToken() {
    localStorage.removeItem('auth_token');
}

function getUserInfo() {
    const userStr = localStorage.getItem('user_info');
    return userStr ? JSON.parse(userStr) : null;
}

function setUserInfo(userInfo) {
    localStorage.setItem('user_info', JSON.stringify(userInfo));
}

function removeUserInfo() {
    localStorage.removeItem('user_info');
}

// ============= AUTH HEADERS =============

function getAuthHeaders() {
    const token = getAuthToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

// ============= LOGIN MODAL =============

function showLoginModal() {
    document.getElementById('login-modal').style.display = 'block';
}

function closeLoginModal() {
    document.getElementById('login-modal').style.display = 'none';
    document.getElementById('login-error').style.display = 'none';
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('login-modal');
    if (event.target === modal) {
        closeLoginModal();
    }
}

// ============= LOGIN HANDLER =============

async function handleLogin(event) {
    event.preventDefault();
    
    const userId = document.getElementById('login-user-id').value;
    const password = document.getElementById('login-password').value;
    const errorDiv = document.getElementById('login-error');
    
    // Hide previous errors
    errorDiv.style.display = 'none';
    
    // Show loading
    showLoadingSpinner();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Store token and user info
            setAuthToken(data.access_token);
            setUserInfo({
                user_id: data.user_info.user_id,
                name: data.user_info.name,
                role: data.user_info.role,
                abha_id: data.user_info.abha_id
            });
            
            // Close modal and update UI
            closeLoginModal();
            updateUIForLoggedInUser();
            
            // Show success message
            showNotification('Login successful!', 'success');
            
            // Reset form
            document.getElementById('login-form').reset();
        } else {
            // Show error
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    } finally {
        hideLoadingSpinner();
    }
}

// ============= LOGOUT HANDLER =============

async function logout() {
    showLoadingSpinner();
    
    try {
        // Call logout endpoint
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear local storage
        removeAuthToken();
        removeUserInfo();
        
        // Update UI
        updateUIForLoggedOutUser();
        
        hideLoadingSpinner();
        
        // Redirect to home if on protected page
        const currentPage = window.location.pathname;
        if (currentPage.includes('dashboard') || currentPage.includes('audit')) {
            window.location.href = 'index.html';
        }
        
        showNotification('Logged out successfully', 'info');
    }
}

// ============= UI UPDATES =============

function updateUIForLoggedInUser() {
    const userInfo = getUserInfo();
    
    if (!userInfo) return;
    
    // Update user name displays
    const userNameElements = document.querySelectorAll('#user-name');
    userNameElements.forEach(el => {
        el.textContent = userInfo.name;
    });
    
    // Show/hide sections
    document.getElementById('login-section')?.setAttribute('style', 'display: none;');
    document.getElementById('user-info')?.setAttribute('style', 'display: flex;');
    
    // Hide auth warning
    document.getElementById('auth-warning')?.setAttribute('style', 'display: none;');
    
    // Show main sections
    document.getElementById('search-section')?.setAttribute('style', 'display: block;');
    document.getElementById('translation-section')?.setAttribute('style', 'display: block;');
    document.getElementById('fhir-section')?.setAttribute('style', 'display: block;');
    
    // Show/hide navigation based on role
    if (userInfo.role === 'admin' || userInfo.role === 'researcher') {
        const dashboardLinks = document.querySelectorAll('#dashboard-link, #dashboard-link-dash');
        dashboardLinks.forEach(link => link.style.display = 'inline-block');
    }
    
    if (userInfo.role === 'admin' || userInfo.role === 'auditor') {
        const auditLinks = document.querySelectorAll('#audit-link, #audit-link-dash');
        auditLinks.forEach(link => link.style.display = 'inline-block');
    }
}

function updateUIForLoggedOutUser() {
    // Show/hide sections
    document.getElementById('login-section')?.setAttribute('style', 'display: block;');
    document.getElementById('user-info')?.setAttribute('style', 'display: none;');
    
    // Show auth warning
    document.getElementById('auth-warning')?.setAttribute('style', 'display: block;');
    
    // Hide main sections
    document.getElementById('search-section')?.setAttribute('style', 'display: none;');
    document.getElementById('translation-section')?.setAttribute('style', 'display: none;');
    document.getElementById('fhir-section')?.setAttribute('style', 'display: none;');
    
    // Hide navigation links
    const dashboardLinks = document.querySelectorAll('#dashboard-link, #dashboard-link-dash');
    dashboardLinks.forEach(link => link.style.display = 'none');
    
    const auditLinks = document.querySelectorAll('#audit-link, #audit-link-dash');
    auditLinks.forEach(link => link.style.display = 'none');
}

// ============= CHECK AUTH STATUS =============

function checkAuthStatus() {
    const token = getAuthToken();
    const userInfo = getUserInfo();
    
    if (token && userInfo) {
        updateUIForLoggedInUser();
        return true;
    } else {
        updateUIForLoggedOutUser();
        return false;
    }
}

// ============= PROTECTED PAGE CHECK =============

function requireAuth() {
    const isAuthenticated = checkAuthStatus();
    
    // Check if on protected page
    const currentPage = window.location.pathname;
    if ((currentPage.includes('dashboard') || currentPage.includes('audit')) && !isAuthenticated) {
        window.location.href = 'index.html';
        return false;
    }
    
    return isAuthenticated;
}

// ============= ROLE-BASED ACCESS =============

function hasPermission(requiredRole) {
    const userInfo = getUserInfo();
    if (!userInfo) return false;
    
    const roleHierarchy = {
        'admin': 4,
        'auditor': 3,
        'researcher': 2,
        'practitioner': 1
    };
    
    const userLevel = roleHierarchy[userInfo.role] || 0;
    const requiredLevel = roleHierarchy[requiredRole] || 0;
    
    return userLevel >= requiredLevel;
}

// ============= API CALL WRAPPER =============

async function authenticatedFetch(url, options = {}) {
    const headers = getAuthHeaders();
    
    const response = await fetch(url, {
        ...options,
        headers: {
            ...headers,
            ...options.headers
        }
    });
    
    // Handle 401 - token expired
    if (response.status === 401) {
        removeAuthToken();
        removeUserInfo();
        showNotification('Session expired. Please login again.', 'warning');
        window.location.href = 'index.html';
        throw new Error('Authentication required');
    }
    
    return response;
}

// ============= UTILITY FUNCTIONS =============

function showLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.style.display = 'flex';
}

function hideLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.style.display = 'none';
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        animation: slideIn 0.3s;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============= INITIALIZATION =============

// Check auth status on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
});

// Auto-refresh token every 50 minutes
setInterval(async () => {
    const token = getAuthToken();
    if (token) {
        try {
            const response = await authenticatedFetch(`${API_BASE_URL}/api/auth/refresh`, {
                method: 'POST'
            });
            if (response.ok) {
                const data = await response.json();
                setAuthToken(data.access_token);
                console.log('Token refreshed');
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
    }
}, 50 * 60 * 1000); // 50 minutes

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});