#!/usr/bin/env python3
"""
Vidurai Ghost Daemon - The Invisible Infrastructure Layer
Runs as OS-level service, provides universal context to all AI tools
"""

import asyncio
import logging
from pathlib import Path
from typing import Set, Dict, Any
from datetime import datetime
import json
from threading import Thread
from queue import Queue

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn

from auto_detector import AutoDetector
from metrics_collector import MetricsCollector
from mcp_bridge import MCPBridge
from smart_file_watcher import SmartFileWatcher
from intelligence.context_mediator import ContextMediator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("vidurai.daemon")

app = FastAPI(
    title="Vidurai Ghost Daemon",
    version="2.5.0",
    description="Universal AI Context Protocol"
)

# CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
watched_projects: Dict[str, Observer] = {}
active_websockets: Set[WebSocket] = set()
event_queue: Queue = Queue()
metrics = {
    "files_watched": 0,
    "changes_detected": 0,
    "tokens_saved": 0,
    "contexts_served": 0,
    "started_at": datetime.now().isoformat(),
    "last_activity": None
}

# Global instances
auto_detector = AutoDetector()
metrics_collector = MetricsCollector()
mcp_bridge = MCPBridge()
context_mediator = ContextMediator()

# Pydantic model for context request
class ContextRequest(BaseModel):
    user_prompt: str
    ai_platform: str = "Unknown"

class ViduraiFileHandler(FileSystemEventHandler):
    """Watches file changes and broadcasts via WebSocket"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        super().__init__()

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        ignore_patterns = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', 'target', '.pytest_cache'
        }

        path_obj = Path(path)
        return any(pattern in path_obj.parts for pattern in ignore_patterns)

    def on_modified(self, event):
        if event.is_directory or self.should_ignore(event.src_path):
            return

        file_path = Path(event.src_path)

        logger.info(f"📝 File changed: {file_path.name}")
        metrics["changes_detected"] += 1
        metrics["last_activity"] = datetime.now().isoformat()

        # Put event in queue for async processing
        event_queue.put({
            "event": "file_changed",
            "path": str(file_path),
            "project": self.project_path,
            "filename": file_path.name,
            "timestamp": datetime.now().isoformat()
        })

async def broadcast_event(message: Dict[str, Any]):
    """Send event to all WebSocket clients"""
    dead_connections = set()

    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except:
            dead_connections.add(ws)

    # Clean up dead connections
    active_websockets.difference_update(dead_connections)

    if dead_connections:
        logger.info(f"🧹 Cleaned {len(dead_connections)} dead connections")

async def process_event_queue():
    """Background task to process file events from queue"""
    while True:
        try:
            if not event_queue.empty():
                event = event_queue.get_nowait()

                # Add event to context mediator for intelligence
                context_mediator.add_event(event)

                # Broadcast to WebSocket clients
                await broadcast_event(event)
            await asyncio.sleep(0.1)  # Small delay to avoid busy loop
        except Exception as e:
            logger.error(f"Error processing event queue: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Start background tasks and auto-detect projects on app startup"""
    # Start event queue processor
    asyncio.create_task(process_event_queue())

    logger.info("")
    logger.info("🚀 Running auto-detection...")
    logger.info("")

    # Detect editors
    editors = auto_detector.detect_active_editors()
    if editors:
        logger.info(f"📝 Detected editors: {', '.join(editors.keys())}")

    # Auto-discover projects
    projects = auto_detector.auto_discover_projects(max_projects=5)

    logger.info("")
    logger.info(f"👁️  Auto-watching {len(projects)} projects...")

    # Watch each project
    for project in projects:
        try:
            result = await watch_project(str(project))
            if result.get("status") == "watching":
                logger.info(f"   ✓ Watching: {project.name}")
        except Exception as e:
            logger.error(f"   ✗ Failed to watch {project.name}: {e}")

    logger.info("")
    logger.info("✅ Auto-detection complete!")
    logger.info("")

@app.get("/health")
def health_check():
    """Health endpoint for monitoring"""
    uptime = (datetime.now() - datetime.fromisoformat(metrics["started_at"])).total_seconds()

    return {
        "status": "alive",
        "version": "2.5.0",
        "uptime_seconds": uptime,
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "watched_projects": len(watched_projects),
        "active_connections": len(active_websockets),
        "metrics": metrics
    }

@app.get("/metrics")
def get_metrics():
    """Return detailed metrics for monitoring"""
    collector_metrics = metrics_collector.get_summary()

    return {
        **metrics,
        **collector_metrics,
        "watched_projects": len(watched_projects),
        "active_connections": len(active_websockets),
        "projects_list": list(watched_projects.keys())
    }

@app.post("/context/prepare")
async def prepare_intelligent_context(request: ContextRequest):
    """
    Prepare intelligent context for AI based on user's prompt
    This is the core of Vidurai's intelligence
    """
    try:
        # Use context mediator to prepare intelligent context
        intelligent_context = context_mediator.prepare_context_for_ai(
            request.user_prompt,
            request.ai_platform
        )

        metrics["contexts_served"] += 1

        return {
            "status": "success",
            "context": intelligent_context,
            "platform": request.ai_platform,
            "user_state": context_mediator.user_state,
            "length": len(intelligent_context)
        }
    except Exception as e:
        logger.error(f"Error preparing context: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_websockets.add(websocket)

    client_info = websocket.client
    logger.info(f"🔌 WebSocket connected from {client_info}. Total: {len(active_websockets)}")

    # Send initial state
    await websocket.send_json({
        "event": "connected",
        "message": "Vidurai Ghost Daemon connected",
        "watched_projects": list(watched_projects.keys()),
        "metrics": metrics
    })

    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received: {data}")

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected. Total: {len(active_websockets) - 1}")
    finally:
        active_websockets.discard(websocket)

@app.post("/watch")
async def watch_project(project_path: str):
    """Start watching a project directory"""
    path = Path(project_path).resolve()

    if not path.exists():
        return {"error": "Path does not exist", "path": str(path)}

    if str(path) in watched_projects:
        return {
            "status": "already_watching",
            "path": str(path),
            "message": "Project already being watched"
        }

    # Start watching with SmartFileWatcher
    event_handler = SmartFileWatcher(str(path), event_queue)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.start()

    watched_projects[str(path)] = observer

    # Count files
    file_count = sum(1 for _ in path.rglob('*') if _.is_file() and not event_handler.should_ignore(str(_)))
    metrics["files_watched"] += file_count

    logger.info(f"👁️  Now watching: {path.name} ({file_count} files)")

    # Broadcast to connected clients
    await broadcast_event({
        "event": "project_added",
        "path": str(path),
        "files": file_count,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "watching",
        "path": str(path),
        "files": file_count
    }

@app.delete("/watch")
async def unwatch_project(project_path: str):
    """Stop watching a project"""
    path = str(Path(project_path).resolve())

    if path not in watched_projects:
        return {"error": "Project not being watched"}

    observer = watched_projects[path]
    observer.stop()
    observer.join()
    del watched_projects[path]

    logger.info(f"👁️  Stopped watching: {path}")

    return {"status": "unwatched", "path": path}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Local dashboard at localhost:7777"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vidurai Ghost Daemon</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: linear-gradient(135deg, #0a0a0a 0%, #1a0a2e 100%);
                color: #10b981;
                font-family: 'Courier New', monospace;
                padding: 40px;
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 {
                font-size: 48px;
                background: linear-gradient(90deg, #10b981, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 30px;
                text-align: center;
            }
            .status {
                background: rgba(139, 92, 246, 0.1);
                border: 2px solid #8b5cf6;
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
            }
            .status-row {
                display: flex;
                justify-content: space-between;
                margin: 15px 0;
                font-size: 18px;
            }
            .live {
                color: #22c55e;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .metric-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .metric-card {
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid #10b981;
                border-radius: 8px;
                padding: 20px;
            }
            .metric-value {
                font-size: 36px;
                color: #8b5cf6;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                font-size: 14px;
                color: #10b981;
                text-transform: uppercase;
            }
            .projects-list {
                margin-top: 30px;
                background: rgba(139, 92, 246, 0.05);
                border: 1px solid #8b5cf6;
                border-radius: 8px;
                padding: 20px;
            }
            .project-item {
                padding: 10px;
                margin: 5px 0;
                background: rgba(16, 185, 129, 0.05);
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
            }
            .footer {
                text-align: center;
                margin-top: 50px;
                color: #8b5cf6;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 VIDURAI GHOST DAEMON</h1>

            <div class="status">
                <div class="status-row">
                    <span>Status:</span>
                    <span class="live">● ALIVE</span>
                </div>
                <div class="status-row">
                    <span>Uptime:</span>
                    <span id="uptime">Loading...</span>
                </div>
                <div class="status-row">
                    <span>Active Connections:</span>
                    <span id="connections">0</span>
                </div>
            </div>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Watched Projects</div>
                    <div class="metric-value" id="projects">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Files Monitored</div>
                    <div class="metric-value" id="files">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Changes Detected</div>
                    <div class="metric-value" id="changes">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Tokens Saved</div>
                    <div class="metric-value" id="tokens">0</div>
                </div>
            </div>

            <div class="projects-list">
                <h3>📁 Watched Projects</h3>
                <div id="project-list"></div>
            </div>

            <div class="footer">
                <p>विस्मृति भी विद्या है — "Forgetting too is knowledge"</p>
                <p>Vidurai Ghost Daemon v2.5.0</p>
            </div>
        </div>

        <script>
            let ws = null;

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:7777/ws');

                ws.onopen = () => {
                    console.log('🔌 WebSocket connected');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('📨 Received:', data);

                    if (data.event === 'file_changed') {
                        showNotification(`File changed: ${data.filename}`);
                    }
                };

                ws.onclose = () => {
                    console.log('🔌 WebSocket disconnected, reconnecting...');
                    setTimeout(connectWebSocket, 3000);
                };
            }

            function showNotification(message) {
                // Could add toast notification here
                console.log('🔔', message);
            }

            async function updateMetrics() {
                try {
                    const res = await fetch('/metrics');
                    const data = await res.json();

                    document.getElementById('files').textContent = data.files_watched.toLocaleString();
                    document.getElementById('changes').textContent = data.changes_detected.toLocaleString();
                    document.getElementById('tokens').textContent = data.tokens_saved.toLocaleString();

                    // Update project list
                    const projectList = document.getElementById('project-list');
                    projectList.innerHTML = data.projects_list.map(p =>
                        `<div class="project-item">
                            <span>📂 ${p.split('/').pop()}</span>
                            <span>${p}</span>
                        </div>`
                    ).join('') || '<p style="color: #8b5cf6; padding: 20px;">No projects being watched yet</p>';
                } catch (e) {
                    console.error('Failed to fetch metrics:', e);
                }
            }

            async function updateHealth() {
                try {
                    const res = await fetch('/health');
                    const data = await res.json();

                    document.getElementById('projects').textContent = data.watched_projects;
                    document.getElementById('connections').textContent = data.active_connections;
                    document.getElementById('uptime').textContent = data.uptime_human;
                } catch (e) {
                    console.error('Failed to fetch health:', e);
                }
            }

            // Initialize
            connectWebSocket();
            updateMetrics();
            updateHealth();

            // Update every second
            setInterval(() => {
                updateMetrics();
                updateHealth();
            }, 1000);
        </script>
    </body>
    </html>
    """

def main():
    logger.info("""
╔══════════════════════════════════════════╗
║   🧠 VIDURAI GHOST DAEMON                ║
║   The Invisible Infrastructure Layer     ║
║   Universal AI Context Protocol          ║
╚══════════════════════════════════════════╝
    """)
    logger.info("🌐 Dashboard: http://localhost:7777")
    logger.info("🔌 WebSocket: ws://localhost:7777/ws")
    logger.info("💓 Health: http://localhost:7777/health")
    logger.info("")
    logger.info("विस्मृति भी विद्या है — 'Forgetting too is knowledge'")
    logger.info("")

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=7777,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")

        # Stop all observers
        for observer in watched_projects.values():
            observer.stop()
            observer.join()

        logger.info("✅ Daemon stopped")

if __name__ == "__main__":
    main()
