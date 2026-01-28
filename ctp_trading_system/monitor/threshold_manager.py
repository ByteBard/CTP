"""
阈值管理与预警模块
满足评估表要求：
- 第11项：重复报单笔数阈值设置及预警功能（建议）
- 第12项：报单总笔数阈值设置及预警功能（严重）
- 第13项：撤单总笔数阈值设置及预警功能（严重）
"""
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading

from ..config.settings import ThresholdConfig
from ..trade_logging.trade_logger import get_logger, TradeLogger
from .order_monitor import OrderMonitor


class ThresholdType(Enum):
    """阈值类型"""
    REPEAT_OPEN = "repeat_open"         # 重复开仓
    REPEAT_CLOSE = "repeat_close"       # 重复平仓
    REPEAT_CANCEL = "repeat_cancel"     # 重复撤单
    TOTAL_ORDER = "total_order"         # 报单总数
    TOTAL_CANCEL = "total_cancel"       # 撤单总数


class AlertLevel(Enum):
    """预警级别"""
    INFO = "INFO"           # 提示
    WARNING = "WARNING"     # 警告
    CRITICAL = "CRITICAL"   # 严重


@dataclass
class ThresholdAlert:
    """阈值预警"""
    threshold_type: ThresholdType
    alert_level: AlertLevel
    current_value: int
    threshold_value: int
    instrument_id: Optional[str]
    message: str
    timestamp: datetime


class ThresholdManager:
    """
    阈值管理器
    满足评估表第11-13项要求：
    - 提供阈值设置功能
    - 达到阈值时触发预警
    """

    def __init__(self, config: ThresholdConfig, order_monitor: OrderMonitor):
        """
        初始化阈值管理器

        Args:
            config: 阈值配置
            order_monitor: 报单监测器
        """
        self.config = config
        self.order_monitor = order_monitor
        self.logger: TradeLogger = get_logger()

        # 预警回调
        self._alert_callbacks: List[Callable[[ThresholdAlert], None]] = []

        # 预警历史
        self._alert_history: List[ThresholdAlert] = []
        self._max_history = 1000

        # 已触发的阈值（避免重复预警）
        self._triggered_alerts: Dict[str, datetime] = {}
        self._alert_cooldown = 60  # 同一预警的冷却时间（秒）

        # 锁
        self._lock = threading.Lock()

        # 注册到报单监测器
        self.order_monitor.register_order_callback(self._on_order_event)

        self.logger.log_system("阈值管理器初始化完成", {
            "repeat_open_threshold": config.repeat_open_threshold,
            "repeat_close_threshold": config.repeat_close_threshold,
            "repeat_cancel_threshold": config.repeat_cancel_threshold,
            "total_order_threshold": config.total_order_threshold,
            "total_cancel_threshold": config.total_cancel_threshold
        })

    def _on_order_event(self, action: str, instrument_id: str, stats: dict):
        """报单事件处理"""
        if action == "open":
            self._check_repeat_open(instrument_id)
            self._check_total_order()
        elif action == "close":
            self._check_repeat_close(instrument_id)
            self._check_total_order()
        elif action == "cancel":
            self._check_repeat_cancel(instrument_id)
            self._check_total_cancel()

    # ==================== 阈值设置（评估表第11-13项） ====================

    def set_repeat_open_threshold(self, threshold: int):
        """
        设置重复开仓阈值
        满足评估表第11项：提供重复报单笔数的阈值设置功能
        """
        old_value = self.config.repeat_open_threshold
        self.config.repeat_open_threshold = threshold
        self.logger.log_system("阈值设置变更", {
            "type": "repeat_open",
            "old_value": old_value,
            "new_value": threshold
        })

    def set_repeat_close_threshold(self, threshold: int):
        """设置重复平仓阈值"""
        old_value = self.config.repeat_close_threshold
        self.config.repeat_close_threshold = threshold
        self.logger.log_system("阈值设置变更", {
            "type": "repeat_close",
            "old_value": old_value,
            "new_value": threshold
        })

    def set_repeat_cancel_threshold(self, threshold: int):
        """设置重复撤单阈值"""
        old_value = self.config.repeat_cancel_threshold
        self.config.repeat_cancel_threshold = threshold
        self.logger.log_system("阈值设置变更", {
            "type": "repeat_cancel",
            "old_value": old_value,
            "new_value": threshold
        })

    def set_total_order_threshold(self, threshold: int):
        """
        设置报单总笔数阈值
        满足评估表第12项：提供报单总笔数的阈值设置功能
        """
        old_value = self.config.total_order_threshold
        self.config.total_order_threshold = threshold
        self.logger.log_system("阈值设置变更", {
            "type": "total_order",
            "old_value": old_value,
            "new_value": threshold
        })

    def set_total_cancel_threshold(self, threshold: int):
        """
        设置撤单总笔数阈值
        满足评估表第13项：提供撤单总笔数的阈值设置功能
        """
        old_value = self.config.total_cancel_threshold
        self.config.total_cancel_threshold = threshold
        self.logger.log_system("阈值设置变更", {
            "type": "total_cancel",
            "old_value": old_value,
            "new_value": threshold
        })

    def update_thresholds(self, config):
        """
        批量更新阈值配置
        """
        if hasattr(config, 'repeat_open_threshold') and config.repeat_open_threshold is not None:
            self.set_repeat_open_threshold(config.repeat_open_threshold)
        if hasattr(config, 'repeat_close_threshold') and config.repeat_close_threshold is not None:
            self.set_repeat_close_threshold(config.repeat_close_threshold)
        if hasattr(config, 'repeat_cancel_threshold') and config.repeat_cancel_threshold is not None:
            self.set_repeat_cancel_threshold(config.repeat_cancel_threshold)
        if hasattr(config, 'total_order_threshold') and config.total_order_threshold is not None:
            self.set_total_order_threshold(config.total_order_threshold)
        if hasattr(config, 'total_cancel_threshold') and config.total_cancel_threshold is not None:
            self.set_total_cancel_threshold(config.total_cancel_threshold)

    # ==================== 阈值检查 ====================

    def _check_repeat_open(self, instrument_id: str):
        """
        检查重复开仓
        满足评估表第11项：重复开仓单报单笔数预警
        """
        current = self.order_monitor.get_instrument_open_count(instrument_id)
        threshold = self.config.repeat_open_threshold

        self.logger.log_threshold_check(
            check_type="repeat_open",
            current_value=current,
            threshold=threshold,
            triggered=(current >= threshold),
            instrument_id=instrument_id
        )

        if current >= threshold:
            self._trigger_alert(
                threshold_type=ThresholdType.REPEAT_OPEN,
                alert_level=AlertLevel.WARNING,
                current_value=current,
                threshold_value=threshold,
                instrument_id=instrument_id,
                message=f"合约{instrument_id}重复开仓次数({current})达到阈值({threshold})"
            )

    def _check_repeat_close(self, instrument_id: str):
        """
        检查重复平仓
        满足评估表第11项：重复平仓单报单笔数预警
        """
        current = self.order_monitor.get_instrument_close_count(instrument_id)
        threshold = self.config.repeat_close_threshold

        self.logger.log_threshold_check(
            check_type="repeat_close",
            current_value=current,
            threshold=threshold,
            triggered=(current >= threshold),
            instrument_id=instrument_id
        )

        if current >= threshold:
            self._trigger_alert(
                threshold_type=ThresholdType.REPEAT_CLOSE,
                alert_level=AlertLevel.WARNING,
                current_value=current,
                threshold_value=threshold,
                instrument_id=instrument_id,
                message=f"合约{instrument_id}重复平仓次数({current})达到阈值({threshold})"
            )

    def _check_repeat_cancel(self, instrument_id: str):
        """
        检查重复撤单
        满足评估表第11项：重复撤单报单笔数预警
        """
        current = self.order_monitor.get_instrument_cancel_count(instrument_id)
        threshold = self.config.repeat_cancel_threshold

        self.logger.log_threshold_check(
            check_type="repeat_cancel",
            current_value=current,
            threshold=threshold,
            triggered=(current >= threshold),
            instrument_id=instrument_id
        )

        if current >= threshold:
            self._trigger_alert(
                threshold_type=ThresholdType.REPEAT_CANCEL,
                alert_level=AlertLevel.WARNING,
                current_value=current,
                threshold_value=threshold,
                instrument_id=instrument_id,
                message=f"合约{instrument_id}重复撤单次数({current})达到阈值({threshold})"
            )

    def _check_total_order(self):
        """
        检查报单总笔数
        满足评估表第12项：报单总笔数预警
        """
        current = self.order_monitor.get_total_order_count()
        threshold = self.config.total_order_threshold

        self.logger.log_threshold_check(
            check_type="total_order",
            current_value=current,
            threshold=threshold,
            triggered=(current >= threshold)
        )

        if current >= threshold:
            self._trigger_alert(
                threshold_type=ThresholdType.TOTAL_ORDER,
                alert_level=AlertLevel.CRITICAL,  # 严重级别
                current_value=current,
                threshold_value=threshold,
                instrument_id=None,
                message=f"报单总笔数({current})达到阈值({threshold})"
            )

    def _check_total_cancel(self):
        """
        检查撤单总笔数
        满足评估表第13项：撤单总笔数预警
        """
        current = self.order_monitor.get_total_cancel_count()
        threshold = self.config.total_cancel_threshold

        self.logger.log_threshold_check(
            check_type="total_cancel",
            current_value=current,
            threshold=threshold,
            triggered=(current >= threshold)
        )

        if current >= threshold:
            self._trigger_alert(
                threshold_type=ThresholdType.TOTAL_CANCEL,
                alert_level=AlertLevel.CRITICAL,  # 严重级别
                current_value=current,
                threshold_value=threshold,
                instrument_id=None,
                message=f"任意撤单总笔数({current})达到阈值({threshold})"
            )

    # ==================== 预警触发 ====================

    def _trigger_alert(self, threshold_type: ThresholdType, alert_level: AlertLevel,
                       current_value: int, threshold_value: int,
                       instrument_id: Optional[str], message: str):
        """触发预警"""
        with self._lock:
            # 检查冷却时间
            alert_key = f"{threshold_type.value}_{instrument_id or 'account'}"
            now = datetime.now()

            if alert_key in self._triggered_alerts:
                last_trigger = self._triggered_alerts[alert_key]
                if (now - last_trigger).total_seconds() < self._alert_cooldown:
                    return  # 冷却中，不重复预警

            # 创建预警
            alert = ThresholdAlert(
                threshold_type=threshold_type,
                alert_level=alert_level,
                current_value=current_value,
                threshold_value=threshold_value,
                instrument_id=instrument_id,
                message=message,
                timestamp=now
            )

            # 记录预警
            self._alert_history.append(alert)
            if len(self._alert_history) > self._max_history:
                self._alert_history = self._alert_history[-self._max_history:]

            self._triggered_alerts[alert_key] = now

            # 记录日志
            self.logger.log_alert(
                alert_type=threshold_type.value,
                message=message,
                level=alert_level.value.lower(),
                current_value=current_value,
                threshold_value=threshold_value,
                instrument_id=instrument_id
            )

            # 触发回调
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.log_exception(e, "alert callback")

    # ==================== 手动检查 ====================

    def check_all_thresholds(self) -> List[ThresholdAlert]:
        """手动检查所有阈值"""
        alerts = []

        # 检查报单总数
        total_order = self.order_monitor.get_total_order_count()
        if total_order >= self.config.total_order_threshold:
            alerts.append(ThresholdAlert(
                threshold_type=ThresholdType.TOTAL_ORDER,
                alert_level=AlertLevel.CRITICAL,
                current_value=total_order,
                threshold_value=self.config.total_order_threshold,
                instrument_id=None,
                message=f"报单总笔数({total_order})达到阈值",
                timestamp=datetime.now()
            ))

        # 检查撤单总数
        total_cancel = self.order_monitor.get_total_cancel_count()
        if total_cancel >= self.config.total_cancel_threshold:
            alerts.append(ThresholdAlert(
                threshold_type=ThresholdType.TOTAL_CANCEL,
                alert_level=AlertLevel.CRITICAL,
                current_value=total_cancel,
                threshold_value=self.config.total_cancel_threshold,
                instrument_id=None,
                message=f"任意撤单总笔数({total_cancel})达到阈值",
                timestamp=datetime.now()
            ))

        # 检查各合约
        for instrument_id, stats in self.order_monitor.get_all_instrument_stats().items():
            if stats.open_count >= self.config.repeat_open_threshold:
                alerts.append(ThresholdAlert(
                    threshold_type=ThresholdType.REPEAT_OPEN,
                    alert_level=AlertLevel.WARNING,
                    current_value=stats.open_count,
                    threshold_value=self.config.repeat_open_threshold,
                    instrument_id=instrument_id,
                    message=f"合约{instrument_id}重复开仓次数达到阈值",
                    timestamp=datetime.now()
                ))

            if stats.close_count >= self.config.repeat_close_threshold:
                alerts.append(ThresholdAlert(
                    threshold_type=ThresholdType.REPEAT_CLOSE,
                    alert_level=AlertLevel.WARNING,
                    current_value=stats.close_count,
                    threshold_value=self.config.repeat_close_threshold,
                    instrument_id=instrument_id,
                    message=f"合约{instrument_id}重复平仓次数达到阈值",
                    timestamp=datetime.now()
                ))

            if stats.cancel_count >= self.config.repeat_cancel_threshold:
                alerts.append(ThresholdAlert(
                    threshold_type=ThresholdType.REPEAT_CANCEL,
                    alert_level=AlertLevel.WARNING,
                    current_value=stats.cancel_count,
                    threshold_value=self.config.repeat_cancel_threshold,
                    instrument_id=instrument_id,
                    message=f"合约{instrument_id}重复撤单次数达到阈值",
                    timestamp=datetime.now()
                ))

        return alerts

    # ==================== 查询 ====================

    def get_alert_history(self, limit: int = 100) -> List[ThresholdAlert]:
        """获取预警历史"""
        return self._alert_history[-limit:]

    def get_current_thresholds(self) -> dict:
        """获取当前阈值设置"""
        return {
            "repeat_open_threshold": self.config.repeat_open_threshold,
            "repeat_close_threshold": self.config.repeat_close_threshold,
            "repeat_cancel_threshold": self.config.repeat_cancel_threshold,
            "total_order_threshold": self.config.total_order_threshold,
            "total_cancel_threshold": self.config.total_cancel_threshold
        }

    def get_threshold_status(self) -> dict:
        """获取阈值状态报告"""
        stats = self.order_monitor.get_statistics()
        return {
            "thresholds": self.get_current_thresholds(),
            "current_values": {
                "total_order_count": stats.total_order_count,
                "total_cancel_count": stats.total_cancel_count,
            },
            "utilization": {
                "order_utilization": f"{stats.total_order_count / self.config.total_order_threshold * 100:.1f}%"
                    if self.config.total_order_threshold > 0 else "N/A",
                "cancel_utilization": f"{stats.total_cancel_count / self.config.total_cancel_threshold * 100:.1f}%"
                    if self.config.total_cancel_threshold > 0 else "N/A"
            },
            "alert_count": len(self._alert_history)
        }

    # ==================== 回调注册 ====================

    def register_alert_callback(self, callback: Callable[[ThresholdAlert], None]):
        """
        注册预警回调
        回调将在达到阈值时被调用
        """
        self._alert_callbacks.append(callback)

    def unregister_alert_callback(self, callback: Callable):
        """注销预警回调"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    def set_alert_cooldown(self, seconds: int):
        """设置预警冷却时间"""
        self._alert_cooldown = seconds

    def clear_triggered_alerts(self):
        """清除已触发的预警记录（重置冷却）"""
        with self._lock:
            self._triggered_alerts.clear()
