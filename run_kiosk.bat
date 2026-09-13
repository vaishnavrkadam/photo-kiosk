@echo off
title Epson PM-520 Smart Photo Kiosk Server
color 0A

echo ============================================================
echo   EPSON PICTUREMATE PM-520 PHOTO PRINT KIOSK
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -c "import flask, razorpay, PIL, win32print" 2>nul
if %errorlevel% neq 0 (
    echo Installing missing packages...
    pip install flask razorpay pillow pywin32 qrcode requests
)

echo [2/3] Generating access QR Code...
python generate_qr.py

echo [3/3] Starting Kiosk Server on http://localhost:5000...
echo.
echo ------------------------------------------------------------
echo Operator Dashboard: http://localhost:5000/admin
echo Customer Interface: http://localhost:5000
echo ------------------------------------------------------------
echo.

start http://localhost:5000/admin
python app.py

pause
