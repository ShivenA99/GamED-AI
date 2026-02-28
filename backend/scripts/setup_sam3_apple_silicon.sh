#!/bin/bash
# Setup SAM3 for Apple Silicon (M1/M2/M3/M4) - Optimized with MLX

set -e

echo "=========================================="
echo "GamED.AI SAM3 Setup for Apple Silicon"
echo "=========================================="
echo ""

# Detect Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "⚠ Warning: This script is optimized for Apple Silicon (arm64)"
    echo "   Your system: $(uname -m)"
    echo "   You can still use official SAM3, but MLX won't be available"
    echo ""
    read -p "Continue anyway? (y/n) [y]: " continue_choice
    continue_choice=${continue_choice:-y}
    if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
        exit 0
    fi
    USE_MLX=false
else
    echo "✓ Detected Apple Silicon (arm64)"
    USE_MLX=true
fi

echo ""
echo "SAM3 Installation Options:"
echo "  1. MLX version (Apple Silicon optimized, recommended for M1/M2/M3/M4)"
echo "  2. Official SAM3 (works on all platforms)"
echo ""

read -p "Which version? (1/2) [1]: " version_choice
version_choice=${version_choice:-1}

if [ "$version_choice" == "1" ] && [ "$USE_MLX" == "true" ]; then
    echo ""
    echo "Installing SAM3 MLX (Apple Silicon optimized)..."
    echo ""
    
    # Check if MLX is available
    if ! python3 -c "import mlx" 2>/dev/null; then
        echo "Installing MLX framework..."
        pip install mlx
    fi
    
    # Install MLX SAM3
    echo "Installing mlx-sam3-image..."
    pip install git+https://github.com/mlx-community/sam3-image.git || {
        echo "⚠ Failed to install from GitHub, trying alternative..."
        pip install sam3-image
    }
    
    echo ""
    echo "✓ SAM3 MLX installed"
    echo ""
    echo "⚠️ IMPORTANT: HuggingFace Authentication Required"
    echo "   SAM3 models are hosted on HuggingFace. You need to authenticate:"
    echo "   pip install huggingface_hub"
    echo "   huggingface-cli login"
    echo ""
    echo "Add to your .env file:"
    echo "  USE_SAM3_MLX=true"
    echo "  SAM3_MLX_MODEL=mlx-community/sam3-image"
    echo ""
    echo "The model will be automatically downloaded from HuggingFace on first use."
    
elif [ "$version_choice" == "2" ] || [ "$USE_MLX" == "false" ]; then
    echo ""
    echo "Installing official SAM3..."
    echo ""
    
    pip install sam3
    
    echo ""
    echo "✓ Official SAM3 installed"
    echo ""
    echo "⚠️ IMPORTANT: HuggingFace Authentication Required"
    echo "   SAM3 models are hosted on HuggingFace. You need to authenticate:"
    echo "   pip install huggingface_hub"
    echo "   huggingface-cli login"
    echo ""
    echo "Add to your .env file:"
    echo "  USE_SAM3_MLX=false"
    echo "  SAM3_MODEL_PATH=/path/to/sam3_checkpoint  # Optional, will download if not set"
    echo ""
    echo "Note: Official SAM3 may require PyTorch. For Apple Silicon, MLX version is recommended."
    
else
    echo "⚠ MLX version requires Apple Silicon. Installing official SAM3 instead..."
    pip install sam3
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Test SAM3 installation:"
echo "  PYTHONPATH=. python scripts/verify_sam.py"
echo ""
