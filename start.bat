@echo off
echo 🚀 Starting Arcadia Hub...
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo 📦 Installing dependencies...
pip install -q -r requirements.txt

REM Run the application
echo.
echo 🎮 Starting Arcadia Hub...
echo Visit: http://localhost:5000
echo Press Ctrl+C to stop
echo.

python app.py
