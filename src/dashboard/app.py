"""
Nexus Agent_agent Agent Dashboard Flask App — src/dashboard/app.py
Web dashboard with API endpoints and WebSocket
"""

import os
import sys
import json
import time
import threading
import structlog
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.server import WSGIServer

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..core.event_loop import event_bus, Event, EventType
from ..core.config import load_config, get_config
from ..device import DeviceSystem
from ..memory import MemoryManager
from ..agent import Nexus Agent_agent AgentAgent, get_agent

logger = structlog.get_logger()


def create_app(config_path: str = None) -> Flask:
    app = Flask(__name__, static_folder="public", static_url_path="")
    CORS(app)

    config = load_config(config_path) if config_path else get_config()
    device = DeviceSystem()
    memory = MemoryManager()
    agent = get_agent()

    # WebSocket clients
    clients = []
    clients_lock = threading.Lock()

    def broadcast(data: dict):
        with clients_lock:
            dead = []
            for client in clients:
                try:
                    client.send(json.dumps(data))
                except Exception:
                    dead.append(client)
            for d in dead:
                clients.remove(d)

    # ---- API Routes ----

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "version": "0.1.0",
            "uptime": device.get_uptime_human(),
            "hostname": device.hostname,
        })

    @app.route("/api/system/stats")
    def system_stats():
        return jsonify(device.get_full_stats())

    @app.route("/api/system/stats/live")
    def system_stats_live():
        """SSE stream of live system stats."""
        def gen():
            while True:
                stats = device.get_full_stats()
                yield f"data: {json.dumps(stats)}\n\n"
                time.sleep(2)
        return Response(gen(), mimetype="text/event-stream")

    @app.route("/api/processes")
    def processes():
        from ..device import ProcessManager
        pm = ProcessManager()
        sort_by = request.args.get("sort", "cpu")
        limit = int(request.args.get("limit", 30))
        return jsonify(pm.list_processes(sort_by=sort_by, limit=limit))

    @app.route("/api/processes/<int:pid>")
    def process_detail(pid):
        from ..device import ProcessManager
        pm = ProcessManager()
        return jsonify(pm.get_process(pid) or {"error": "not found"})

    @app.route("/api/processes/<int:pid>/kill", methods=["POST"])
    def process_kill(pid):
        from ..device import ProcessManager
        pm = ProcessManager()
        return jsonify(pm.kill_process(pid))

    @app.route("/api/services")
    def services():
        from ..device import ServiceManager
        sm = ServiceManager()
        state = request.args.get("state", "all")
        return jsonify(sm.list_services(state=state))

    @app.route("/api/registry/startup")
    def startup_items():
        from ..device import RegistryManager
        rm = RegistryManager()
        return jsonify(rm.get_startup_items())

    @app.route("/api/memory/search", methods=["POST"])
    def memory_search():
        data = request.json or {}
        query = data.get("query", "")
        limit = data.get("limit", 5)
        if not query:
            return jsonify({"error": "query required"}), 400
        return jsonify(memory.recall(query=query, limit=limit))

    @app.route("/api/memory/add", methods=["POST"])
    def memory_add():
        data = request.json or {}
        content = data.get("content", "")
        if not content:
            return jsonify({"error": "content required"}), 400
        entry_id = memory.add(
            content=content,
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 1.0),
        )
        return jsonify({"success": True, "id": entry_id})

    @app.route("/api/memory/stats")
    def memory_stats():
        return jsonify(memory.get_stats())

    @app.route("/api/memory/graph")
    def memory_graph():
        return jsonify(memory.graph.get_graph_stats())

    @app.route("/api/sessions")
    def sessions():
        return jsonify({
            "sessions": list(agent._sessions.keys()),
            "active_count": len(agent._sessions),
        })

    @app.route("/api/sessions/<session_id>")
    def session_history(session_id):
        history = agent.get_session_history(session_id)
        return jsonify({"session_id": session_id, "messages": history})

    @app.route("/api/agent/message", methods=["POST"])
    def agent_message():
        data = request.json or {}
        session_id = data.get("session_id", "default")
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "message required"}), 400

        response = agent.send_message(session_id=session_id, user_message=message, stream=False)
        return jsonify({"session_id": session_id, "response": response})

    @app.route("/api/agent/stats")
    def agent_stats():
        return jsonify(agent.get_all_stats())

    @app.route("/api/tools/list")
    def tools_list():
        from ..tools import TOOL_REGISTRY
        return jsonify({
            "count": len(TOOL_REGISTRY),
            "tools": list(TOOL_REGISTRY.keys()),
        })

    @app.route("/api/tools/execute", methods=["POST"])
    def tools_execute():
        data = request.json or {}
        tool_name = data.get("tool", "")
        tool_args = data.get("args", {})
        if not tool_name:
            return jsonify({"error": "tool name required"}), 400
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result)

    # ---- Dashboard settings ----
    dash_cfg = config.dashboard or type("obj", (object,), {"port": 18790, "host": "127.0.0.1", "password": "Nexus Agent_agent Agent"})()
    port = dash_cfg.port if hasattr(dash_cfg, "port") else 18790

    logger.info("dashboard_created", port=port)
    return app


def run_dashboard(config_path: str = None, port: int = None):
    app = create_app(config_path)

    config = load_config(config_path) if config_path else get_config()
    dash_cfg = config.dashboard
    host = "127.0.0.1"
    port = port or (dash_cfg.port if dash_cfg and hasattr(dash_cfg, "port") else 18790)

    logger.info("starting_dashboard", host=host, port=port)
    server = pywsgi.WSGIServer((host, port), app, handler_class=WebSocketHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_dashboard()