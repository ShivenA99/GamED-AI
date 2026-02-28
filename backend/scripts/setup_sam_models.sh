#!/bin/bash
# Setup SAM (Segment Anything Model) for GamED.AI image segmentation
# NOTE: For Apple Silicon, use setup_sam3_apple_silicon.sh instead (optimized)

set -e

echo "=========================================="
echo "GamED.AI SAM Model Setup (Legacy)"
echo "=========================================="
echo ""
echo "⚠ NOTE: SAM3 is now preferred. For Apple Silicon, use:"
echo "   ./scripts/setup_sam3_apple_silicon.sh"
echo ""
read -p "Continue with SAM v1/SAM2 setup? (y/n) [n]: " continue_choice
continue_choice=${continue_choice:-n}
if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
    echo "Exiting. Run ./scripts/setup_sam3_apple_silicon.sh for SAM3 setup."
    exit 0
fi
echo ""

# Default model directory
MODELS_DIR="${MODELS_DIR:-$(pwd)/pretrained_models}"
mkdir -p "$MODELS_DIR"

echo "Models will be downloaded to: $MODELS_DIR"
echo ""

# SAM v1 Models
echo "SAM v1 Model Checkpoints:"
echo "  1. sam_vit_b.pth (~375MB) - Smallest, fastest [RECOMMENDED]"
echo "  2. sam_vit_l.pth (~1.2GB) - Medium quality"
echo "  3. sam_vit_h.pth (~2.4GB) - Highest quality"
echo ""

read -p "Which SAM v1 model to download? (1/2/3) [1]: " sam_choice
sam_choice=${sam_choice:-1}

case $sam_choice in
    1)
        SAM_MODEL="sam_vit_b"
        SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
        ;;
    2)
        SAM_MODEL="sam_vit_l"
        SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth"
        ;;
    3)
        SAM_MODEL="sam_vit_h"
        SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
        ;;
    *)
        echo "Invalid choice. Using sam_vit_b (default)"
        SAM_MODEL="sam_vit_b"
        SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
        ;;
esac

SAM_PATH="$MODELS_DIR/${SAM_MODEL}.pth"

echo ""
echo "Downloading $SAM_MODEL..."
if [ -f "$SAM_PATH" ]; then
    echo "✓ $SAM_MODEL already exists at $SAM_PATH"
else
    echo "Downloading from $SAM_URL..."
    curl -L -o "$SAM_PATH" "$SAM_URL"
    echo "✓ Downloaded $SAM_MODEL to $SAM_PATH"
fi

# Ask about SAM2
echo ""
read -p "Download SAM2 model? (y/n) [n]: " sam2_choice
sam2_choice=${sam2_choice:-n}

if [[ "$sam2_choice" == "y" || "$sam2_choice" == "Y" ]]; then
    echo ""
    echo "SAM2 Model Checkpoints:"
    echo "  1. sam2_hiera_tiny (~50MB) - Smallest"
    echo "  2. sam2_hiera_small (~100MB) - Small"
    echo "  3. sam2_hiera_base_plus (~200MB) - Recommended"
    echo "  4. sam2_hiera_large (~1GB) - Largest"
    echo ""
    
    read -p "Which SAM2 model? (1/2/3/4) [3]: " sam2_model_choice
    sam2_model_choice=${sam2_model_choice:-3}
    
    case $sam2_model_choice in
        1)
            SAM2_MODEL="sam2_hiera_tiny"
            SAM2_TYPE="sam2_hiera_tiny"
            ;;
        2)
            SAM2_MODEL="sam2_hiera_small"
            SAM2_TYPE="sam2_hiera_small"
            ;;
        3)
            SAM2_MODEL="sam2_hiera_base_plus"
            SAM2_TYPE="sam2_hiera_base_plus"
            ;;
        4)
            SAM2_MODEL="sam2_hiera_large"
            SAM2_TYPE="sam2_hiera_large"
            ;;
        *)
            SAM2_MODEL="sam2_hiera_base_plus"
            SAM2_TYPE="sam2_hiera_base_plus"
            ;;
    esac
    
    # SAM2 models are typically installed via pip, not downloaded directly
    echo ""
    echo "SAM2 models are installed via pip. To use SAM2:"
    echo "  pip install git+https://github.com/facebookresearch/segment-anything-2.git"
    echo ""
    echo "Then set in .env:"
    echo "  SAM2_MODEL_TYPE=$SAM2_TYPE"
    echo ""
    echo "Note: SAM2 requires the model files to be in the package installation."
    echo "The model type determines which checkpoint is used."
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Add to your .env file:"
echo "  SAM_MODEL_PATH=$SAM_PATH"
if [[ "$sam2_choice" == "y" || "$sam2_choice" == "Y" ]]; then
    echo "  SAM2_MODEL_TYPE=$SAM2_TYPE"
fi
echo ""
echo "Test SAM installation:"
echo "  PYTHONPATH=. python scripts/verify_sam.py"
echo ""
