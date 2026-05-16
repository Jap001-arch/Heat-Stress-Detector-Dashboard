/**
 * Heat Stress Detector Dashboard - Frontend JavaScript
 * Handles API interactions, real-time updates, and UI management
 */

// ==================== CONFIGURATION ====================

const API_BASE = '/api';
const POLL_INTERVAL = 3000; // Poll every 3 seconds
const NOTIFICATION_TIMEOUT = 4000; // Show notifications for 4 seconds

// ==================== STATE MANAGEMENT ====================

const appState = {
    equipment: [],
    pollIntervalId: null,
    currentEditingId: null,
};

// ==================== DOM ELEMENTS ====================

const DOM = {
    equipmentGrid: document.getElementById('equipment-grid'),
    statTotal: document.getElementById('stat-total'),
    statAlerts: document.getElementById('stat-alerts'),
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
    btnEditFromDetail: document.getElementById('btn-edit-from-detail'),
    btnDeleteFromDetail: document.getElementById('btn-delete-from-detail'),
    
    // Forms
    formAddEquipment: document.getElementById('form-add-equipment'),
    formEditEquipment: document.getElementById('form-edit-equipment'),
};

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Heat Stress Detector Dashboard initialized');
    
    // Setup event listeners
    setupEventListeners();
    
    // Load initial data
    loadEquipment();
    
    // Start polling for updates
    startPolling();
});

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
    // Control panel buttons
    DOM.btnAddEquipment.addEventListener('click', () => openAddEquipmentModal());
    DOM.btnCleanup.addEventListener('click', () => cleanupOldLogs());
    
    // Search
    DOM.searchInput.addEventListener('input', (e) => filterEquipment(e.target.value));
    
    // Forms
    DOM.formAddEquipment.addEventListener('submit', (e) => handleAddEquipment(e));
    DOM.formEditEquipment.addEventListener('submit', (e) => handleEditEquipment(e));
    
    // Modal buttons
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
        const equipmentId = document.getElementById('detail-eq-id').textContent;
        openEditEquipmentModal(parseInt(equipmentId));
        DOM.modalEquipmentDetails.classList.remove('active');
    });
    
    DOM.btnDeleteFromDetail.addEventListener('click', () => {
        const equipmentId = document.getElementById('detail-eq-id').textContent;
        if (confirm(`Are you sure you want to delete equipment ${equipmentId}? This action cannot be undone.`)) {
            deleteEquipment(parseInt(equipmentId));
            DOM.modalEquipmentDetails.classList.remove('active');
        }
    });
}

// ==================== API FUNCTIONS ====================

/**
 * Fetch all equipment with latest telemetry data
 */
async function loadEquipment() {
    try {
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
        showNotification('Error connecting to server', 'error');
    }
}

/**
 * Add new equipment
 */
async function createEquipment(name, maxTempThreshold) {
    try {
        const response = await fetch(`${API_BASE}/equipment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                max_temp_threshold: parseFloat(maxTempThreshold),
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
 * Update equipment details
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
 * Delete equipment
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
 * Fetch equipment details with history
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
 * Add temperature telemetry
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
        
        return true;
    } catch (error) {
        console.error('Error adding telemetry:', error);
        return false;
    }
}

/**
 * Cleanup old telemetry logs
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

// ==================== RENDERING FUNCTIONS ====================

/**
 * Render equipment cards
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
    
    // Add event listeners to cards
    document.querySelectorAll('.equipment-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't trigger if clicking buttons
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
 * Create HTML for equipment card
 */
function createEquipmentCard(equipment) {
    const status = getStatus(equipment);
    const currentTemp = equipment.Current_Temp ?? 'No data';
    const maxTemp = equipment.Max_Temp_Threshold;
    const tempDisplay = typeof currentTemp === 'number' ? `${currentTemp.toFixed(1)}` : currentTemp;
    
    return `
        <div class="equipment-card status-${status}" data-equipment-id="${equipment.Equipment_ID}">
            <div class="equipment-card-header">
                <div>
                    <div class="equipment-name">${escapeHtml(equipment.Name)}</div>
                    <div class="equipment-id">ID: ${equipment.Equipment_ID}</div>
                </div>
                <div class="status-badge ${status}">${status.toUpperCase()}</div>
            </div>
            
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
 * Show equipment details modal
 */
async function showEquipmentDetails(equipmentId) {
    try {
        const detail = await fetchEquipmentDetail(equipmentId);
        if (!detail) return;
        
        const eq = detail.equipment;
        const telemetry = detail.recent_telemetry || [];
        
        // Populate detail modal
        document.getElementById('detail-equipment-name').textContent = eq.Name;
        document.getElementById('detail-eq-id').textContent = eq.Equipment_ID;
        document.getElementById('detail-max-temp').textContent = `${eq.Max_Temp_Threshold.toFixed(1)}°C`;
        
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
        
        // Render recent readings (last 10)
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
        
        // Open modal
        DOM.modalEquipmentDetails.classList.add('active');
    } catch (error) {
        console.error('Error showing equipment details:', error);
        showNotification('Failed to load equipment details', 'error');
    }
}

/**
 * Filter equipment by search term
 */
function filterEquipment(searchTerm) {
    const filtered = appState.equipment.filter(eq => 
        eq.Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        eq.Equipment_ID.toString().includes(searchTerm)
    );
    
    // Temporarily replace equipment array and re-render
    const original = appState.equipment;
    appState.equipment = filtered;
    renderEquipment();
    appState.equipment = original;
}

/**
 * Update dashboard statistics
 */
function updateStats() {
    const total = appState.equipment.length;
    const alerts = appState.equipment.filter(eq => getStatus(eq) === 'alert').length;
    
    DOM.statTotal.textContent = total;
    DOM.statAlerts.textContent = alerts;
}

/**
 * Update current time display
 */
function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    DOM.statTime.textContent = `${hours}:${minutes}:${seconds}`;
}

// ==================== MODAL HANDLERS ====================

/**
 * Open add equipment modal
 */
function openAddEquipmentModal() {
    DOM.formAddEquipment.reset();
    DOM.modalAddEquipment.classList.add('active');
    document.getElementById('input-eq-name').focus();
}

/**
 * Open edit equipment modal
 */
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
    
    DOM.modalEditEquipment.classList.add('active');
    document.getElementById('edit-eq-name').focus();
}

/**
 * Handle add equipment form submission
 */
async function handleAddEquipment(e) {
    e.preventDefault();
    
    const name = document.getElementById('input-eq-name').value.trim();
    const maxTemp = document.getElementById('input-max-temp').value;
    
    if (!name || !maxTemp) {
        showNotification('Please fill in all required fields', 'warning');
        return;
    }
    
    const btn = DOM.formAddEquipment.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Creating...';
    
    try {
        const success = await createEquipment(name, maxTemp);
        if (success) {
            DOM.modalAddEquipment.classList.remove('active');
            DOM.formAddEquipment.reset();
        }
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Equipment';
    }
}

/**
 * Handle edit equipment form submission
 */
async function handleEditEquipment(e) {
    e.preventDefault();
    
    const equipmentId = parseInt(document.getElementById('edit-equipment-id').value);
    const name = document.getElementById('edit-eq-name').value.trim();
    const maxTemp = document.getElementById('edit-max-temp').value;
    
    const updates = {};
    if (name) updates.name = name;
    if (maxTemp) updates.max_temp_threshold = parseFloat(maxTemp);
    
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

/**
 * Start polling for equipment updates
 */
function startPolling() {
    if (appState.pollIntervalId) {
        clearInterval(appState.pollIntervalId);
    }
    
    appState.pollIntervalId = setInterval(() => {
        loadEquipment();
    }, POLL_INTERVAL);
}

/**
 * Stop polling
 */
function stopPolling() {
    if (appState.pollIntervalId) {
        clearInterval(appState.pollIntervalId);
        appState.pollIntervalId = null;
    }
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Determine equipment status based on temperature
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
 * Format timestamp for display
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
        
        // Fall back to date format
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return '--';
    }
}

/**
 * Escape HTML special characters
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
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    DOM.notificationContainer.appendChild(notification);
    
    // Auto-remove after timeout
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100px)';
        setTimeout(() => notification.remove(), 300);
    }, NOTIFICATION_TIMEOUT);
}

// ==================== CLEANUP ====================

/**
 * Stop polling when page unloads
 */
window.addEventListener('beforeunload', () => {
    stopPolling();
});

console.log('Heat Stress Detector Dashboard loaded successfully');
