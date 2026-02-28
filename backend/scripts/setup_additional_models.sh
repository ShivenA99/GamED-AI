#!/bin/bash
# Setup Additional Local AI Models for M4 MacBook Pro 16GB
# This script installs recommended models beyond the basic setup

set -e

echo "=========================================="
echo "Additional Local AI Models Setup"
echo "For M4 MacBook Pro 16GB"
echo "=========================================="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed!"
    echo "Please install Ollama first:"
    echo "  brew install ollama"
    echo "  or visit: https://ollama.com"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama server is not running. Starting..."
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "❌ Could not start Ollama. Please start manually: ollama serve"
        exit 1
    fi
fi

echo "✅ Ollama is running"
echo ""

# Function to pull model with error handling
pull_model() {
    local model=$1
    local description=$2
    
    echo "📥 Pulling $model..."
    echo "   $description"
    if ollama pull "$model"; then
        echo "   ✅ $model installed successfully"
    else
        echo "   ⚠️  Failed to pull $model (may already be installed or unavailable)"
    fi
    echo ""
}

# Reasoning Models
echo "=== Reasoning Models ==="
pull_model "deepseek-r1:7b" "Advanced reasoning for validators/judges"
pull_model "deepseek-r1:1.5b" "Lightweight reasoning model"

# Alternative General Models
echo "=== Alternative General Models ==="
pull_model "phi3:mini" "Fast reasoning (4B parameters)"
pull_model "mistral:7b" "Fast general-purpose model"
pull_model "llama3.1:8b" "More capable than 3.2 (if needed)"

# Alternative Code Models
echo "=== Alternative Code Models ==="
pull_model "codellama:7b" "Alternative code generation model"
pull_model "starcoder2:7b" "Code completion specialist"

# Vision Models (if not already installed)
echo "=== Vision Models ==="
pull_model "qwen2.5-vl:7b" "High-quality vision-language model"
pull_model "llava:latest" "General vision-language model"

echo "=========================================="
echo "✅ Model installation complete!"
echo ""
echo "Next steps:"
echo "1. Test models: ollama run deepseek-r1:7b 'Solve: 2x + 5 = 15'"
echo "2. Update backend/app/config/models.py with new model configs"
echo "3. See docs/LOCAL_AI_MODELS_M4_RESEARCH.md for usage recommendations"
echo ""
echo "To use these models, set in your .env:"
echo "  AGENT_MODEL_JUDGE=local-deepseek-r1"
echo "  AGENT_MODEL_CRITIC=local-deepseek-r1"
echo ""
