#!/bin/bash

echo "🚀 Starting Arcadia Hub..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Run the application
echo ""
echo "🎮 Starting Arcadia Hub..."
echo "Visit: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python app.py
