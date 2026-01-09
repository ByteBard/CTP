"""
连接状态监测模块
满足评估表第5项：系统连接状态异常监测功能
- 能正常监测到启动、正常运行、断开、重连的连接状态
"""
import time
import threading
from enum import Enum
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime

from ..trade_logging.trade_logger import get_logger, TradeLogger
from ..core.ctp_gateway import CtpGateway


class ConnectionState(Enum):
    """
    连接状态枚举
    满足评估表要求：启动、正常运行、断开、重连
    """
    STARTING = "STARTING"           # 启动中
    CONNECTED = "CONNECTED"         # 已连接（正常运行）
    DISCONNECTED = "DISCONNECTED"   # 断开连接
    RECONNECTING = "RECONNECTING"   # 重连中
    AUTHENTICATED = "AUTHENTICATED" # 已认证
    LOGGED_IN = "LOGGED_IN"         # 已登录
    ERROR = "ERROR"                 # 错误


@dataclass
class ConnectionEvent:
    """连接事件"""
    state: ConnectionState
    timestamp: datetime
    message: str = ""
    error_code: int = 0


class ConnectionMonitor:
    """
    连接状态监测器
    满足评估表第5项要求：
    - 监测启动状态
    - 监测正常运行状态
    - 监测断开状态
    - 监测重连状态
    """

    def __init__(self, gateway: CtpGateway,
                 reconnect_interval: int = 5,
                 max_reconnect_attempts: int = 10,
                 heartbeat_interval: int = 30):
        """
        初始化连接监测器

        Args:
            gateway: CTP网关实例
            reconnect_interval: 重连间隔（秒）
            max_reconnect_attempts: 最大重连次数
            heartbeat_interval: 心跳检测间隔（秒）
        """
        self.gateway = gateway
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval

        self.logger: TradeLogger = get_logger()

        # 当前状态
        self._current_state: ConnectionState = ConnectionState.DISCONNECTED
        self._last_state_change: datetime = datetime.now()

        # 重连计数
        self._reconnect_count = 0
        self._auto_reconnect_enabled = True

        # 事件历史
        self._event_history: List[ConnectionEvent] = []
        self._max_history = 1000

        # 回调
        self._state_callbacks: List[Callable[[ConnectionState, ConnectionState], None]] = []

        # 线程控制
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # 注册网关回调
        self._register_gateway_callbacks()

    def _register_gateway_callbacks(self):
        """注册网关回调"""
        self.gateway.register_callback("on_connected", self._on_connected)
        self.gateway.register_callback("on_disconnected", self._on_disconnected)

    def _on_connected(self):
        """连接成功回调"""
        self._set_state(ConnectionState.CONNECTED, "连接成功")
        self._reconnect_count = 0

    def _on_disconnected(self, reason: int = 0):
        """连接断开回调"""
        reason_map = {
            0x1001: "网络读失败",
            0x1002: "网络写失败",
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文",
        }
        msg = reason_map.get(reason, f"未知原因({reason})")
        self._set_state(ConnectionState.DISCONNECTED, msg, reason)

        # 触发自动重连
        if self._auto_reconnect_enabled:
            self._trigger_reconnect()

    def _set_state(self, new_state: ConnectionState, message: str = "",
                   error_code: int = 0):
        """设置新状态"""
        with self._lock:
            old_state = self._current_state
            if old_state == new_state:
                return

            self._current_state = new_state
            self._last_state_change = datetime.now()

            # 记录事件
            event = ConnectionEvent(
                state=new_state,
                timestamp=self._last_state_change,
                message=message,
                error_code=error_code
            )
            self._event_history.append(event)

            # 限制历史记录数量
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

            # 记录日志
            self.logger.log_monitor("连接状态变化", {
                "old_state": old_state.value,
                "new_state": new_state.value,
                "message": message,
                "error_code": error_code
            })

            # 触发回调
            for callback in self._state_callbacks:
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    self.logger.log_exception(e, "state callback")

    def _trigger_reconnect(self):
        """触发重连"""
        if self._reconnect_count >= self.max_reconnect_attempts:
            self.logger.log_error("达到最大重连次数，停止重连",
                                  error_msg=f"已尝试{self._reconnect_count}次")
            self._set_state(ConnectionState.ERROR, "达到最大重连次数")
            return

        self._reconnect_count += 1
        self._set_state(ConnectionState.RECONNECTING,
                        f"第{self._reconnect_count}次重连")

        # 在新线程中执行重连
        threading.Thread(target=self._do_reconnect, daemon=True).start()

    def _do_reconnect(self):
        """执行重连"""
        self.logger.log_system("开始重连", {
            "attempt": self._reconnect_count,
            "max_attempts": self.max_reconnect_attempts
        })

        # 等待一段时间
        time.sleep(self.reconnect_interval)

        # 尝试连接
        try:
            if self.gateway.connect(timeout=30):
                if self.gateway.authenticate(timeout=10):
                    if self.gateway.login(timeout=10):
                        self._set_state(ConnectionState.LOGGED_IN, "重连成功并登录")
                        return
                    else:
                        self._set_state(ConnectionState.AUTHENTICATED, "重连成功，登录失败")
                else:
                    self._set_state(ConnectionState.CONNECTED, "重连成功，认证失败")
            else:
                self._set_state(ConnectionState.DISCONNECTED, "重连失败")
                # 继续尝试重连
                if self._auto_reconnect_enabled:
                    self._trigger_reconnect()
        except Exception as e:
            self.logger.log_exception(e, "reconnect")
            self._set_state(ConnectionState.ERROR, str(e))

    def start(self):
        """
        启动监测
        记录启动状态
        """
        self._set_state(ConnectionState.STARTING, "监测器启动")
        self._running = True

        # 启动监测线程
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        self.logger.log_system("连接监测器已启动", {
            "reconnect_interval": self.reconnect_interval,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "heartbeat_interval": self.heartbeat_interval
        })

    def stop(self):
        """停止监测"""
        self._running = False
        self._auto_reconnect_enabled = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        self.logger.log_system("连接监测器已停止")

    def _monitor_loop(self):
        """监测循环"""
        last_check = time.time()

        while self._running:
            try:
                current_time = time.time()

                # 定期检查连接状态
                if current_time - last_check >= self.heartbeat_interval:
                    self._check_connection_health()
                    last_check = current_time

                time.sleep(1)

            except Exception as e:
                self.logger.log_exception(e, "monitor loop")
                time.sleep(5)

    def _check_connection_health(self):
        """检查连接健康状态"""
        if not self.gateway.is_connected():
            if self._current_state not in [ConnectionState.DISCONNECTED,
                                           ConnectionState.RECONNECTING,
                                           ConnectionState.ERROR]:
                self._set_state(ConnectionState.DISCONNECTED, "心跳检测：连接已断开")
                if self._auto_reconnect_enabled:
                    self._trigger_reconnect()

    # ==================== 状态查询 ====================

    def get_current_state(self) -> ConnectionState:
        """获取当前状态"""
        return self._current_state

    def get_state_duration(self) -> float:
        """获取当前状态持续时间（秒）"""
        return (datetime.now() - self._last_state_change).total_seconds()

    def get_event_history(self, limit: int = 100) -> List[ConnectionEvent]:
        """获取事件历史"""
        return self._event_history[-limit:]

    def get_reconnect_count(self) -> int:
        """获取重连次数"""
        return self._reconnect_count

    def is_healthy(self) -> bool:
        """是否健康（已连接或已登录）"""
        return self._current_state in [
            ConnectionState.CONNECTED,
            ConnectionState.AUTHENTICATED,
            ConnectionState.LOGGED_IN
        ]

    # ==================== 配置 ====================

    def enable_auto_reconnect(self):
        """启用自动重连"""
        self._auto_reconnect_enabled = True
        self.logger.log_system("自动重连已启用")

    def disable_auto_reconnect(self):
        """禁用自动重连"""
        self._auto_reconnect_enabled = False
        self.logger.log_system("自动重连已禁用")

    def reset_reconnect_count(self):
        """重置重连计数"""
        self._reconnect_count = 0

    # ==================== 回调注册 ====================

    def register_state_callback(self, callback: Callable[[ConnectionState, ConnectionState], None]):
        """
        注册状态变化回调

        Args:
            callback: 回调函数，参数为(old_state, new_state)
        """
        self._state_callbacks.append(callback)

    def unregister_state_callback(self, callback: Callable):
        """注销回调"""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    # ==================== 状态报告 ====================

    def get_status_report(self) -> dict:
        """获取状态报告"""
        return {
            "current_state": self._current_state.value,
            "state_duration_seconds": self.get_state_duration(),
            "last_state_change": self._last_state_change.isoformat(),
            "reconnect_count": self._reconnect_count,
            "auto_reconnect_enabled": self._auto_reconnect_enabled,
            "is_healthy": self.is_healthy(),
            "gateway_connected": self.gateway.is_connected(),
            "gateway_logged_in": self.gateway.is_logged_in(),
            "recent_events_count": len(self._event_history)
        }
