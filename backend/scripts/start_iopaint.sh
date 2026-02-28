#!/bin/bash
# Start IOPaint server with LaMa model for inpainting
#
# This script starts the IOPaint server with:
# - LaMa model (best for removing text/annotations from images)
# - MPS device (Apple Metal Performance Shaders for M-series Macs)
# - Port 8080 (configurable via IOPAINT_PORT environment variable)
#
# Usage:
#   ./scripts/start_iopaint.sh
#
# Environment Variables:
#   IOPAINT_PORT - Port to run on (default: 8080)
#   IOPAINT_MODEL - Model to use (default: lama)
#   IOPAINT_DEVICE - Device to use: mps, cuda, cpu (default: mps)
#
# Requirements:
#   pip install iopaint
#
# Note: First run will download the LaMa model (~200MB)

set -e

IOPAINT_PORT=${IOPAINT_PORT:-8080}
IOPAINT_MODEL=${IOPAINT_MODEL:-lama}
IOPAINT_DEVICE=${IOPAINT_DEVICE:-mps}

echo "=================================================="
echo "Starting IOPaint Server for Label Diagram Inpainting"
echo "=================================================="
echo "Model: $IOPAINT_MODEL"
echo "Device: $IOPAINT_DEVICE"
echo "Port: $IOPAINT_PORT"
echo ""

# Check if iopaint is installed
if ! command -v iopaint &> /dev/null; then
    echo "Error: iopaint not found. Please install it:"
    echo "  pip install iopaint"
    exit 1
fi

# Check if port is already in use
if lsof -i:$IOPAINT_PORT &> /dev/null; then
    echo "Warning: Port $IOPAINT_PORT is already in use"
    echo "Checking if it's IOPaint..."
    if curl -s http://localhost:$IOPAINT_PORT/health &> /dev/null; then
        echo "IOPaint is already running on port $IOPAINT_PORT"
        exit 0
    else
        echo "Another process is using port $IOPAINT_PORT"
        echo "Either stop that process or set IOPAINT_PORT to a different value"
        exit 1
    fi
fi

echo "Starting IOPaint..."
echo "Once started, the server will be available at:"
echo "  http://localhost:$IOPAINT_PORT"
echo ""
echo "Add to your .env file:"
echo "  IOPAINT_URL=http://localhost:$IOPAINT_PORT"
echo ""

# Start IOPaint
iopaint start --model=$IOPAINT_MODEL --device=$IOPAINT_DEVICE --port=$IOPAINT_PORT
