// ==================== CONFIGURATION ====================

/**
 * CRITICAL NETWORK CONFIGURATION:
 * The API base URL is explicitly hardcoded to the Linux VM IP.
 * Do NOT use localhost, 127.0.0.1, or relative paths.
 */
const API_BASE = 'http://your_ip_address:5000/api';
const API_EXPORT = 'http://your_ip_address:5000/api/export';

const POLL_INTERVAL = 3000;               // Poll every 3 seconds
const NOTIFICATION_TIMEOUT = 4000;        // Show notifications for 4 seconds
const RAPID_HEAT_THRESHOLD = 10.0;        // 10°C increase triggers rapid heating alert

// ==================== STATE MANAGEMENT ====================

const appState = {
    equipment: [],
    pollIntervalId: null,
    currentEditingId: null,
    trendCharts: {},  // Feature 1: Store Chart.js instances
};

// ==================== DOM ELEMENTS ====================

const DOM = {
    equipmentGrid: document.getElementById('equipment-grid'),
    statTotal: document.getElementById('stat-total'),
    statAlerts: document.getElementById('stat-alerts'),
    statRapidHeat: document.getElementById('stat-rapid-heat'),
    statTime: document.getElementById('stat-time'),
    notificationContainer: document.getElementById('notification-container'),
    searchInput: document.getElementById('search-input'),
    
    // Modals
    modalAddEquipment: document.getElementById('modal-add-equipment'),
    modalEditEquipment: document.getElementById('modal-edit-equipment'),
    modalEquipmentDetails: document.getElementById('modal-equipment-details'),
    
    // Buttons
    btnAddEquipment: document.getElementById('btn-add-equipment'),
    btnCleanup: document.getElementById('btn-cleanup'),
    btnExportCSV: document.getElementById('btn-export-csv'),  // Feature 4: CSV Export
    btnEditFromDetail: document.getElementById('btn-edit-from-detail'),
    btnDeleteFromDetail: document.getElementById('btn-delete-from-detail'),
    
    // Forms
    formAddEquipment: document.getElementById('form-add-equipment'),
    formEditEquipment: document.getElementById('form-edit-equipment'),
};

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Heat Stress Detector v2.0 initialized');
    console.log(`API Base URL: ${API_BASE}`);
    
    setupEventListeners();
    loadEquipment();
    startPolling();
});

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
    // Control panel buttons
    DOM.btnAddEquipment.addEventListener('click', () => openAddEquipmentModal());
    DOM.btnCleanup.addEventListener('click', () => cleanupOldLogs());
    DOM.btnExportCSV.addEventListener('click', () => exportToCSV());  // Feature 4
    
    // Search
    DOM.searchInput.addEventListener('input', (e) => filterEquipment(e.target.value));
    
    // Forms
    DOM.formAddEquipment.addEventListener('submit', (e) => handleAddEquipment(e));
    DOM.formEditEquipment.addEventListener('submit', (e) => handleEditEquipment(e));
    
    // Modal controls
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.remove('active');
        });
    });
    
    document.querySelectorAll('.modal-cancel').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.remove('active');
        });
    });
    
    // Modal backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Detail modal buttons
    DOM.btnEditFromDetail.addEventListener('click', () => {
        const equipmentId = parseInt(document.getElementById('detail-eq-id').textContent);
        openEditEquipmentModal(equipmentId);
        DOM.modalEquipmentDetails.classList.remove('active');
    });
    
    DOM.btnDeleteFromDetail.addEventListener('click', () => {
        const equipmentId = parseInt(document.getElementById('detail-eq-id').textContent);
        if (confirm(`Are you sure you want to delete this equipment? This action cannot be undone.`)) {
            deleteEquipment(equipmentId);
            DOM.modalEquipmentDetails.classList.remove('active');
        }
    });
}

// ==================== API FUNCTIONS ====================

/**
 * Load all equipment from the server.
 * Includes health scores (Feature 6) and trend data (Feature 1).
 */
async function loadEquipment() {
    try {
        console.log(`Fetching equipment from: ${API_BASE}/equipment`);
        const response = await fetch(`${API_BASE}/equipment`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            appState.equipment = data.data || [];
            renderEquipment();
            updateStats();
            updateTime();
        } else {
            showNotification('Failed to load equipment data', 'error');
        }
    } catch (error) {
        console.error('Error loading equipment:', error);
        showNotification('Error connecting to server at 10.57.23.226:5000', 'error');
    }
}

/**
 * Create new equipment.
 * Feature 5: Now includes location parameter.
 */
async function createEquipment(name, maxTempThreshold, location) {
    try {
        const response = await fetch(`${API_BASE}/equipment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                max_temp_threshold: parseFloat(maxTempThreshold),
                location: location,  // Feature 5: Location support
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create equipment');
        }
        
        showNotification(`Equipment "${name}" created successfully`, 'success');
        loadEquipment();
        return true;
    } catch (error) {
        console.error('Error creating equipment:', error);
        showNotification(error.message, 'error');
        return false;
    }
}

/**
 * Update equipment.
 * Feature 5: Now includes location parameter.
 */
async function updateEquipment(equipmentId, updates) {
    try {
        const response = await fetch(`${API_BASE}/equipment/${equipmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update equipment');
        }
        
        showNotification('Equipment updated successfully', 'success');
        loadEquipment();
        return true;
    } catch (error) {
        console.error('Error updating equipment:', error);
        showNotification(error.message, 'error');
        return false;
    }
}

/**
 * Delete equipment.
 */
async function deleteEquipment(equipmentId) {
    try {
        const response = await fetch(`${API_BASE}/equipment/${equipmentId}`, {
            method: 'DELETE',
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete equipment');
        }
        
        showNotification('Equipment deleted successfully', 'success');
        loadEquipment();
        return true;
    } catch (error) {
        console.error('Error deleting equipment:', error);
        showNotification(error.message, 'error');
        return false;
    }
}

/**
 * Fetch equipment details including trend data (Feature 1).
 */
async function fetchEquipmentDetail(equipmentId) {
    try {
        const response = await fetch(`${API_BASE}/equipment/${equipmentId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            return data;
        } else {
            showNotification('Failed to load equipment details', 'error');
            return null;
        }
    } catch (error) {
        console.error('Error fetching equipment detail:', error);
        showNotification('Error connecting to server', 'error');
        return null;
    }
}

/**
 * Add telemetry reading.
 * Server will detect rapid heating and send alerts.
 */
async function addTelemetry(equipmentId, currentTemp) {
    try {
        const response = await fetch(`${API_BASE}/telemetry`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                equipment_id: equipmentId,
                current_temp: parseFloat(currentTemp),
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            console.warn('Failed to add telemetry:', data.error);
            return false;
        }
        
        // Feature 2: Show rapid heating alert if detected
        if (data.alerts && data.alerts.rapid_heating) {
            showNotification('⚡ RAPID HEATING DETECTED! Temperature rising quickly!', 'warning');
        }
        
        return true;
    } catch (error) {
        console.error('Error adding telemetry:', error);
        return false;
    }
}

/**
 * Clean up old telemetry logs.
 */
async function cleanupOldLogs() {
    try {
        DOM.btnCleanup.disabled = true;
        DOM.btnCleanup.textContent = '🗑️ Cleaning...';
        
        const response = await fetch(`${API_BASE}/telemetry/cleanup`, {
            method: 'DELETE',
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to cleanup logs');
        }
        
        showNotification(`Cleaned up ${data.deleted_count} old telemetry records`, 'success');
    } catch (error) {
        console.error('Error cleaning up logs:', error);
        showNotification(error.message, 'error');
    } finally {
        DOM.btnCleanup.disabled = false;
        DOM.btnCleanup.textContent = '🗑️ Cleanup Old Logs';
    }
}

/**
 * Feature 4: Export data to CSV.
 */
async function exportToCSV() {
    try {
        DOM.btnExportCSV.disabled = true;
        DOM.btnExportCSV.textContent = '📥 Exporting...';
        
        // Create a temporary anchor element to trigger download
        const link = document.createElement('a');
        link.href = API_EXPORT;
        link.download = 'heat_report.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('CSV exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting CSV:', error);
        showNotification('Failed to export CSV', 'error');
    } finally {
        DOM.btnExportCSV.disabled = false;
        DOM.btnExportCSV.textContent = '📥 Export to CSV';
    }
}

// ==================== RENDERING FUNCTIONS ====================

/**
 * Render all equipment cards.
 * Feature 1: Includes trend chart integration
 * Feature 5: Shows location badges
 * Feature 6: Displays health scores with color coding
 */
function renderEquipment() {
    if (appState.equipment.length === 0) {
        DOM.equipmentGrid.innerHTML = `
            <div class="no-data">
                <p>📭 No equipment registered yet. Click "Add Equipment" to get started.</p>
            </div>
        `;
        return;
    }
    
    DOM.equipmentGrid.innerHTML = appState.equipment
        .map(equipment => createEquipmentCard(equipment))
        .join('');
    
    // Add event listeners
    document.querySelectorAll('.equipment-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.btn')) {
                showEquipmentDetails(parseInt(card.dataset.equipmentId));
            }
        });
    });
    
    document.querySelectorAll('.btn-view-details').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const equipmentId = parseInt(btn.dataset.equipmentId);
            showEquipmentDetails(equipmentId);
        });
    });
    
    document.querySelectorAll('.btn-edit-equipment').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const equipmentId = parseInt(btn.dataset.equipmentId);
            openEditEquipmentModal(equipmentId);
        });
    });
}

/**
 * Create HTML for equipment card.
 * Features 1, 5, 6 integrated.
 */
function createEquipmentCard(equipment) {
    const status = getStatus(equipment);
    const currentTemp = equipment.Current_Temp ?? 'No data';
    const maxTemp = equipment.Max_Temp_Threshold;
    const tempDisplay = typeof currentTemp === 'number' ? `${currentTemp.toFixed(1)}` : currentTemp;
    
    // Feature 5: Location badge
    const locationBadge = equipment.Location ? 
        `<span class="location-badge">📍 ${escapeHtml(equipment.Location)}</span>` : 
        '';
    
    // Feature 6: Health score with color coding
    const healthScore = equipment.Health_Score || 0;
    const healthStatus = equipment.Health_Status || 'Critical';
    const healthColor = getHealthColor(healthStatus);
    const healthEmoji = getHealthEmoji(healthStatus);
    
    return `
        <div class="equipment-card status-${status}" data-equipment-id="${equipment.Equipment_ID}">
            <div class="equipment-card-header">
                <div>
                    <div class="equipment-name">${escapeHtml(equipment.Name)}</div>
                    <div class="equipment-id">ID: ${equipment.Equipment_ID}</div>
                </div>
                <div style="display: flex; gap: 10px; align-items: flex-start;">
                    <div class="status-badge ${status}">${status.toUpperCase()}</div>
                    <!-- Feature 6: Health Score Badge -->
                    <div class="health-badge" style="border-color: ${healthColor};">
                        <div style="font-size: 12px; color: ${healthColor};">HEALTH</div>
                        <div style="font-size: 18px; font-weight: 700; color: ${healthColor};">${healthScore}%</div>
                        <div style="font-size: 10px; color: ${healthColor};">${healthEmoji}</div>
                    </div>
                </div>
            </div>
            
            <!-- Feature 5: Location badge -->
            ${locationBadge}
            
            <div class="equipment-body">
                <div class="temperature-display">
                    <span class="temp-label">Current Temperature</span>
                    <div>
                        <span class="temp-current">${tempDisplay}</span>
                        ${typeof currentTemp === 'number' ? '<span class="temp-unit">°C</span>' : ''}
                    </div>
                    <div class="temp-info">
                        <div class="temp-info-item">
                            <span class="temp-info-label">Max Threshold</span>
                            <span class="temp-info-value">${maxTemp.toFixed(1)}°C</span>
                        </div>
                        <div class="temp-info-item">
                            <span class="temp-info-label">Margin</span>
                            <span class="temp-info-value">
                                ${typeof currentTemp === 'number' ? (maxTemp - currentTemp).toFixed(1) : '--'}°C
                            </span>
                        </div>
                    </div>
                </div>
                
                ${equipment.Timestamp ? `
                    <div class="timestamp">
                        Last Updated: ${formatTime(equipment.Timestamp)}
                    </div>
                ` : `
                    <div class="timestamp" style="color: var(--text-muted);">
                        No readings yet
                    </div>
                `}
            </div>
            
            <div class="equipment-footer">
                <button class="btn btn-secondary btn-view-details" data-equipment-id="${equipment.Equipment_ID}">
                    📊 Details
                </button>
                <button class="btn btn-secondary btn-edit-equipment" data-equipment-id="${equipment.Equipment_ID}">
                    ⚙️ Edit
                </button>
            </div>
        </div>
    `;
}

/**
 * Show equipment details modal with trend chart (Feature 1).
 */
async function showEquipmentDetails(equipmentId) {
    try {
        const detail = await fetchEquipmentDetail(equipmentId);
        if (!detail) return;
        
        const eq = detail.equipment;
        const telemetry = detail.recent_telemetry || [];
        const trendData = detail.trend_data || { temps: [], timestamps: [] };
        
        // Populate modal
        document.getElementById('detail-equipment-name').textContent = eq.Name;
        document.getElementById('detail-eq-id').textContent = eq.Equipment_ID;
        document.getElementById('detail-location').textContent = eq.Location || 'Not specified';  // Feature 5
        document.getElementById('detail-max-temp').textContent = `${eq.Max_Temp_Threshold.toFixed(1)}°C`;
        document.getElementById('detail-overheat-count').textContent = eq.Overheat_Count || 0;
        
        // Feature 6: Display health score
        const healthScore = eq.Health_Score || 0;
        const healthStatus = eq.Health_Status || 'Critical';
        const healthColor = getHealthColor(healthStatus);
        document.getElementById('detail-health-score').innerHTML = 
            `<span style="color: ${healthColor}; font-weight: 700;">${healthScore}% (${healthStatus})</span>`;
        
        const currentTelemetry = telemetry[0];
        if (currentTelemetry) {
            document.getElementById('detail-current-temp').textContent = 
                `${currentTelemetry.Current_Temp.toFixed(1)}°C`;
            document.getElementById('detail-timestamp').textContent = 
                formatTime(currentTelemetry.Timestamp);
        } else {
            document.getElementById('detail-current-temp').textContent = 'No data';
            document.getElementById('detail-timestamp').textContent = '--';
        }
        
        // Render recent readings
        const readingsList = document.getElementById('detail-readings-list');
        if (telemetry.length > 0) {
            readingsList.innerHTML = telemetry.slice(0, 10).map(t => `
                <div class="reading-item">
                    <span class="reading-temp">${t.Current_Temp.toFixed(1)}°C</span>
                    <span class="reading-time">${formatTime(t.Timestamp)}</span>
                </div>
            `).join('');
        } else {
            readingsList.innerHTML = '<p class="no-data">No readings recorded yet</p>';
        }
        
        // Feature 1: Create trend chart using Chart.js
        createTrendChart(equipmentId, eq.Name, trendData, eq.Max_Temp_Threshold);
        
        DOM.modalEquipmentDetails.classList.add('active');
    } catch (error) {
        console.error('Error showing equipment details:', error);
        showNotification('Failed to load equipment details', 'error');
    }
}

/**
 * Feature 1: Create Chart.js trend graph.
 */
function createTrendChart(equipmentId, equipmentName, trendData, maxThreshold) {
    // Destroy existing chart if it exists
    if (appState.trendCharts[equipmentId]) {
        appState.trendCharts[equipmentId].destroy();
    }
    
    const ctx = document.getElementById('trend-chart');
    if (!ctx) return;
    
    appState.trendCharts[equipmentId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.timestamps.map(ts => formatChartTime(ts)),
            datasets: [
                {
                    label: `Temperature`,
                    data: trendData.temps,
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.05)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointBackgroundColor: '#00d4ff',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1,
                },
                {
                    label: 'Max Threshold',
                    data: Array(trendData.temps.length).fill(maxThreshold),
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#cbd5e1',
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(100, 116, 139, 0.1)',
                    },
                    ticks: {
                        color: '#cbd5e1',
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(100, 116, 139, 0.1)',
                    },
                    ticks: {
                        color: '#cbd5e1',
                    }
                }
            }
        }
    });
}

/**
 * Filter equipment by search term.
 */
function filterEquipment(searchTerm) {
    const filtered = appState.equipment.filter(eq => 
        eq.Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        eq.Equipment_ID.toString().includes(searchTerm) ||
        (eq.Location && eq.Location.toLowerCase().includes(searchTerm.toLowerCase()))  // Feature 5
    );
    
    const original = appState.equipment;
    appState.equipment = filtered;
    renderEquipment();
    appState.equipment = original;
}

/**
 * Update dashboard statistics.
 * Feature 2: Include rapid heating count
 * Feature 6: Include health score stats
 */
function updateStats() {
    const total = appState.equipment.length;
    const alerts = appState.equipment.filter(eq => getStatus(eq) === 'alert').length;
    
    // Feature 2: Count rapid heating events (would need additional tracking)
    const rapidHeatingDetected = appState.equipment.filter(eq => {
        // This would be tracked via the alerts in telemetry responses
        return false;  // Placeholder
    }).length;
    
    DOM.statTotal.textContent = total;
    DOM.statAlerts.textContent = alerts;
    DOM.statRapidHeat.textContent = '0';  // Would be updated from telemetry responses
}

/**
 * Update current time display.
 */
function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    DOM.statTime.textContent = `${hours}:${minutes}:${seconds}`;
}

// ==================== MODAL HANDLERS ====================

function openAddEquipmentModal() {
    DOM.formAddEquipment.reset();
    DOM.modalAddEquipment.classList.add('active');
    document.getElementById('input-eq-name').focus();
}

function openEditEquipmentModal(equipmentId) {
    const equipment = appState.equipment.find(eq => eq.Equipment_ID === equipmentId);
    if (!equipment) {
        showNotification('Equipment not found', 'error');
        return;
    }
    
    appState.currentEditingId = equipmentId;
    document.getElementById('edit-equipment-id').value = equipmentId;
    document.getElementById('edit-eq-name').value = equipment.Name;
    document.getElementById('edit-max-temp').value = equipment.Max_Temp_Threshold;
    document.getElementById('edit-location').value = equipment.Location || '';  // Feature 5
    
    DOM.modalEditEquipment.classList.add('active');
    document.getElementById('edit-eq-name').focus();
}

async function handleAddEquipment(e) {
    e.preventDefault();
    
    const name = document.getElementById('input-eq-name').value.trim();
    const maxTemp = document.getElementById('input-max-temp').value;
    const location = document.getElementById('input-location').value.trim();  // Feature 5
    
    if (!name || !maxTemp || !location) {
        showNotification('Please fill in all required fields', 'warning');
        return;
    }
    
    const btn = DOM.formAddEquipment.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Creating...';
    
    try {
        const success = await createEquipment(name, maxTemp, location);  // Feature 5
        if (success) {
            DOM.modalAddEquipment.classList.remove('active');
            DOM.formAddEquipment.reset();
        }
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Equipment';
    }
}

async function handleEditEquipment(e) {
    e.preventDefault();
    
    const equipmentId = parseInt(document.getElementById('edit-equipment-id').value);
    const name = document.getElementById('edit-eq-name').value.trim();
    const maxTemp = document.getElementById('edit-max-temp').value;
    const location = document.getElementById('edit-location').value.trim();  // Feature 5
    
    const updates = {};
    if (name) updates.name = name;
    if (maxTemp) updates.max_temp_threshold = parseFloat(maxTemp);
    if (location) updates.location = location;  // Feature 5
    
    if (Object.keys(updates).length === 0) {
        showNotification('Please fill in at least one field', 'warning');
        return;
    }
    
    const btn = DOM.formEditEquipment.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    try {
        const success = await updateEquipment(equipmentId, updates);
        if (success) {
            DOM.modalEditEquipment.classList.remove('active');
            DOM.formEditEquipment.reset();
            appState.currentEditingId = null;
        }
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Changes';
    }
}

// ==================== POLLING & UPDATES ====================

function startPolling() {
    if (appState.pollIntervalId) {
        clearInterval(appState.pollIntervalId);
    }
    
    appState.pollIntervalId = setInterval(() => {
        loadEquipment();
    }, POLL_INTERVAL);
}

function stopPolling() {
    if (appState.pollIntervalId) {
        clearInterval(appState.pollIntervalId);
        appState.pollIntervalId = null;
    }
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Determine equipment status.
 */
function getStatus(equipment) {
    if (equipment.Current_Temp === null) {
        return 'normal';
    }
    
    if (equipment.Current_Temp > equipment.Max_Temp_Threshold) {
        return 'alert';
    } else if (equipment.Current_Temp > (equipment.Max_Temp_Threshold * 0.9)) {
        return 'warning';
    }
    
    return 'normal';
}

/**
 * Feature 6: Get health score color.
 */
function getHealthColor(status) {
    switch(status) {
        case 'Healthy':
            return '#10b981';  // Green
        case 'Warning':
            return '#f59e0b';  // Orange
        case 'Critical':
            return '#ef4444';  // Red
        default:
            return '#cbd5e1';  // Gray
    }
}

/**
 * Feature 6: Get health score emoji.
 */
function getHealthEmoji(status) {
    switch(status) {
        case 'Healthy':
            return '🟢';
        case 'Warning':
            return '🟡';
        case 'Critical':
            return '🔴';
        default:
            return '⚪';
    }
}

/**
 * Format timestamp for display.
 */
function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return '--';
    }
}

/**
 * Format timestamp for Chart.js labels.
 */
function formatChartTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
        return '--';
    }
}

/**
 * Escape HTML special characters.
 */
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Show notification.
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    DOM.notificationContainer.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100px)';
        setTimeout(() => notification.remove(), 300);
    }, NOTIFICATION_TIMEOUT);
}

// ==================== CLEANUP ====================

window.addEventListener('beforeunload', () => {
    stopPolling();
});

console.log('Heat Stress Detector v2.0 loaded successfully with hardcoded IP: 10.57.23.226:5000');
