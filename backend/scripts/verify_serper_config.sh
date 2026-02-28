#!/bin/bash
# Verify SERPER_API_KEY is configured correctly

echo "=========================================="
echo "SERPER API Key Configuration Check"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

# Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if SERPER_API_KEY is set
if [ -z "$SERPER_API_KEY" ]; then
    echo "❌ SERPER_API_KEY is NOT set in environment"
    echo ""
    echo "To fix:"
    echo "1. Add to backend/.env:"
    echo "   SERPER_API_KEY=your-serper-api-key-here"
    echo "   USE_IMAGE_DIAGRAMS=true"
    echo ""
    echo "2. Get free API key at: https://serper.dev"
    echo ""
    exit 1
else
    KEY_LEN=${#SERPER_API_KEY}
    if [ $KEY_LEN -lt 10 ]; then
        echo "⚠️  SERPER_API_KEY is set but seems too short (${KEY_LEN} chars)"
        echo "   Expected: 20+ characters"
    else
        echo "✅ SERPER_API_KEY is set (${KEY_LEN} characters)"
        echo "   First 10 chars: ${SERPER_API_KEY:0:10}..."
    fi
fi

echo ""

# Check USE_IMAGE_DIAGRAMS
if [ "$USE_IMAGE_DIAGRAMS" = "true" ]; then
    echo "✅ USE_IMAGE_DIAGRAMS=true (image retrieval enabled)"
else
    echo "⚠️  USE_IMAGE_DIAGRAMS is not 'true' (currently: ${USE_IMAGE_DIAGRAMS:-not set})"
    echo "   Image retrieval will be skipped"
    echo "   To enable: Set USE_IMAGE_DIAGRAMS=true in .env"
fi

echo ""
echo "=========================================="
echo "Services Using SERPER_API_KEY:"
echo "=========================================="
echo ""
echo "1. ✅ Domain Knowledge Retriever"
echo "   - Uses: get_serper_client().search()"
echo "   - Purpose: Web search for canonical labels"
echo ""
echo "2. ✅ Diagram Image Retriever"
echo "   - Uses: get_serper_client().search_images()"
echo "   - Purpose: Image search for diagram images"
echo "   - Requires: USE_IMAGE_DIAGRAMS=true"
echo ""
echo "Both services use the same SERPER_API_KEY from environment."
echo ""
