/**
 * Main Application Logic for AYUSH Terminology Bridge
 * Handles: Search, Translation, FHIR Generation
 */



// ============= SEARCH FUNCTIONALITY =============

function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        searchCodes();
    }
}

async function searchCodes() {
    const query = document.getElementById('search-input').value.trim();
    const useML = document.getElementById('use-ml-search').checked;
    const limit = document.getElementById('search-limit').value;
    const resultsDiv = document.getElementById('search-results');
    
    if (!query) {
        resultsDiv.innerHTML = '<div class="alert alert-warning">Please enter a search query</div>';
        return;
    }
    
    // Show loading
    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';
    showLoadingSpinner();
    
    try {
        const url = `${API_BASE_URL}/api/terminology/search?q=${encodeURIComponent(query)}&limit=${limit}&use_ml=${useML}`;
        const response = await authenticatedFetch(url);
        const data = await response.json();
        
        if (response.ok) {
            displaySearchResults(data);
        } else {
            resultsDiv.innerHTML = `<div class="alert alert-error">${data.error || 'Search failed'}</div>`;
        }
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    } finally {
        hideLoadingSpinner();
    }
}

function displaySearchResults(data) {
    const resultsDiv = document.getElementById('search-results');
    
    if (data.results.length === 0) {
        resultsDiv.innerHTML = `
            <div class="alert alert-info">
                <strong>No results found</strong>
                <p>Try different search terms or check spelling</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div style="margin-bottom: 1rem;">
            <strong>${data.count} results found</strong> in ${data.response_time_ms}ms
            ${data.ml_enabled ? '<span class="badge" style="background: var(--success-color); color: white; padding: 0.25rem 0.5rem; border-radius: 4px; margin-left: 0.5rem;">ML Enhanced</span>' : ''}
        </div>
    `;
    
    data.results.forEach(result => {
        const matchScore = result.combined_score || result.match_score || 0;
        const scorePercent = Math.round(matchScore * 100);
        
        html += `
            <div class="result-item">
                <div class="result-header">
                    <span class="result-code">${result.code}</span>
                    <span class="result-score">${scorePercent}% match</span>
                </div>
                <div class="result-display">${result.display}</div>
                <div class="result-meta">
                    <span><strong>System:</strong> ${result.system || 'NAMASTE'}</span>
                    ${result.semantic_score ? `<span><strong>Semantic Score:</strong> ${(result.semantic_score * 100).toFixed(1)}%</span>` : ''}
                </div>
                <div class="result-actions">
                    <button class="btn btn-primary" onclick="translateFromSearch('${result.code}')">
                        🔄 Translate to ICD-11
                    </button>
                    <button class="btn btn-secondary" onclick="viewCodeDetails('${result.code}')">
                        👁️ View Details
                    </button>
                </div>
            </div>
        `;
    });
    
    resultsDiv.innerHTML = html;
}

function translateFromSearch(code) {
    // Scroll to translation section
    document.getElementById('translate-input').value = code;
    document.getElementById('translation-section').scrollIntoView({ behavior: 'smooth' });
    
    // Trigger translation after scroll
    setTimeout(() => translateCode(), 500);
}

function viewCodeDetails(code) {
    // TODO: Implement code details modal
    alert(`Viewing details for ${code}\nThis feature will show full NAMASTE code information.`);
}

// ============= TRANSLATION FUNCTIONALITY =============

async function translateCode() {
    const namasteCode = document.getElementById('translate-input').value.trim();
    const useML = document.getElementById('use-ml-translate').checked;
    const resultsDiv = document.getElementById('translation-results');
    
    if (!namasteCode) {
        resultsDiv.innerHTML = '<div class="alert alert-warning">Please enter a NAMASTE code</div>';
        return;
    }
    
    // Show loading
    resultsDiv.innerHTML = '<div class="loading">Translating...</div>';
    showLoadingSpinner();
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/terminology/translate`, {
            method: 'POST',
            body: JSON.stringify({
                namaste_code: namasteCode,
                use_ml: useML
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayTranslationResults(data);
        } else {
            resultsDiv.innerHTML = `<div class="alert alert-error">${data.detail || 'Translation failed'}</div>`;
        }
    } catch (error) {
        console.error('Translation error:', error);
        resultsDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    } finally {
        hideLoadingSpinner();
    }
}

function displayTranslationResults(data) {
    const resultsDiv = document.getElementById('translation-results');
    
    const namaste = data.namaste;
    const tm2Matches = data.icd11_tm2_matches || [];
    const bioMatches = data.icd11_biomedicine_matches || [];
    
    let html = `
        <div class="translation-result">
            <div class="translation-header">
                <h3>Translation Results</h3>
                <span style="color: var(--text-secondary);">${data.response_time_ms}ms</span>
            </div>
            
            <div class="namaste-section">
                <h4>📚 NAMASTE Code</h4>
                <div style="margin-top: 0.75rem;">
                    <div style="font-size: 1.25rem; font-weight: 600; color: var(--primary-color); margin-bottom: 0.5rem;">
                        ${namaste.code}
                    </div>
                    <div style="font-size: 1rem; margin-bottom: 0.5rem;">
                        ${namaste.display}
                    </div>
                    ${namaste.definition ? `<div style="color: var(--text-secondary); font-size: 0.9rem;">${namaste.definition}</div>` : ''}
                </div>
            </div>
    `;
    
    // TM2 Matches
    if (tm2Matches.length > 0) {
        html += `
            <div class="icd-section">
                <h4>🌿 ICD-11 Traditional Medicine 2 (TM2)</h4>
        `;
        
        tm2Matches.slice(0, 5).forEach((match, index) => {
            const mlScore = match.ml_score ? `<span class="match-score">ML: ${(match.ml_score * 100).toFixed(0)}%</span>` : '';
            html += `
                <div class="icd-match">
                    <div class="icd-match-header">
                        <span class="icd-code">${match.code}</span>
                        ${mlScore}
                    </div>
                    <div style="font-weight: 500; margin-bottom: 0.25rem;">${match.title}</div>
                    ${match.definition ? `<div style="color: var(--text-secondary); font-size: 0.875rem;">${match.definition}</div>` : ''}
                    <button class="btn btn-secondary" style="margin-top: 0.5rem;" onclick="useFHIR('${namaste.code}', '${match.code}')">
                        Use in FHIR
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    // Biomedicine Matches
    if (bioMatches.length > 0) {
        html += `
            <div class="icd-section" style="border-left-color: var(--warning-color);">
                <h4 style="color: var(--warning-color);">🏥 ICD-11 Biomedicine (MMS)</h4>
        `;
        
        bioMatches.slice(0, 5).forEach((match, index) => {
            const mlScore = match.ml_score ? `<span class="match-score">ML: ${(match.ml_score * 100).toFixed(0)}%</span>` : '';
            html += `
                <div class="icd-match">
                    <div class="icd-match-header">
                        <span class="icd-code">${match.code}</span>
                        ${mlScore}
                    </div>
                    <div style="font-weight: 500; margin-bottom: 0.25rem;">${match.title}</div>
                    ${match.definition ? `<div style="color: var(--text-secondary); font-size: 0.875rem;">${match.definition}</div>` : ''}
                    <button class="btn btn-secondary" style="margin-top: 0.5rem;" onclick="useFHIR('${namaste.code}', '${match.code}')">
                        Use in FHIR
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    if (tm2Matches.length === 0 && bioMatches.length === 0) {
        html += '<div class="alert alert-warning">No ICD-11 matches found</div>';
    }
    
    html += '</div>';
    
    resultsDiv.innerHTML = html;
}

function useFHIR(namasteCode, icdCode) {
    // Scroll to FHIR section and populate fields
    document.getElementById('fhir-namaste-code').value = namasteCode;
    const currentIcdCodes = document.getElementById('fhir-icd-codes').value;
    if (currentIcdCodes) {
        document.getElementById('fhir-icd-codes').value = currentIcdCodes + ', ' + icdCode;
    } else {
        document.getElementById('fhir-icd-codes').value = icdCode;
    }
    
    document.getElementById('fhir-section').scrollIntoView({ behavior: 'smooth' });
}

// ============= FHIR GENERATION =============

async function generateFHIR() {
    const namasteCode = document.getElementById('fhir-namaste-code').value.trim();
    const icdCodesStr = document.getElementById('fhir-icd-codes').value.trim();
    const patientId = document.getElementById('fhir-patient-id').value.trim();
    const abhaId = document.getElementById('fhir-abha-id').value.trim();
    const resultsDiv = document.getElementById('fhir-results');
    
    if (!namasteCode || !icdCodesStr || !patientId) {
        resultsDiv.innerHTML = '<div class="alert alert-warning">Please fill in all required fields</div>';
        return;
    }
    
    // Parse ICD codes
    const icdCodes = icdCodesStr.split(',').map(code => code.trim()).filter(code => code);
    
    // Show loading
    resultsDiv.innerHTML = '<div class="loading">Generating FHIR resource...</div>';
    showLoadingSpinner();
    
    try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/fhir/Condition`, {
            method: 'POST',
            body: JSON.stringify({
                namaste_code: namasteCode,
                icd_codes: icdCodes,
                patient_id: patientId,
                abha_id: abhaId || null
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayFHIRResults(data);
        } else {
            resultsDiv.innerHTML = `<div class="alert alert-error">${data.detail || 'FHIR generation failed'}</div>`;
        }
    } catch (error) {
        console.error('FHIR generation error:', error);
        resultsDiv.innerHTML = '<div class="alert alert-error">Network error. Please try again.</div>';
    } finally {
        hideLoadingSpinner();
    }
}

function displayFHIRResults(data) {
    const resultsDiv = document.getElementById('fhir-results');
    
    const jsonStr = JSON.stringify(data, null, 2);
    
    let html = `
        <div class="alert alert-success">
            <strong>✅ FHIR Condition Resource Generated Successfully</strong>
            <p>Resource ID: <code>${data.id}</code></p>
        </div>
        
        <div style="margin-top: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3>FHIR R4 JSON</h3>
                <button class="btn btn-secondary" onclick="copyFHIRToClipboard()">
                    📋 Copy to Clipboard
                </button>
            </div>
            <pre id="fhir-json-output" style="background: var(--bg-color); padding: 1.5rem; border-radius: 8px; overflow-x: auto; border: 1px solid var(--border-color); font-size: 0.875rem;">${jsonStr}</pre>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function copyFHIRToClipboard() {
    const jsonOutput = document.getElementById('fhir-json-output');
    const text = jsonOutput.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        showNotification('FHIR JSON copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Copy failed:', err);
        showNotification('Copy failed', 'error');
    });
}

// ============= INITIALIZATION =============

document.addEventListener('DOMContentLoaded', () => {
    console.log('AYUSH Terminology Bridge App Initialized');
});