#!/bin/bash
# Start topology tests with logging enabled

cd /Users/shivenagarwal/Hackathon-Anthropic/Claude_Hackathon/backend
source venv/bin/activate
export USE_OLLAMA=true
export FORCE_TEMPLATE=STATE_TRACER_CODE
export PYTHONUNBUFFERED=1

echo "Starting topology tests..."
echo "Logs will be saved to: test_output.log"
echo ""

python3 -u scripts/test_all_topologies.py --topology T0 --topology T1 2>&1 | tee test_output.log
