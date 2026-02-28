#!/bin/bash
# Monitor game generation and open in browser when ready

PROCESS_ID=$1

if [ -z "$PROCESS_ID" ]; then
    echo "Usage: $0 <process_id>"
    echo ""
    echo "Example:"
    echo "  $0 ca83f27b-da1e-452a-a278-8698ed310de8"
    exit 1
fi

echo "Monitoring game generation for process: $PROCESS_ID"
echo ""

MAX_WAIT=300  # 5 minutes
ELAPSED=0
INTERVAL=3

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(curl -s "http://localhost:8000/api/generate/$PROCESS_ID/status" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        STATUS_VALUE=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
        CURRENT_AGENT=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('current_agent', 'N/A'))" 2>/dev/null || echo "N/A")
        
        echo "[$ELAPSED s] Status: $STATUS_VALUE | Current Agent: $CURRENT_AGENT"
        
        if [ "$STATUS_VALUE" = "completed" ]; then
            echo ""
            echo "✅ Game generation completed!"
            echo ""
            echo "Opening in browser..."
            open "http://localhost:3000/game/$PROCESS_ID" 2>/dev/null || \
            xdg-open "http://localhost:3000/game/$PROCESS_ID" 2>/dev/null || \
            echo "Please open: http://localhost:3000/game/$PROCESS_ID"
            exit 0
        elif [ "$STATUS_VALUE" = "error" ]; then
            ERROR=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', 'Unknown error'))" 2>/dev/null || echo "Unknown error")
            echo ""
            echo "❌ Game generation failed: $ERROR"
            exit 1
        fi
    else
        echo "[$ELAPSED s] Waiting for backend..."
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "⏱️  Timeout reached. Check status manually:"
echo "   curl http://localhost:8000/api/generate/$PROCESS_ID/status"
echo ""
echo "Or view in browser:"
echo "   http://localhost:3000/game/$PROCESS_ID"
