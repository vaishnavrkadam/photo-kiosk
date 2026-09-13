@echo off
title Epson PM-520 Kiosk Laptop Print Agent
color 0b

echo ====================================================
echo   Epson PM-520 Kiosk - Laptop Print Agent
echo ====================================================
echo.
echo Connecting to hosted cloud server and waiting for jobs...
echo (Ensure printer is powered on and connected via USB)
echo.

python print_agent.py

pause
