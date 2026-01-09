"""
应急处置模块
满足评估表要求：
- 第20项：暂停交易功能（严重）
  - 限制账号权限
  - 停止策略执行
  - 强制退出账号
- 第23项：部分撤单功能（建议）
- 第24项：全部撤单功能（建议）
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import time

from ..core.ctp_gateway import CtpGateway
from ..logging.trade_logger import get_logger, TradeLogger
from ..alert.alert_service import AlertService, AlertLevel


class EmergencyAction(Enum):
    """应急操作类型"""
    PAUSE_TRADING = "PAUSE_TRADING"       # 暂停交易
    STOP_STRATEGY = "STOP_STRATEGY"       # 停止策略
    CANCEL_ORDERS = "CANCEL_ORDERS"       # 撤单
    FORCE_LOGOUT = "FORCE_LOGOUT"         # 强制退出
    RESUME_TRADING = "RESUME_TRADING"     # 恢复交易


@dataclass
class EmergencyEvent:
    """应急事件"""
    action: EmergencyAction
    timestamp: datetime
    reason: str
    success: bool
    details: dict = None


class EmergencyHandler:
    """
    应急处置器
    满足评估表第20、23-24项要求
    """

    def __init__(self, gateway: CtpGateway, alert_service: Optional[AlertService] = None):
        """
        初始化应急处置器

        Args:
            gateway: CTP网关
            alert_service: 预警服务（可选）
        """
        self.gateway = gateway
        self.alert_service = alert_service
        self.logger: TradeLogger = get_logger()

        # 状态
        self._trading_paused = False
        self._strategy_stopped = False

        # 策略管理
        self._strategies: Dict[str, Callable] = {}
        self._strategy_status: Dict[str, bool] = {}

        # 待撤订单缓存
        self._pending_orders: Dict[str, dict] = {}

        # 事件历史
        self._event_history: List[EmergencyEvent] = []

        # 锁
        self._lock = threading.Lock()

        self.logger.log_system("应急处置器初始化完成")

    # ==================== 第20项：暂停交易功能 ====================

    def pause_trading(self, reason: str = "手动暂停") -> bool:
        """
        暂停交易
        满足评估表第20项：通过限制账号权限暂停交易

        Args:
            reason: 暂停原因

        Returns:
            是否成功
        """
        with self._lock:
            if self._trading_paused:
                self.logger.log_system("交易已处于暂停状态")
                return True

            try:
                # 禁用网关交易功能
                self.gateway.disable_trading()
                self._trading_paused = True

                # 记录事件
                self._record_event(
                    action=EmergencyAction.PAUSE_TRADING,
                    reason=reason,
                    success=True
                )

                self.logger.log_system("交易已暂停", {"reason": reason})

                # 发送预警
                if self.alert_service:
                    self.alert_service.warning(
                        "交易暂停",
                        f"交易已暂停，原因：{reason}",
                        source="EmergencyHandler"
                    )

                return True

            except Exception as e:
                self.logger.log_exception(e, "pause trading")
                self._record_event(
                    action=EmergencyAction.PAUSE_TRADING,
                    reason=reason,
                    success=False,
                    details={"error": str(e)}
                )
                return False

    def resume_trading(self, reason: str = "手动恢复") -> bool:
        """
        恢复交易

        Args:
            reason: 恢复原因

        Returns:
            是否成功
        """
        with self._lock:
            if not self._trading_paused:
                self.logger.log_system("交易未处于暂停状态")
                return True

            try:
                # 启用网关交易功能
                self.gateway.enable_trading()
                self._trading_paused = False

                # 记录事件
                self._record_event(
                    action=EmergencyAction.RESUME_TRADING,
                    reason=reason,
                    success=True
                )

                self.logger.log_system("交易已恢复", {"reason": reason})

                if self.alert_service:
                    self.alert_service.info(
                        "交易恢复",
                        f"交易已恢复，原因：{reason}",
                        source="EmergencyHandler"
                    )

                return True

            except Exception as e:
                self.logger.log_exception(e, "resume trading")
                return False

    def stop_strategy(self, strategy_id: str = None, reason: str = "应急停止") -> bool:
        """
        停止策略执行
        满足评估表第20项：通过停止策略执行暂停交易

        Args:
            strategy_id: 策略ID，None表示停止所有策略
            reason: 停止原因

        Returns:
            是否成功
        """
        with self._lock:
            try:
                if strategy_id:
                    # 停止指定策略
                    if strategy_id in self._strategy_status:
                        self._strategy_status[strategy_id] = False
                        self.logger.log_system(f"策略{strategy_id}已停止", {"reason": reason})
                else:
                    # 停止所有策略
                    for sid in self._strategy_status:
                        self._strategy_status[sid] = False
                    self._strategy_stopped = True
                    self.logger.log_system("所有策略已停止", {"reason": reason})

                # 记录事件
                self._record_event(
                    action=EmergencyAction.STOP_STRATEGY,
                    reason=reason,
                    success=True,
                    details={"strategy_id": strategy_id or "ALL"}
                )

                if self.alert_service:
                    self.alert_service.warning(
                        "策略停止",
                        f"策略已停止，原因：{reason}",
                        source="EmergencyHandler"
                    )

                return True

            except Exception as e:
                self.logger.log_exception(e, "stop strategy")
                return False

    def force_logout(self, reason: str = "应急退出") -> bool:
        """
        强制退出账号
        满足评估表第20项：通过强制退出账号暂停交易

        Args:
            reason: 退出原因

        Returns:
            是否成功
        """
        with self._lock:
            try:
                # 先撤销所有订单
                self.cancel_all_orders(reason)

                # 关闭网关连接
                self.gateway.close()

                # 记录事件
                self._record_event(
                    action=EmergencyAction.FORCE_LOGOUT,
                    reason=reason,
                    success=True
                )

                self.logger.log_system("已强制退出账号", {"reason": reason})

                if self.alert_service:
                    self.alert_service.critical(
                        "强制退出",
                        f"已强制退出账号，原因：{reason}",
                        source="EmergencyHandler"
                    )

                return True

            except Exception as e:
                self.logger.log_exception(e, "force logout")
                return False

    # ==================== 第23-24项：批量撤单功能 ====================

    def cancel_orders_by_instrument(self, instrument_id: str,
                                    reason: str = "应急撤单") -> Dict[str, bool]:
        """
        按合约撤单（部分撤单）
        满足评估表第23项：部分撤单功能

        Args:
            instrument_id: 合约代码
            reason: 撤单原因

        Returns:
            撤单结果 {order_ref: success}
        """
        results = {}

        try:
            # 获取该合约的所有未成交订单
            orders = self._get_pending_orders(instrument_id)

            self.logger.log_system(f"开始撤销合约{instrument_id}的订单", {
                "order_count": len(orders),
                "reason": reason
            })

            for order_ref, order_info in orders.items():
                try:
                    success = self.gateway.cancel_order(
                        instrument_id=order_info.get("instrument_id", instrument_id),
                        order_ref=order_ref,
                        exchange_id=order_info.get("exchange_id", ""),
                        order_sys_id=order_info.get("order_sys_id", "")
                    )
                    results[order_ref] = success

                    if success:
                        self.logger.log_system(f"撤单成功: {order_ref}")
                    else:
                        self.logger.log_error(f"撤单失败: {order_ref}")

                except Exception as e:
                    self.logger.log_exception(e, f"cancel order {order_ref}")
                    results[order_ref] = False

                # 避免请求过快
                time.sleep(0.1)

            # 记录事件
            success_count = sum(1 for v in results.values() if v)
            self._record_event(
                action=EmergencyAction.CANCEL_ORDERS,
                reason=reason,
                success=success_count > 0,
                details={
                    "instrument_id": instrument_id,
                    "total": len(results),
                    "success": success_count
                }
            )

            return results

        except Exception as e:
            self.logger.log_exception(e, "cancel orders by instrument")
            return results

    def cancel_all_orders(self, reason: str = "全部撤单") -> Dict[str, bool]:
        """
        全部撤单
        满足评估表第24项：全部撤单功能

        Args:
            reason: 撤单原因

        Returns:
            撤单结果 {order_ref: success}
        """
        results = {}

        try:
            # 获取所有未成交订单
            all_orders = self._get_all_pending_orders()

            self.logger.log_system("开始全部撤单", {
                "order_count": len(all_orders),
                "reason": reason
            })

            if self.alert_service:
                self.alert_service.warning(
                    "全部撤单",
                    f"开始执行全部撤单，共{len(all_orders)}笔订单",
                    source="EmergencyHandler"
                )

            for order_ref, order_info in all_orders.items():
                try:
                    success = self.gateway.cancel_order(
                        instrument_id=order_info.get("instrument_id", ""),
                        order_ref=order_ref,
                        exchange_id=order_info.get("exchange_id", ""),
                        order_sys_id=order_info.get("order_sys_id", "")
                    )
                    results[order_ref] = success

                except Exception as e:
                    self.logger.log_exception(e, f"cancel order {order_ref}")
                    results[order_ref] = False

                # 避免请求过快
                time.sleep(0.1)

            # 记录事件
            success_count = sum(1 for v in results.values() if v)
            self._record_event(
                action=EmergencyAction.CANCEL_ORDERS,
                reason=reason,
                success=True,
                details={
                    "type": "ALL",
                    "total": len(results),
                    "success": success_count
                }
            )

            self.logger.log_system("全部撤单完成", {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            })

            return results

        except Exception as e:
            self.logger.log_exception(e, "cancel all orders")
            return results

    def _get_pending_orders(self, instrument_id: str = None) -> Dict[str, dict]:
        """获取待撤订单"""
        # 从网关获取当前订单
        orders = getattr(self.gateway, '_orders', {})

        pending = {}
        for order_ref, order in orders.items():
            # 检查订单状态（未成交或部分成交）
            if hasattr(order, 'OrderStatus'):
                status = order.OrderStatus
                if status in ['3', '1']:  # 未成交在队列中 或 部分成交在队列中
                    if instrument_id is None or order.InstrumentID == instrument_id:
                        pending[order_ref] = {
                            "instrument_id": order.InstrumentID,
                            "exchange_id": order.ExchangeID,
                            "order_sys_id": order.OrderSysID,
                            "direction": order.Direction,
                            "volume_total": order.VolumeTotal
                        }

        # 合并缓存的订单
        for order_ref, order_info in self._pending_orders.items():
            if instrument_id is None or order_info.get("instrument_id") == instrument_id:
                if order_ref not in pending:
                    pending[order_ref] = order_info

        return pending

    def _get_all_pending_orders(self) -> Dict[str, dict]:
        """获取所有待撤订单"""
        return self._get_pending_orders(instrument_id=None)

    def register_pending_order(self, order_ref: str, order_info: dict):
        """注册待撤订单（供外部调用）"""
        self._pending_orders[order_ref] = order_info

    def unregister_pending_order(self, order_ref: str):
        """注销待撤订单"""
        self._pending_orders.pop(order_ref, None)

    # ==================== 策略管理 ====================

    def register_strategy(self, strategy_id: str, strategy: Callable):
        """注册策略"""
        self._strategies[strategy_id] = strategy
        self._strategy_status[strategy_id] = True

    def unregister_strategy(self, strategy_id: str):
        """注销策略"""
        self._strategies.pop(strategy_id, None)
        self._strategy_status.pop(strategy_id, None)

    def is_strategy_running(self, strategy_id: str) -> bool:
        """检查策略是否运行中"""
        return self._strategy_status.get(strategy_id, False)

    def is_trading_paused(self) -> bool:
        """检查交易是否暂停"""
        return self._trading_paused

    # ==================== 事件记录 ====================

    def _record_event(self, action: EmergencyAction, reason: str,
                      success: bool, details: dict = None):
        """记录应急事件"""
        event = EmergencyEvent(
            action=action,
            timestamp=datetime.now(),
            reason=reason,
            success=success,
            details=details or {}
        )
        self._event_history.append(event)

    def get_event_history(self, limit: int = 100) -> List[EmergencyEvent]:
        """获取事件历史"""
        return self._event_history[-limit:]

    # ==================== 一键应急 ====================

    def emergency_stop(self, reason: str = "紧急停止"):
        """
        一键紧急停止
        执行所有应急措施：暂停交易 + 停止策略 + 全部撤单

        Args:
            reason: 停止原因
        """
        self.logger.log_system("执行一键紧急停止", {"reason": reason})

        if self.alert_service:
            self.alert_service.critical(
                "紧急停止",
                f"正在执行一键紧急停止，原因：{reason}",
                source="EmergencyHandler"
            )

        # 1. 暂停交易
        self.pause_trading(reason)

        # 2. 停止所有策略
        self.stop_strategy(reason=reason)

        # 3. 全部撤单
        self.cancel_all_orders(reason)

        self.logger.log_system("一键紧急停止完成")

    # ==================== 状态报告 ====================

    def get_status_report(self) -> dict:
        """获取状态报告"""
        return {
            "trading_paused": self._trading_paused,
            "strategy_stopped": self._strategy_stopped,
            "registered_strategies": list(self._strategies.keys()),
            "strategy_status": dict(self._strategy_status),
            "pending_orders_count": len(self._pending_orders),
            "event_count": len(self._event_history),
            "gateway_connected": self.gateway.is_connected(),
            "gateway_logged_in": self.gateway.is_logged_in()
        }
