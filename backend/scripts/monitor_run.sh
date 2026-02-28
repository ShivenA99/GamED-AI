#!/bin/bash
# Monitor a pipeline run and show progress

PROCESS_ID="${1:-}"

if [ -z "$PROCESS_ID" ]; then
    echo "Usage: ./monitor_run.sh <process_id>"
    echo ""
    echo "Example:"
    echo "  ./monitor_run.sh 01eee0f5-f835-4586-aab5-48e5b88e411e"
    exit 1
fi

echo "🔍 Monitoring process: $PROCESS_ID"
echo "   View game: http://localhost:3000/game/$PROCESS_ID"
echo ""

while true; do
    STATUS=$(curl -s "http://localhost:8000/api/generate/$PROCESS_ID/status" 2>/dev/null)
    
    if [ -z "$STATUS" ] || [ "$STATUS" = "null" ]; then
        echo "⏳ Process not found yet (may still be initializing)..."
        sleep 2
        continue
    fi
    
    CURRENT_AGENT=$(echo "$STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('current_agent', 'N/A'))" 2>/dev/null)
    PROGRESS=$(echo "$STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('progress_percent', 0))" 2>/dev/null)
    STATUS_TEXT=$(echo "$STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'N/A'))" 2>/dev/null)
    ERROR=$(echo "$STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('error_message', ''))" 2>/dev/null)
    
    echo -ne "\r📊 Status: $STATUS_TEXT | Agent: $CURRENT_AGENT | Progress: $PROGRESS%"
    
    if [ "$STATUS_TEXT" = "completed" ] || [ "$STATUS_TEXT" = "error" ]; then
        echo ""
        echo ""
        if [ "$STATUS_TEXT" = "completed" ]; then
            echo "✅ Generation complete!"
        else
            echo "❌ Generation failed: $ERROR"
        fi
        echo "   View game: http://localhost:3000/game/$PROCESS_ID"
        break
    fi
    
    sleep 2
done
