# ABOUTME: HTTP health check server for watch mode monitoring
# ABOUTME: Provides /health and /metrics endpoints for container orchestration

"""Simple HTTP health check server for watch mode."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from ..utils.logger import get_logger
from .status import WatchStatus

log = get_logger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks."""

    # Class variable to store status file path
    status_file_path: Path | None = None

    def log_message(self, format, *args):
        """Override to use our logger instead of printing to stderr."""
        log.debug(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/metrics":
            self._handle_metrics()
        elif self.path == "/":
            self._handle_root()
        else:
            self._send_404()

    def _handle_root(self):
        """Handle root endpoint."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chronicon Watch Health Check</title>
            <style>
                body {
                    font-family: monospace;
                    padding: 20px;
                    background: #1e1e1e;
                    color: #d4d4d4;
                }
                h1 { color: #4ec9b0; }
                a { color: #569cd6; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .endpoint {
                    margin: 10px 0;
                    padding: 10px;
                    background: #252526;
                    border-left: 3px solid #4ec9b0;
                }
            </style>
        </head>
        <body>
            <h1>Chronicon Watch Health Check</h1>
            <p>Available endpoints:</p>
            <div class="endpoint">
                <strong>GET /health</strong> - Health status (JSON)
            </div>
            <div class="endpoint">
                <strong>GET /metrics</strong> - Detailed metrics (JSON)
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _handle_health(self):
        """Handle /health endpoint."""
        # Load status from file
        status = self._load_status()

        if status is None:
            # No status file means daemon hasn't run yet
            response = {
                "status": "initializing",
                "healthy": False,
                "message": "No status file found - daemon may not have started yet",
            }
            self._send_json_response(503, response)
            return

        # Check if daemon is running and healthy
        is_healthy = (
            status.is_running
            and status.consecutive_errors < 3  # Allow up to 2 consecutive errors
        )

        response = {
            "status": "healthy" if is_healthy else "unhealthy",
            "healthy": is_healthy,
            "running": status.is_running,
            "pid": status.pid,
            "consecutive_errors": status.consecutive_errors,
            "last_check": status.last_check,
            "next_check": status.next_check,
        }

        status_code = 200 if is_healthy else 503
        self._send_json_response(status_code, response)

    def _handle_metrics(self):
        """Handle /metrics endpoint."""
        status = self._load_status()

        if status is None:
            response = {
                "error": "No status file found",
            }
            self._send_json_response(503, response)
            return

        # Build detailed metrics response
        response = {
            "status": {
                "running": status.is_running,
                "pid": status.pid,
                "started_at": status.started_at,
                "uptime_seconds": status.uptime_seconds,
                "uptime_hours": round(status.uptime_seconds / 3600, 2),
            },
            "cycles": {
                "total": status.total_cycles,
                "successful": status.successful_cycles,
                "failed": status.failed_cycles,
                "consecutive_errors": status.consecutive_errors,
                "success_rate": round(
                    status.successful_cycles / status.total_cycles * 100, 2
                )
                if status.total_cycles > 0
                else 0,
            },
            "updates": {
                "total_new_posts": status.total_new_posts,
                "total_modified_posts": status.total_modified_posts,
                "total_affected_topics": status.total_affected_topics,
            },
            "timing": {
                "last_check": status.last_check,
                "next_check": status.next_check,
            },
            "recent_cycles": [
                {
                    "timestamp": cycle.timestamp,
                    "success": cycle.success,
                    "new_posts": cycle.new_posts,
                    "modified_posts": cycle.modified_posts,
                    "affected_topics": cycle.affected_topics,
                    "duration_seconds": cycle.duration_seconds,
                    "error_message": cycle.error_message,
                }
                for cycle in (status.recent_cycles or [])[-10:]  # Last 10 cycles
            ],
        }

        if status.last_error:
            response["last_error"] = status.last_error

        self._send_json_response(200, response)

    def _load_status(self) -> WatchStatus | None:
        """Load status from file."""
        if self.status_file_path is None:
            return None

        try:
            return WatchStatus.load(self.status_file_path)
        except Exception as e:
            log.error(f"Error loading status file: {e}")
            return None

    def _send_json_response(self, status_code: int, data: dict):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response_body = json.dumps(data, indent=2)
        self.wfile.write(response_body.encode())

    def _send_404(self):
        """Send 404 response."""
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "error": "Not found",
            "message": "Available endpoints: /health, /metrics",
        }
        self.wfile.write(json.dumps(response).encode())


class HealthCheckServer:
    """HTTP server for health checks."""

    def __init__(self, port: int, status_file: Path):
        """
        Initialize health check server.

        Args:
            port: Port to listen on
            status_file: Path to status JSON file
        """
        self.port = port
        self.status_file = status_file
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None

        # Set class variable for handler
        HealthCheckHandler.status_file_path = status_file

    def start(self):
        """Start the health check server in a background thread."""
        try:
            self.server = HTTPServer(("0.0.0.0", self.port), HealthCheckHandler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            log.info(f"Health check server started on port {self.port}")
        except Exception as e:
            log.error(f"Failed to start health check server: {e}")
            raise

    def stop(self):
        """Stop the health check server."""
        if self.server:
            log.info("Stopping health check server...")
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=5)
            log.info("Health check server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.thread is not None and self.thread.is_alive()
