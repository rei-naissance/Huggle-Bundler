#!/bin/bash

# Local Testing Startup Script
# This script helps you test both the image server and main API locally

echo "🧪 Local Bundle Image Generation Testing"
echo "========================================"
echo ""

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Activating .venv..."
    source .venv/bin/activate
fi

echo ""
echo "🖥️  System Info:"
python -c "
import torch
print('🔥 PyTorch version:', torch.__version__)
print('🖥️  CUDA available:', torch.cuda.is_available())
print('💻 Device:', 'GPU' if torch.cuda.is_available() else 'CPU')
"

echo ""
echo "📋 Testing Options:"
echo "1. Start Local Image Server (Port 8001)"
echo "2. Test Image Server Connection"  
echo "3. Start Main Bundle API (Port 8000)"
echo "4. Run Full Integration Test"
echo ""

read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo "🚀 Starting Local Image Server..."
        echo "This will download Stable Diffusion v1.5 (~4GB) on first run"
        echo "Press Ctrl+C to stop"
        echo ""
        python local_image_server.py
        ;;
    2)
        echo "🔌 Testing Image Server Connection..."
        python test_local_image_server.py
        ;;
    3)
        echo "🚀 Starting Main Bundle API..."
        echo "Make sure the Image Server (option 1) is running first!"
        echo "Press Ctrl+C to stop"
        echo ""
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    4)
        echo "🧪 Running Full Integration Test..."
        echo "This will test the complete bundle image generation flow"
        echo ""
        python test_local_image_server.py
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac