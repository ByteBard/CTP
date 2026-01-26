"""
风控引擎
来源: production_config.py

功能:
- 日内风控 (日亏损、交易数、连续亏损)
- 单笔风控 (最大亏损、最大持仓)
- 交易时段控制
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """风控配置"""
    # 日内风控
    daily_stop_loss_pct: float = -0.007    # 日亏-0.7%停止
    max_daily_trades: int = 500            # 最大日交易数
    max_consecutive_losses: int = 10       # 最大连续亏损次数

    # 单笔风控
    max_single_loss_pct: float = -0.005    # 单笔最大亏损-0.5%
    max_position_value: float = 100000     # 最大持仓金额

    # 仓位控制
    max_total_position: int = 10           # 最大总持仓手数
    max_single_position: int = 3           # 单策略最大持仓手数

    # 交易时段
    trading_sessions: List[Tuple[time, time]] = None
    enable_night_session: bool = True

    def __post_init__(self):
        if self.trading_sessions is None:
            # 默认交易时段
            self.trading_sessions = [
                (time(9, 0), time(10, 15)),    # 上午第一节
                (time(10, 30), time(11, 30)),  # 上午第二节
                (time(13, 30), time(15, 0)),   # 下午
            ]
            if self.enable_night_session:
                self.trading_sessions.append((time(21, 0), time(23, 0)))  # 夜盘


class RiskEngine:
    """
    风控引擎

    来源: production_config.py

    功能:
    - 日内风控检查
    - 单笔风控检查
    - 交易时段控制
    - 持仓控制
    """

    def __init__(self, config: RiskConfig = None):
        """
        Args:
            config: 风控配置
        """
        self.config = config or RiskConfig()

        # 日内状态
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._consecutive_losses: int = 0
        self._last_trade_date: Optional[datetime] = None
        self._trading_paused: bool = False
        self._pause_reason: str = ""

        # 持仓状态
        self._current_positions: dict = {}  # {strategy_name: position_size}

    def reset_daily(self):
        """每日重置"""
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._consecutive_losses = 0
        self._trading_paused = False
        self._pause_reason = ""
        logger.info("[RiskEngine] 日内风控已重置")

    def check_new_day(self):
        """检查是否新的交易日"""
        now = datetime.now()
        if self._last_trade_date is None or self._last_trade_date.date() != now.date():
            self.reset_daily()
            self._last_trade_date = now

    def check_trade_allowed(self, strategy_name: str = None) -> Tuple[bool, str]:
        """
        检查是否允许交易

        Args:
            strategy_name: 策略名称 (可选)

        Returns:
            (是否允许, 原因)
        """
        self.check_new_day()

        # 检查交易时段
        if not self._is_trading_time():
            return False, "非交易时段"

        # 检查是否暂停
        if self._trading_paused:
            return False, f"交易已暂停: {self._pause_reason}"

        # 检查日亏损
        if self._daily_pnl <= self.config.daily_stop_loss_pct:
            self._trading_paused = True
            self._pause_reason = f"日亏损{self._daily_pnl*100:.2f}%"
            return False, self._pause_reason

        # 检查日交易数
        if self._daily_trades >= self.config.max_daily_trades:
            return False, f"日交易数达到{self._daily_trades}"

        # 检查连续亏损
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            self._trading_paused = True
            self._pause_reason = f"连续亏损{self._consecutive_losses}次"
            return False, self._pause_reason

        # 检查持仓限制
        total_position = sum(self._current_positions.values())
        if total_position >= self.config.max_total_position:
            return False, f"总持仓达到{total_position}手"

        if strategy_name and self._current_positions.get(strategy_name, 0) >= self.config.max_single_position:
            return False, f"策略{strategy_name}持仓达到上限"

        return True, "OK"

    def check_single_trade(self, expected_loss_pct: float) -> Tuple[bool, str]:
        """
        检查单笔交易风险

        Args:
            expected_loss_pct: 预期最大亏损百分比 (负数)

        Returns:
            (是否允许, 原因)
        """
        if expected_loss_pct < self.config.max_single_loss_pct:
            return False, f"单笔预期亏损{expected_loss_pct*100:.2f}%超限"

        return True, "OK"

    def record_trade(self, strategy_name: str, pnl_pct: float):
        """
        记录交易结果

        Args:
            strategy_name: 策略名称
            pnl_pct: 收益百分比
        """
        self._daily_pnl += pnl_pct
        self._daily_trades += 1

        if pnl_pct < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        logger.info(f"[RiskEngine] 记录交易: {strategy_name}, PnL={pnl_pct*100:.4f}%, "
                   f"日累计={self._daily_pnl*100:.4f}%, 日交易数={self._daily_trades}")

    def update_position(self, strategy_name: str, position_delta: int):
        """
        更新持仓

        Args:
            strategy_name: 策略名称
            position_delta: 持仓变化 (正=开仓, 负=平仓)
        """
        current = self._current_positions.get(strategy_name, 0)
        new_position = max(0, current + position_delta)
        self._current_positions[strategy_name] = new_position

        logger.debug(f"[RiskEngine] 持仓更新: {strategy_name} {current} -> {new_position}")

    def _is_trading_time(self) -> bool:
        """检查是否在交易时段"""
        now = datetime.now().time()

        for start, end in self.config.trading_sessions:
            # 处理跨午夜的夜盘
            if start > end:
                if now >= start or now <= end:
                    return True
            else:
                if start <= now <= end:
                    return True

        return False

    def pause_trading(self, reason: str):
        """暂停交易"""
        self._trading_paused = True
        self._pause_reason = reason
        logger.warning(f"[RiskEngine] 暂停交易: {reason}")

    def resume_trading(self):
        """恢复交易"""
        self._trading_paused = False
        self._pause_reason = ""
        logger.info("[RiskEngine] 恢复交易")

    def get_status(self) -> dict:
        """获取风控状态"""
        return {
            'daily_pnl': self._daily_pnl,
            'daily_pnl_pct': f"{self._daily_pnl * 100:.4f}%",
            'daily_trades': self._daily_trades,
            'consecutive_losses': self._consecutive_losses,
            'trading_paused': self._trading_paused,
            'pause_reason': self._pause_reason,
            'positions': self._current_positions.copy(),
            'total_position': sum(self._current_positions.values()),
            'is_trading_time': self._is_trading_time()
        }

    def get_remaining_capacity(self, strategy_name: str = None) -> dict:
        """
        获取剩余容量

        Args:
            strategy_name: 策略名称 (可选)

        Returns:
            剩余容量字典
        """
        total_position = sum(self._current_positions.values())
        strategy_position = self._current_positions.get(strategy_name, 0) if strategy_name else 0

        return {
            'daily_loss_remaining': self.config.daily_stop_loss_pct - self._daily_pnl,
            'daily_trades_remaining': self.config.max_daily_trades - self._daily_trades,
            'consecutive_loss_remaining': self.config.max_consecutive_losses - self._consecutive_losses,
            'total_position_remaining': self.config.max_total_position - total_position,
            'strategy_position_remaining': self.config.max_single_position - strategy_position if strategy_name else None
        }
