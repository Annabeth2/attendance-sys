// Common functionality for all pages
const API_BASE_URL = 'http://localhost:8000';
const DEBUG = true; // Set to false in production

// Debug logging
function debugLog(message, data = null) {
    if (DEBUG) {
        console.log(`[DEBUG] ${message}`, data || '');
    }
}

// Authentication functions
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        debugLog('No authentication token found');
        window.location.href = 'login.html';
        return false;
    }
    debugLog('Authentication token found');
    return token;
}

function logout() {
    debugLog('Logging out user');
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}

// API request helper
async function apiRequest(endpoint, options = {}) {
    const token = checkAuth();
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };

    try {
        debugLog(`Making API request to ${endpoint}`, options);
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...defaultOptions,
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            debugLog('API request failed', error);
            throw new Error(error.detail || 'API request failed');
        }

        const data = await response.json();
        debugLog(`API request successful`, data);
        return data;
    } catch (error) {
        debugLog('API Error:', error);
        alert(error.message);
        throw error;
    }
}

// Bluetooth functions
let scanningInterval = null;
let discoveredBeacons = new Set();
let connectedDevice = null;
let lastError = null;

async function startBluetoothScan() {
    try {
        debugLog('Starting Bluetooth scan');
        
        if (!navigator.bluetooth) {
            throw new Error('Bluetooth is not supported in this browser');
        }

        const device = await navigator.bluetooth.requestDevice({
            acceptAllDevices: true,
            optionalServices: ['0000180f-0000-1000-8000-00805f9b34fb']
        });

        debugLog('Bluetooth device selected', device);
        connectedDevice = await device.gatt.connect();
        debugLog('Connected to device', connectedDevice);
        
        updateScanStatus('connected', device.name);
        scanningInterval = setInterval(scanForBeacons, 5000);

        device.addEventListener('gattserverdisconnected', () => {
            debugLog('Device disconnected');
            stopBluetoothScan();
            alert('Bluetooth device disconnected. Please reconnect.');
        });

    } catch (error) {
        lastError = error;
        debugLog('Error starting Bluetooth scan:', error);
        updateScanStatus('error', error.message);
        alert('Failed to start Bluetooth scanning: ' + error.message);
    }
}

function updateScanStatus(status, message) {
    const startBtn = document.getElementById('startScanBtn');
    const stopBtn = document.getElementById('stopScanBtn');
    const statusDiv = document.getElementById('scanStatus');
    
    if (status === 'connected') {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        statusDiv.innerHTML = `
            <div class="status-active">
                <p>Connected to device: ${message || 'Unknown Device'}</p>
                <p>Scanning for attendance beacons...</p>
            </div>
        `;
    } else if (status === 'error') {
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        statusDiv.innerHTML = `
            <div class="status-error">
                <p>Error: ${message}</p>
                <p>Please try again</p>
            </div>
        `;
    } else {
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        statusDiv.innerHTML = '';
    }
}

function stopBluetoothScan() {
    debugLog('Stopping Bluetooth scan');
    if (scanningInterval) {
        clearInterval(scanningInterval);
        scanningInterval = null;
    }
    
    if (connectedDevice) {
        connectedDevice.gatt.disconnect();
        connectedDevice = null;
    }
    
    updateScanStatus('stopped');
}

async function scanForBeacons() {
    try {
        if (!connectedDevice) {
            throw new Error('No device connected');
        }

        debugLog('Scanning for beacons');
        const service = await connectedDevice.gatt.getPrimaryService('0000180f-0000-1000-8000-00805f9b34fb');
        const characteristic = await service.getCharacteristic('00002a00-0000-1000-8000-00805f9b34fb');
        const value = await characteristic.readValue();
        const deviceName = new TextDecoder().decode(value);
        
        debugLog('Device name read', deviceName);
        
        if (deviceName.startsWith('LECTURER_')) {
            const beaconId = deviceName.split('_')[1];
            if (!discoveredBeacons.has(beaconId)) {
                debugLog('New beacon discovered', beaconId);
                discoveredBeacons.add(beaconId);
                await markAttendance(beaconId);
            } else {
                debugLog('Beacon already discovered', beaconId);
            }
        }
    } catch (error) {
        debugLog('Error scanning for beacons:', error);
        if (error.message.includes('disconnected')) {
            stopBluetoothScan();
            alert('Bluetooth device disconnected. Please reconnect.');
        }
    }
}

async function markAttendance(beaconId) {
    try {
        debugLog('Marking attendance for beacon', beaconId);
        await apiRequest('/bluetooth/mark-attendance', {
            method: 'POST',
            body: JSON.stringify({ beacon_id: beaconId })
        });
        debugLog('Attendance marked successfully');
        alert('Attendance marked successfully!');
    } catch (error) {
        debugLog('Error marking attendance:', error);
        alert('Failed to mark attendance: ' + error.message);
    }
}

// Form validation
function validateMacAddress(mac) {
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    const isValid = macRegex.test(mac);
    debugLog('MAC address validation', { mac, isValid });
    return isValid;
}

// Date formatting
function formatDate(date) {
    const formatted = new Date(date).toLocaleString();
    debugLog('Date formatting', { input: date, output: formatted });
    return formatted;
}

// Error handling
function handleError(error, elementId) {
    debugLog('Handling error', { error, elementId });
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = error.message;
    } else {
        console.error(error);
    }
}

// Add error boundary for unhandled errors
window.onerror = function(msg, url, lineNo, columnNo, error) {
    debugLog('Unhandled error', { msg, url, lineNo, columnNo, error });
    return false;
};

// Add promise rejection handler
window.onunhandledrejection = function(event) {
    debugLog('Unhandled promise rejection', event.reason);
    return false;
}; 