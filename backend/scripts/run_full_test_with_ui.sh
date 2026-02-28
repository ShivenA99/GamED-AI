#!/bin/bash
# Complete setup and test script for LABEL_DIAGRAM with UI access

set -e

echo "=========================================="
echo "LABEL_DIAGRAM Full Test with UI"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

# 1. Check/Start Ollama
echo "1. Checking Ollama..."
if ! pgrep -x ollama > /dev/null; then
    echo "   Starting Ollama server..."
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    echo "   ✅ Ollama started"
else
    echo "   ✅ Ollama already running"
fi

# Check if Ollama is accessible
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ⚠️  Ollama not accessible, waiting 5 seconds..."
    sleep 5
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "   ❌ Ollama still not accessible. Please start manually: ollama serve"
        exit 1
    fi
fi
echo "   ✅ Ollama is accessible"

# 2. Check/Pull required models
echo ""
echo "2. Checking models..."
MODELS=("llama3.2" "qwen2.5:7b" "deepseek-coder:6.7b")
for model in "${MODELS[@]}"; do
    if curl -s http://localhost:11434/api/tags | grep -q "$model"; then
        echo "   ✅ $model available"
    else
        echo "   📥 Pulling $model..."
        ollama pull "$model" || echo "   ⚠️  Failed to pull $model (may still work)"
    fi
done

# 3. Activate venv and run test
echo ""
echo "3. Running LABEL_DIAGRAM test..."
source venv/bin/activate

# Run test and capture process ID
TEST_OUTPUT=$(FORCE_TEMPLATE=LABEL_DIAGRAM TOPOLOGY=T0 PYTHONPATH=. python scripts/test_label_diagram.py 2>&1)
echo "$TEST_OUTPUT"

# Extract process ID if available (from saved JSON file)
LATEST_OUTPUT=$(ls -t pipeline_outputs/label_diagram_test_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_OUTPUT" ]; then
    echo ""
    echo "   ✅ Test output saved to: $LATEST_OUTPUT"
    
    # Try to extract process_id if it's in the file
    PROCESS_ID=$(python3 -c "import json, sys; data=json.load(open('$LATEST_OUTPUT')); print(data.get('process_id', ''))" 2>/dev/null || echo "")
    
    if [ -z "$PROCESS_ID" ]; then
        # Generate via API instead
        echo ""
        echo "4. Generating game via API..."
        API_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/generate?question_text=Label%20the%20parts%20of%20a%20flower%20including%20the%20petal%2C%20sepal%2C%20stamen%2C%20pistil%2C%20ovary%2C%20and%20receptacle" \
            -H "Content-Type: application/json" 2>/dev/null || echo '{"process_id":""}')
        PROCESS_ID=$(echo "$API_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('process_id', ''))" 2>/dev/null || echo "")
    fi
else
    echo "   ⚠️  No test output file found"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Backend Server (in a new terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "2. Start Frontend Server (in another terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
if [ -n "$PROCESS_ID" ]; then
    echo "3. View your game:"
    echo "   http://localhost:3000/game/$PROCESS_ID"
    echo ""
fi
echo "4. Or generate a new game:"
echo "   http://localhost:3000"
echo ""
