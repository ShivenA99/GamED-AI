#!/bin/bash
# Setup Ollama for GamED.AI local LLM inference

set -e

echo "=========================================="
echo "GamED.AI Ollama Setup"
echo "=========================================="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing via Homebrew..."
            brew install ollama
        else
            echo "Please install Homebrew first, or install Ollama manually from https://ollama.com"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Installing via official script..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Unsupported OS. Please install Ollama manually from https://ollama.com"
        exit 1
    fi
else
    echo "✓ Ollama is already installed"
fi

# Start Ollama service (if not running)
echo ""
echo "Starting Ollama service..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 3
    echo "✓ Ollama service started"
else
    echo "✓ Ollama service is already running"
fi

# Check if Ollama is accessible
echo ""
echo "Checking Ollama connection..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is accessible at http://localhost:11434"
else
    echo "⚠ Warning: Cannot connect to Ollama. Make sure it's running."
    echo "  Try: ollama serve"
fi

# Pull recommended models
echo ""
echo "Pulling recommended models..."
echo ""

echo "1. Pulling llama3.2 (fast, good for most tasks)..."
ollama pull llama3.2 || echo "⚠ Failed to pull llama3.2"

echo ""
echo "2. Pulling qwen2.5:7b (better quality for complex tasks)..."
ollama pull qwen2.5:7b || echo "⚠ Failed to pull qwen2.5:7b"

echo ""
echo "3. Pulling VLM model for zone labeling..."
echo "   Detecting system specs..."

# Check available RAM (rough estimate)
if command -v sysctl &> /dev/null; then
    TOTAL_RAM_GB=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
    echo "   Detected RAM: ${TOTAL_RAM_GB}GB"
    
    if [ "$TOTAL_RAM_GB" -lt 32 ]; then
        echo "   Using llava:7b (optimized for systems with <32GB RAM)"
        ollama pull llava:7b || echo "⚠ Failed to pull llava:7b"
        echo ""
        echo "   Note: For better quality (if you have more RAM), you can also run:"
        echo "     ollama pull llava:latest"
    else
        echo "   Using llava:latest (system has sufficient RAM)"
        ollama pull llava:latest || echo "⚠ Failed to pull llava:latest"
    fi
else
    # Default to smaller model for safety
    echo "   Using llava:7b (default for compatibility)"
    ollama pull llava:7b || echo "⚠ Failed to pull llava:7b"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To use Ollama with GamED.AI:"
echo "  export USE_OLLAMA=true"
echo "  export FORCE_TEMPLATE=LABEL_DIAGRAM  # For image pipeline testing"
echo ""
echo "Verify VLM is working:"
echo "  PYTHONPATH=. python scripts/verify_vlm.py"
echo ""
echo "For Apple Silicon (M1/M2/M3/M4), Ollama runs natively and efficiently."
echo ""
echo "Test Ollama:"
echo "  ollama run llama3.2 'Hello, world!'"
echo ""
