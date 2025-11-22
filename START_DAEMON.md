# 🚀 Vidurai Daemon - Manual Start Guide

## Quick Start Command

```bash
cd /home/user/vidurai/vidurai-daemon && nohup python3 daemon.py > daemon.log 2>&1 &
```

This single command will:
- Navigate to the daemon directory
- Start the daemon in background (`nohup ... &`)
- Redirect all output to `daemon.log`
- Keep running even if terminal closes

---

## Step-by-Step Commands

If you prefer to do it step by step:

```bash
# 1. Navigate to daemon directory
cd /home/user/vidurai/vidurai-daemon

# 2. Start daemon in background
nohup python3 daemon.py > daemon.log 2>&1 &
```

---

## Verify Daemon is Running

```bash
# Check health endpoint
curl http://localhost:7777/health

# Expected response:
# {"status": "alive", "version": "2.5.0", ...}
```

Or with pretty formatting:
```bash
curl -s http://localhost:7777/health | python3 -m json.tool
```

---

## View Daemon Logs

```bash
# View last 50 lines
tail -50 /home/user/vidurai/vidurai-daemon/daemon.log

# Follow logs in real-time
tail -f /home/user/vidurai/vidurai-daemon/daemon.log

# Search for errors
grep ERROR /home/user/vidurai/vidurai-daemon/daemon.log

# Check Human-AI Whisperer logs
grep "🎭\|🧠\|✨" /home/user/vidurai/vidurai-daemon/daemon.log
```

---

## Stop Daemon

```bash
# Kill the daemon process
pkill -f "python.*daemon.py"
```

---

## Restart Daemon

```bash
# Stop and start in one go
cd /home/user/vidurai/vidurai-daemon && pkill -f "python.*daemon.py" && nohup python3 daemon.py > daemon.log 2>&1 &
```

---

## Check if Daemon is Already Running

```bash
# Check process
ps aux | grep "python.*daemon.py" | grep -v grep

# Or check the port
lsof -i :7777

# Or just try the health endpoint
curl http://localhost:7777/health
```

---

## Troubleshooting

### Issue: "Connection refused"

**Cause**: Daemon not running or still starting up

**Solution**:
```bash
# Check if daemon is running
ps aux | grep daemon.py

# Check logs for errors
tail -30 /home/user/vidurai/vidurai-daemon/daemon.log

# If not running, start it
cd /home/user/vidurai/vidurai-daemon && nohup python3 daemon.py > daemon.log 2>&1 &
```

---

### Issue: "Port already in use"

**Cause**: Another daemon instance or process using port 7777

**Solution**:
```bash
# Find what's using port 7777
lsof -i :7777

# Kill the old daemon
pkill -f "python.*daemon.py"

# Wait 2 seconds
sleep 2

# Start fresh daemon
cd /home/user/vidurai/vidurai-daemon && nohup python3 daemon.py > daemon.log 2>&1 &
```

---

### Issue: Daemon crashes immediately

**Solution**:
```bash
# Check last error in logs
tail -100 /home/user/vidurai/vidurai-daemon/daemon.log | grep -A 10 ERROR

# Common fixes:
# 1. Missing dependencies
pip install -r requirements.txt

# 2. Permission issues
chmod +x daemon.py

# 3. Python version
python3 --version  # Should be 3.8+
```

---

## What Happens on Startup

When you start the daemon, it will:

1. **Initialize Intelligence** (2-3 seconds)
   - Load HumanAIWhisperer (🎭)
   - Load ContextMediator (🧠)
   - Initialize compression models

2. **Auto-detect Projects** (5-10 seconds)
   - Scan for VS Code workspaces
   - Prioritize by recency
   - Start watching top 5 projects

3. **Start Services** (1 second)
   - HTTP server on port 7777
   - WebSocket server for browser extension
   - File watchers for each project

4. **Ready** (Total: ~10 seconds)
   - Health endpoint responding
   - Ready to serve WOW contexts

---

## Expected Log Output

On successful startup, you should see:

```
╔═══════════════════════════════════════════════╗
║   🧠 VIDURAI GHOST DAEMON                     ║
║   विस्मृति भी विद्या है                        ║
╚═══════════════════════════════════════════════╝

[INFO] 🎭 Human-AI Whisperer initialized
[INFO] 🧠 Context Mediator initialized with Human-AI Whisperer
[INFO] 📊 Prioritized 5 projects to watch
[INFO] 👁️  Now watching: vidurai-website (16 files)
[INFO] 👁️  Now watching: vidurai-docs (75 files)
[INFO] 👁️  Now watching: vidurai (176 files)
[INFO] ✅ Auto-detection complete!
[INFO] Application startup complete.
[INFO] Uvicorn running on http://0.0.0.0:7777
```

---

## Current Status

✅ **Daemon is RUNNING**

```json
{
  "status": "alive",
  "version": "2.5.0",
  "watched_projects": 5,
  "files_watched": 338,
  "active_connections": 2
}
```

---

## Browser Extension

After starting the daemon, the browser extension should automatically connect via WebSocket.

You'll see in the logs:
```
[INFO] 🔌 WebSocket connected from 127.0.0.1
```

And in the browser console:
```
✅ Ghost Daemon connected
```

---

## Quick Reference Card

```bash
# START
cd /home/user/vidurai/vidurai-daemon && nohup python3 daemon.py > daemon.log 2>&1 &

# CHECK
curl http://localhost:7777/health

# LOGS
tail -f /home/user/vidurai/vidurai-daemon/daemon.log

# STOP
pkill -f "python.*daemon.py"

# RESTART
cd /home/user/vidurai/vidurai-daemon && pkill -f "python.*daemon.py" && nohup python3 daemon.py > daemon.log 2>&1 &
```

---

**विस्मृति भी विद्या है** - The daemon runs silently, watching, learning, whispering. 🎭
