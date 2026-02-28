#!/bin/bash
# Setup coding models for GamED.AI code generation

set -e

echo "=========================================="
echo "GamED.AI Coding Models Setup"
echo "=========================================="
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠ Warning: Ollama is not running. Start it with: ollama serve"
    echo ""
fi

echo "Pulling coding models for better code generation..."
echo ""

echo "1. Pulling deepseek-coder:6.7b (best for code generation)..."
echo "   This model excels at generating React/TypeScript code"
ollama pull deepseek-coder:6.7b || {
    echo "⚠ Failed to pull deepseek-coder:6.7b"
    echo "   You can try: ollama pull deepseek-coder (latest version)"
}

echo ""
echo "2. Pulling qwen2.5-coder:7b (good for structured output & TypeScript)..."
echo "   This model is excellent for JSON/structured output and TypeScript"
ollama pull qwen2.5-coder:7b || {
    echo "⚠ Failed to pull qwen2.5-coder:7b"
    echo "   Falling back to qwen2.5:7b..."
    ollama pull qwen2.5:7b || echo "⚠ Failed to pull qwen2.5:7b"
}

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Available models for code generation:"
echo "  - deepseek-coder:6.7b (code generation)"
echo "  - qwen2.5-coder:7b (structured output, TypeScript)"
echo ""
echo "These models will be used automatically when USE_OLLAMA=true"
echo ""
