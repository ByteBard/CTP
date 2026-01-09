"""
策略基类
提供策略开发的基础框架
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.ctp_gateway import CtpGateway, Direction, OffsetFlag
from ..validator.order_validator import OrderValidator, ValidationResult
from ..monitor.order_monitor import OrderMonitor
from ..logging.trade_logger import get_logger, TradeLogger


class BaseStrategy(ABC):
    """
    策略基类
    所有交易策略应继承此类
    """

    def __init__(self, strategy_id: str, gateway: CtpGateway,
                 validator: OrderValidator, order_monitor: OrderMonitor):
        """
        初始化策略

        Args:
            strategy_id: 策略ID
            gateway: CTP网关
            validator: 交易指令验证器
            order_monitor: 报单监测器
        """
        self.strategy_id = strategy_id
        self.gateway = gateway
        self.validator = validator
        self.order_monitor = order_monitor
        self.logger: TradeLogger = get_logger()

        # 策略状态
        self._running = False
        self._positions: Dict[str, int] = {}  # 策略持仓

        self.logger.log_system(f"策略{strategy_id}初始化完成")

    @abstractmethod
    def on_init(self):
        """策略初始化（子类实现）"""
        pass

    @abstractmethod
    def on_start(self):
        """策略启动（子类实现）"""
        pass

    @abstractmethod
    def on_stop(self):
        """策略停止（子类实现）"""
        pass

    @abstractmethod
    def on_tick(self, tick: dict):
        """
        行情回调（子类实现）

        Args:
            tick: 行情数据
        """
        pass

    @abstractmethod
    def on_order(self, order: dict):
        """
        订单回调（子类实现）

        Args:
            order: 订单数据
        """
        pass

    @abstractmethod
    def on_trade(self, trade: dict):
        """
        成交回调（子类实现）

        Args:
            trade: 成交数据
        """
        pass

    # ==================== 交易接口 ====================

    def buy_open(self, instrument_id: str, price: float, volume: int) -> Optional[str]:
        """
        买入开仓

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量

        Returns:
            报单引用，失败返回None
        """
        # 验证交易指令
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='0',  # 买
            offset='0',     # 开仓
            price=price,
            volume=volume
        )

        if not result.is_valid:
            self.logger.log_error(f"策略{self.strategy_id}买开验证失败",
                                  error_msg=result.error_message)
            return None

        # 记录报单
        self.order_monitor.count_open_order(instrument_id, volume)

        # 发送报单
        return self.gateway.open_position(
            instrument_id=instrument_id,
            direction=Direction.BUY,
            price=price,
            volume=volume
        )

    def sell_open(self, instrument_id: str, price: float, volume: int) -> Optional[str]:
        """
        卖出开仓

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量

        Returns:
            报单引用，失败返回None
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='1',  # 卖
            offset='0',     # 开仓
            price=price,
            volume=volume
        )

        if not result.is_valid:
            self.logger.log_error(f"策略{self.strategy_id}卖开验证失败",
                                  error_msg=result.error_message)
            return None

        self.order_monitor.count_open_order(instrument_id, volume)

        return self.gateway.open_position(
            instrument_id=instrument_id,
            direction=Direction.SELL,
            price=price,
            volume=volume
        )

    def buy_close(self, instrument_id: str, price: float, volume: int,
                  close_today: bool = False) -> Optional[str]:
        """
        买入平仓（平空仓）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量
            close_today: 是否平今

        Returns:
            报单引用，失败返回None
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='0',  # 买
            offset='1',     # 平仓
            price=price,
            volume=volume
        )

        if not result.is_valid:
            self.logger.log_error(f"策略{self.strategy_id}买平验证失败",
                                  error_msg=result.error_message)
            return None

        self.order_monitor.count_close_order(instrument_id, volume)

        return self.gateway.close_position(
            instrument_id=instrument_id,
            direction=Direction.BUY,
            price=price,
            volume=volume,
            close_today=close_today
        )

    def sell_close(self, instrument_id: str, price: float, volume: int,
                   close_today: bool = False) -> Optional[str]:
        """
        卖出平仓（平多仓）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量
            close_today: 是否平今

        Returns:
            报单引用，失败返回None
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='1',  # 卖
            offset='1',     # 平仓
            price=price,
            volume=volume
        )

        if not result.is_valid:
            self.logger.log_error(f"策略{self.strategy_id}卖平验证失败",
                                  error_msg=result.error_message)
            return None

        self.order_monitor.count_close_order(instrument_id, volume)

        return self.gateway.close_position(
            instrument_id=instrument_id,
            direction=Direction.SELL,
            price=price,
            volume=volume,
            close_today=close_today
        )

    def cancel_order(self, instrument_id: str, order_ref: str) -> bool:
        """
        撤单

        Args:
            instrument_id: 合约代码
            order_ref: 报单引用

        Returns:
            是否发送成功
        """
        self.order_monitor.count_cancel_order(instrument_id)
        return self.gateway.cancel_order(instrument_id, order_ref)

    # ==================== 策略控制 ====================

    def start(self):
        """启动策略"""
        if self._running:
            return

        self._running = True
        self.on_start()
        self.logger.log_system(f"策略{self.strategy_id}已启动")

    def stop(self):
        """停止策略"""
        if not self._running:
            return

        self._running = False
        self.on_stop()
        self.logger.log_system(f"策略{self.strategy_id}已停止")

    def is_running(self) -> bool:
        """是否运行中"""
        return self._running

    # ==================== 工具方法 ====================

    def get_position(self, instrument_id: str) -> int:
        """获取策略持仓"""
        return self._positions.get(instrument_id, 0)

    def update_position(self, instrument_id: str, delta: int):
        """更新策略持仓"""
        current = self._positions.get(instrument_id, 0)
        self._positions[instrument_id] = current + delta
