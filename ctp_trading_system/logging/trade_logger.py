"""
交易日志系统
满足评估表第25项：日志记录功能
- 交易日志：报单、成交、撤单
- 系统运行记录：连接、登录、心跳
- 监测记录：阈值检查、预警
- 错误提示信息
"""
import os
import json
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum
from loguru import logger
import sys


class LogType(Enum):
    """日志类型"""
    TRADE = "trade"         # 交易日志
    SYSTEM = "system"       # 系统日志
    MONITOR = "monitor"     # 监测日志
    ERROR = "error"         # 错误日志


class TradeLogger:
    """
    交易日志记录器
    满足评估表第25项要求：
    1. 提供日志记录功能
    2. 日志信息包括：交易日志、系统运行记录、监测记录、错误提示信息
    """

    def __init__(self, log_dir: str = "./logs", rotation: str = "1 day", retention: str = "30 days"):
        """
        初始化日志系统

        Args:
            log_dir: 日志目录
            rotation: 日志轮转周期
            retention: 日志保留时间
        """
        self.log_dir = log_dir
        self.rotation = rotation
        self.retention = retention

        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)

        # 配置loguru
        self._setup_loggers()

        # 记录启动日志
        self.log_system("日志系统初始化完成", {"log_dir": log_dir})

    def _setup_loggers(self):
        """配置各类日志文件"""
        # 移除默认处理器
        logger.remove()

        # 控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
            level="INFO"
        )

        # 交易日志
        logger.add(
            os.path.join(self.log_dir, "trade_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            filter=lambda record: record["extra"].get("log_type") == LogType.TRADE.value,
            rotation=self.rotation,
            retention=self.retention,
            encoding="utf-8"
        )

        # 系统日志
        logger.add(
            os.path.join(self.log_dir, "system_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            filter=lambda record: record["extra"].get("log_type") == LogType.SYSTEM.value,
            rotation=self.rotation,
            retention=self.retention,
            encoding="utf-8"
        )

        # 监测日志
        logger.add(
            os.path.join(self.log_dir, "monitor_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            filter=lambda record: record["extra"].get("log_type") == LogType.MONITOR.value,
            rotation=self.rotation,
            retention=self.retention,
            encoding="utf-8"
        )

        # 错误日志
        logger.add(
            os.path.join(self.log_dir, "error_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            filter=lambda record: record["extra"].get("log_type") == LogType.ERROR.value,
            rotation=self.rotation,
            retention=self.retention,
            encoding="utf-8"
        )

        # 全量日志（所有类型）
        logger.add(
            os.path.join(self.log_dir, "all_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | [{extra[log_type]}] {message}",
            rotation=self.rotation,
            retention=self.retention,
            encoding="utf-8"
        )

    def _format_message(self, message: str, data: Optional[Dict[str, Any]] = None) -> str:
        """格式化日志消息"""
        if data:
            return f"{message} | {json.dumps(data, ensure_ascii=False)}"
        return message

    # ==================== 交易日志 ====================

    def log_order_insert(self, instrument_id: str, direction: str, offset: str,
                         price: float, volume: int, order_ref: str, **kwargs):
        """记录报单"""
        data = {
            "action": "ORDER_INSERT",
            "instrument_id": instrument_id,
            "direction": direction,
            "offset": offset,
            "price": price,
            "volume": volume,
            "order_ref": order_ref,
            **kwargs
        }
        logger.bind(log_type=LogType.TRADE.value).info(
            self._format_message("报单", data)
        )

    def log_order_cancel(self, instrument_id: str, order_ref: str,
                         order_sys_id: str = "", **kwargs):
        """记录撤单"""
        data = {
            "action": "ORDER_CANCEL",
            "instrument_id": instrument_id,
            "order_ref": order_ref,
            "order_sys_id": order_sys_id,
            **kwargs
        }
        logger.bind(log_type=LogType.TRADE.value).info(
            self._format_message("撤单", data)
        )

    def log_trade(self, instrument_id: str, direction: str, offset: str,
                  price: float, volume: int, trade_id: str, **kwargs):
        """记录成交"""
        data = {
            "action": "TRADE",
            "instrument_id": instrument_id,
            "direction": direction,
            "offset": offset,
            "price": price,
            "volume": volume,
            "trade_id": trade_id,
            **kwargs
        }
        logger.bind(log_type=LogType.TRADE.value).info(
            self._format_message("成交", data)
        )

    def log_order_status(self, order_ref: str, status: str, status_msg: str = "", **kwargs):
        """记录订单状态变化"""
        data = {
            "action": "ORDER_STATUS",
            "order_ref": order_ref,
            "status": status,
            "status_msg": status_msg,
            **kwargs
        }
        logger.bind(log_type=LogType.TRADE.value).info(
            self._format_message("订单状态", data)
        )

    # ==================== 系统日志 ====================

    def log_system(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录系统运行信息"""
        logger.bind(log_type=LogType.SYSTEM.value).info(
            self._format_message(message, data)
        )

    def log_connection(self, state: str, front_addr: str = "", **kwargs):
        """记录连接状态"""
        data = {
            "action": "CONNECTION",
            "state": state,
            "front_addr": front_addr,
            **kwargs
        }
        logger.bind(log_type=LogType.SYSTEM.value).info(
            self._format_message("连接状态", data)
        )

    def log_login(self, investor_id: str, success: bool, error_msg: str = "", **kwargs):
        """记录登录信息"""
        data = {
            "action": "LOGIN",
            "investor_id": investor_id,
            "success": success,
            "error_msg": error_msg,
            **kwargs
        }
        level = "info" if success else "warning"
        getattr(logger.bind(log_type=LogType.SYSTEM.value), level)(
            self._format_message("用户登录", data)
        )

    def log_authenticate(self, success: bool, error_msg: str = "", **kwargs):
        """记录认证信息"""
        data = {
            "action": "AUTHENTICATE",
            "success": success,
            "error_msg": error_msg,
            **kwargs
        }
        level = "info" if success else "warning"
        getattr(logger.bind(log_type=LogType.SYSTEM.value), level)(
            self._format_message("客户端认证", data)
        )

    def log_heartbeat(self, time_lapse: int, **kwargs):
        """记录心跳"""
        data = {
            "action": "HEARTBEAT",
            "time_lapse": time_lapse,
            **kwargs
        }
        logger.bind(log_type=LogType.SYSTEM.value).debug(
            self._format_message("心跳", data)
        )

    # ==================== 监测日志 ====================

    def log_monitor(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录监测信息"""
        logger.bind(log_type=LogType.MONITOR.value).info(
            self._format_message(message, data)
        )

    def log_threshold_check(self, check_type: str, current_value: int,
                            threshold: int, triggered: bool, **kwargs):
        """记录阈值检查"""
        data = {
            "action": "THRESHOLD_CHECK",
            "check_type": check_type,
            "current_value": current_value,
            "threshold": threshold,
            "triggered": triggered,
            **kwargs
        }
        level = "warning" if triggered else "info"
        getattr(logger.bind(log_type=LogType.MONITOR.value), level)(
            self._format_message("阈值检查", data)
        )

    def log_alert(self, alert_type: str, message: str, level: str = "warning", **kwargs):
        """记录预警"""
        data = {
            "action": "ALERT",
            "alert_type": alert_type,
            "message": message,
            **kwargs
        }
        getattr(logger.bind(log_type=LogType.MONITOR.value), level)(
            self._format_message("预警触发", data)
        )

    def log_order_statistics(self, stats: Dict[str, Any]):
        """记录报单统计"""
        data = {
            "action": "ORDER_STATISTICS",
            **stats
        }
        logger.bind(log_type=LogType.MONITOR.value).info(
            self._format_message("报单统计", data)
        )

    # ==================== 错误日志 ====================

    def log_error(self, message: str, error_code: int = 0,
                  error_msg: str = "", **kwargs):
        """记录错误信息"""
        data = {
            "action": "ERROR",
            "error_code": error_code,
            "error_msg": error_msg,
            **kwargs
        }
        logger.bind(log_type=LogType.ERROR.value).error(
            self._format_message(message, data)
        )

    def log_validation_error(self, validation_type: str, message: str, **kwargs):
        """记录验证错误"""
        data = {
            "action": "VALIDATION_ERROR",
            "validation_type": validation_type,
            "message": message,
            **kwargs
        }
        logger.bind(log_type=LogType.ERROR.value).error(
            self._format_message("指令验证失败", data)
        )

    def log_exception(self, exception: Exception, context: str = ""):
        """记录异常"""
        data = {
            "action": "EXCEPTION",
            "exception_type": type(exception).__name__,
            "exception_msg": str(exception),
            "context": context
        }
        logger.bind(log_type=LogType.ERROR.value).exception(
            self._format_message("异常", data)
        )


# 全局日志实例
_logger_instance: Optional[TradeLogger] = None


def get_logger() -> TradeLogger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TradeLogger()
    return _logger_instance


def init_logger(log_dir: str = "./logs", rotation: str = "1 day",
                retention: str = "30 days") -> TradeLogger:
    """初始化全局日志实例"""
    global _logger_instance
    _logger_instance = TradeLogger(log_dir, rotation, retention)
    return _logger_instance
