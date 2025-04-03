# PowerShell startup script for Attendance System

# Function to check if a port is in use
function Test-PortInUse {
    param($port)
    $connection = New-Object System.Net.Sockets.TcpClient
    try {
        $connection.Connect("127.0.0.1", $port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to kill process using a port
function Stop-ProcessOnPort {
    param($port)
    $processId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    if ($processId) {
        Stop-Process -Id $processId -Force
        Write-Host "Killed process using port $port"
    }
}

# Function to check if a command exists
function Test-Command {
    param($command)
    try {
        Get-Command $command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Get the script's directory and ensure we're using absolute paths
$scriptPath = (Get-Item $PSScriptRoot).FullName
Write-Host "Script directory: $scriptPath"

# Create virtual environment in AppData
$venvPath = Join-Path $env:APPDATA "attendance_system_venv"
Write-Host "Virtual environment path: $venvPath"

# Check if Python is installed
if (-not (Test-Command "python")) {
    Write-Host "Error: Python is not installed or not in PATH"
    Write-Host "Please install Python 3.8 or later and add it to your PATH"
    exit 1
}

# Get Python executable path
$pythonPath = (Get-Command python).Path
Write-Host "Using Python at: $pythonPath"

# Check Python version
$pythonVersion = & $pythonPath --version
Write-Host "Python version: $pythonVersion"

# Remove existing venv if it exists and has incorrect paths
if (Test-Path $venvPath) {
    $venvPythonPath = Join-Path $venvPath "Scripts\python.exe"
    if (Test-Path $venvPythonPath) {
        $venvPythonContent = Get-Content $venvPythonPath -Raw
        if ($venvPythonContent -match "C:\\Users\\admin\\proj\\. X") {
            Write-Host "Removing existing virtual environment with incorrect paths..."
            Remove-Item -Path $venvPath -Recurse -Force
        }
    }
}

# Create new virtual environment if needed
if (-not (Test-Path "$venvPath\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    try {
        & $pythonPath -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error creating virtual environment"
            exit 1
        }
        Write-Host "Virtual environment created successfully"
    }
    catch {
        Write-Host "Error creating virtual environment: $_"
        exit 1
    }
}

# Check if backend directory exists
$backendPath = Join-Path $scriptPath "backend"
if (-not (Test-Path $backendPath)) {
    Write-Host "Error: Backend directory not found at: $backendPath"
    exit 1
}

# Check if frontend directory exists
$frontendPath = Join-Path $scriptPath "frontend"
if (-not (Test-Path $frontendPath)) {
    Write-Host "Error: Frontend directory not found at: $frontendPath"
    exit 1
}

# Kill any existing processes on ports 8000 and 3000
Write-Host "Checking for existing processes..."
Stop-ProcessOnPort 8000
Stop-ProcessOnPort 3000

# Activate virtual environment
Write-Host "Activating virtual environment..."
try {
    & "$venvPath\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated successfully"
}
catch {
    Write-Host "Error activating virtual environment: $_"
    exit 1
}

# Install requirements if needed
Write-Host "Checking dependencies..."
try {
    $requirementsPath = Join-Path $backendPath "requirements.txt"
    Write-Host "Installing requirements from: $requirementsPath"
    & "$venvPath\Scripts\pip.exe" install -r $requirementsPath
    Write-Host "Dependencies installed successfully"
}
catch {
    Write-Host "Error installing dependencies: $_"
    exit 1
}

# Recreate database
Write-Host "Setting up database..."
try {
    Set-Location $backendPath
    Write-Host "Running database setup..."
    & "$venvPath\Scripts\python.exe" recreate_db.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error recreating database"
        exit 1
    }
    Write-Host "Database recreated successfully"
    Set-Location $scriptPath
}
catch {
    Write-Host "Error setting up database: $_"
    exit 1
}

# Start the backend server in a new window
Write-Host "Starting backend server..."
try {
    $backendCommand = "Set-Location '$backendPath'; & '$venvPath\Scripts\Activate.ps1'; & '$venvPath\Scripts\python.exe' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
    Write-Host "Backend server started successfully"
}
catch {
    Write-Host "Error starting backend server: $_"
    exit 1
}

# Wait for backend to start
Write-Host "Waiting for backend to start..."
$maxAttempts = 10
$attempt = 0
while (-not (Test-PortInUse 8000) -and $attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $attempt++
}
if (-not (Test-PortInUse 8000)) {
    Write-Host "Error: Backend server failed to start"
    exit 1
}
Write-Host "Backend server is running on port 8000"

# Start the frontend server
Write-Host "Starting frontend server..."
try {
    Set-Location $frontendPath
    & "$venvPath\Scripts\python.exe" serve.py
}
catch {
    Write-Host "Error starting frontend server: $_"
    exit 1
} 