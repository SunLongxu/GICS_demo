#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GICS Demo API 入口：HTTP API + Socket.IO，供前端 (Vite :5173) 调用。
"""

import logging
import os
import traceback

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "*"]}},
    supports_credentials=True,
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)


@app.route("/")
def index():
    return "GICS API Server is running"


@app.route("/test", methods=["GET"])
def test():
    return jsonify({"status": "success", "message": "Test endpoint working"})


@socketio.on("connect")
def on_connect():
    logger.info("WebSocket client connected")
    emit("connection_response", {"data": "Connected"})


@socketio.on("disconnect")
def on_disconnect():
    logger.info("WebSocket client disconnected")


try:
    from src.api_routes import register_routes

    register_routes(app, socketio)

    with app.app_context():
        from src.api_routes import initialize_icsgnn

        if initialize_icsgnn():
            logger.info("ICSGNN initialized at startup")
        else:
            logger.warning("ICSGNN startup initialization failed; will retry on first API call")

    logger.info("Registered all API routes")

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5001))
        host = os.environ.get("HOST", "0.0.0.0")
        debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
        logger.info("Starting GICS API server on %s:%s (debug=%s)", host, port, debug)
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True,
        )
except Exception as e:
    logger.error("Failed to start server: %s", e)
    logger.error(traceback.format_exc())
    raise
