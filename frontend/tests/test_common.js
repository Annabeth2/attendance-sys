// Mock localStorage
const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock fetch
global.fetch = jest.fn();

// Mock navigator.bluetooth
const bluetoothMock = {
    requestDevice: jest.fn(),
    getAvailability: jest.fn()
};
global.navigator.bluetooth = bluetoothMock;

// Import the common.js functions
const {
    checkAuth,
    logout,
    apiRequest,
    startBluetoothScan,
    stopBluetoothScan,
    scanForBeacons,
    markAttendance,
    validateMacAddress,
    formatDate,
    handleError
} = require('../static/js/common.js');

describe('Authentication Functions', () => {
    beforeEach(() => {
        localStorageMock.getItem.mockClear();
        localStorageMock.removeItem.mockClear();
    });

    test('checkAuth should redirect to login when no token exists', () => {
        localStorageMock.getItem.mockReturnValue(null);
        const result = checkAuth();
        expect(result).toBe(false);
        expect(window.location.href).toBe('login.html');
    });

    test('checkAuth should return token when it exists', () => {
        const mockToken = 'test-token';
        localStorageMock.getItem.mockReturnValue(mockToken);
        const result = checkAuth();
        expect(result).toBe(mockToken);
    });

    test('logout should remove token and redirect to login', () => {
        logout();
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('token');
        expect(window.location.href).toBe('login.html');
    });
});

describe('API Request Function', () => {
    beforeEach(() => {
        fetch.mockClear();
        localStorageMock.getItem.mockReturnValue('test-token');
    });

    test('apiRequest should make successful request', async () => {
        const mockResponse = { ok: true, json: () => Promise.resolve({ data: 'test' }) };
        fetch.mockResolvedValue(mockResponse);

        const result = await apiRequest('/test');
        expect(fetch).toHaveBeenCalledWith(
            'http://localhost:8000/test',
            expect.objectContaining({
                headers: expect.objectContaining({
                    'Authorization': 'Bearer test-token'
                })
            })
        );
        expect(result).toEqual({ data: 'test' });
    });

    test('apiRequest should handle error response', async () => {
        const mockResponse = { ok: false, json: () => Promise.resolve({ detail: 'error' }) };
        fetch.mockResolvedValue(mockResponse);

        await expect(apiRequest('/test')).rejects.toThrow('error');
    });
});

describe('Bluetooth Functions', () => {
    beforeEach(() => {
        bluetoothMock.requestDevice.mockClear();
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('startBluetoothScan should handle successful device connection', async () => {
        const mockDevice = {
            name: 'Test Device',
            gatt: {
                connect: jest.fn().mockResolvedValue({
                    getPrimaryService: jest.fn().mockResolvedValue({
                        getCharacteristic: jest.fn().mockResolvedValue({
                            readValue: jest.fn().mockResolvedValue(new Uint8Array())
                        })
                    })
                })
            }
        };
        bluetoothMock.requestDevice.mockResolvedValue(mockDevice);

        await startBluetoothScan();
        expect(bluetoothMock.requestDevice).toHaveBeenCalled();
        expect(mockDevice.gatt.connect).toHaveBeenCalled();
    });

    test('startBluetoothScan should handle unsupported Bluetooth', async () => {
        global.navigator.bluetooth = null;
        await expect(startBluetoothScan()).rejects.toThrow('Bluetooth is not supported');
    });

    test('stopBluetoothScan should clear interval and disconnect device', () => {
        const mockDevice = { gatt: { disconnect: jest.fn() } };
        global.connectedDevice = mockDevice;
        global.scanningInterval = setInterval(() => {}, 1000);

        stopBluetoothScan();
        expect(clearInterval).toHaveBeenCalled();
        expect(mockDevice.gatt.disconnect).toHaveBeenCalled();
    });
});

describe('Utility Functions', () => {
    test('validateMacAddress should validate correct MAC address', () => {
        expect(validateMacAddress('00:11:22:33:44:55')).toBe(true);
        expect(validateMacAddress('00-11-22-33-44-55')).toBe(true);
    });

    test('validateMacAddress should reject invalid MAC address', () => {
        expect(validateMacAddress('invalid')).toBe(false);
        expect(validateMacAddress('00:11:22:33:44')).toBe(false);
    });

    test('formatDate should format date correctly', () => {
        const date = new Date('2024-03-20T10:00:00');
        expect(formatDate(date)).toBe(date.toLocaleString());
    });

    test('handleError should update error element', () => {
        document.body.innerHTML = '<div id="error"></div>';
        const error = new Error('Test error');
        handleError(error, 'error');
        expect(document.getElementById('error').textContent).toBe('Test error');
    });
}); 