#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 首先导入并执行eventlet的monkey_patch，确保在导入其他模块前完成
import eventlet
eventlet.monkey_patch()

# 然后导入其他模块
import logging
import traceback
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import networkx as nx
import random
from collections import deque

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 配置SocketIO
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='eventlet',
                   logger=True, 
                   engineio_logger=True)

# 全局变量
icsgnn_instance = None

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('message')
def handle_message(message):
    logger.info(f'Received message: {message}')
    emit('response', {'data': f'Received: {message}'})

@socketio.on_error()
def handle_error(e):
    logger.error(f'SocketIO error: {str(e)}')
    logger.error(traceback.format_exc())

def handle_state_update(state):
    """
    处理状态更新
    """
    try:
        if state and isinstance(state, dict):
            socketio.emit('state_update', state)
    except Exception as e:
        logger.error(f"Error in handle_state_update: {str(e)}")
        logger.error(traceback.format_exc())

# 主入口点
if __name__ == '__main__':
    # 设置端口和主机
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting API server on {host}:{port}")
    
    # 使用socketio.run()而不是app.run()，以确保WebSocket功能正常工作
    socketio.run(app, host=host, port=port, debug=True) 