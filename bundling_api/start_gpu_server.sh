#!/bin/bash

# Start GPU-optimized local image server for cloudflared tunnel
# This will run on port 8081 which is tunneled via image.huggle.tech

echo "🚀 Starting GPU-Optimized Image Server for cloudflared tunnel..."
echo "=============================================="
echo "Local server: http://localhost:8081"
echo "Public URL: https://image.huggle.tech"
echo "API endpoint: https://api.huggle.tech"
echo ""
echo "Make sure your cloudflared tunnel is running:"
echo "  image.huggle.tech -> localhost:8081"
echo "  api.huggle.tech -> localhost:8080"
echo ""

# Start the server
python3 local_image_server_gpu_optimized.py