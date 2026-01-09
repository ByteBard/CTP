"""
WebSocket 实时推送模块
用于推送日志、预警、状态更新
"""
import asyncio
import json
from typing import Set
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        if not self.active_connections:
            return

        message_json = json.dumps(message, ensure_ascii=False, default=str)
        disconnected = set()

        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)

        # 清理断开的连接
        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected

    async def send_log(self, log_type: str, level: str, message: str, data: dict = None):
        """发送日志消息"""
        await self.broadcast({
            "type": "log",
            "log_type": log_type,
            "level": level,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })

    async def send_alert(self, level: str, title: str, message: str):
        """发送预警消息"""
        await self.broadcast({
            "type": "alert",
            "level": level,
            "title": title,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    async def send_status(self, status_type: str, data: dict):
        """发送状态更新"""
        await self.broadcast({
            "type": "status",
            "status_type": status_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    async def send_order_update(self, order: dict):
        """发送订单更新"""
        await self.broadcast({
            "type": "order",
            "order": order,
            "timestamp": datetime.now().isoformat()
        })


# 全局连接管理器
manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """获取WebSocket管理器"""
    return manager


def setup_websocket(app: FastAPI):
    """设置WebSocket路由"""

    @app.websocket("/ws/realtime")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket实时推送端点"""
        await manager.connect(websocket)
        try:
            # 发送连接成功消息
            await websocket.send_json({
                "type": "connected",
                "message": "WebSocket连接成功",
                "timestamp": datetime.now().isoformat()
            })

            # 保持连接，接收客户端消息
            while True:
                try:
                    data = await websocket.receive_text()
                    # 处理客户端消息（心跳等）
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                except WebSocketDisconnect:
                    break
                except Exception:
                    break
        finally:
            await manager.disconnect(websocket)
