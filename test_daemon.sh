#!/usr/bin/env bash
# Test script for Vidurai Daemon

set -e

echo "🧪 Testing Vidurai Daemon..."
echo ""

# Start daemon in background
echo "1. Starting daemon..."
python3 daemon.py &
DAEMON_PID=$!
sleep 3

# Test health endpoint
echo "2. Testing health endpoint..."
HEALTH=$(curl -s http://localhost:7777/health)
echo "   Response: $HEALTH"

if echo "$HEALTH" | grep -q '"status":"alive"'; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    kill $DAEMON_PID
    exit 1
fi

# Test dashboard
echo "3. Testing dashboard..."
DASHBOARD=$(curl -s http://localhost:7777/)
if echo "$DASHBOARD" | grep -q "VIDURAI GHOST DAEMON"; then
    echo "   ✅ Dashboard loaded"
else
    echo "   ❌ Dashboard failed"
    kill $DAEMON_PID
    exit 1
fi

# Test metrics
echo "4. Testing metrics endpoint..."
METRICS=$(curl -s http://localhost:7777/metrics)
echo "   Response: $METRICS"
if echo "$METRICS" | grep -q '"files_watched"'; then
    echo "   ✅ Metrics working"
else
    echo "   ❌ Metrics failed"
    kill $DAEMON_PID
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "Daemon PID: $DAEMON_PID"
echo "Dashboard: http://localhost:7777"
echo ""
echo "Kill daemon with: kill $DAEMON_PID"
