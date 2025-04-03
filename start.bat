@echo off
echo Starting Attendance System...

:: Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: PowerShell is not installed or not in PATH
    pause
    exit /b 1
)

:: Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"

:: If PowerShell script failed
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to start the system
    pause
    exit /b 1
)

cd "C:\Users\Public\proj. y\attendance_system"