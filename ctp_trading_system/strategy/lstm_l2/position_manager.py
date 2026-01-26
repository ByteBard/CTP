"""
LSTM策略仓位管理器
三态状态机: Flat → Probe → Full → Trail

来源: L2滑点回测.py

状态转换:
- Flat: 无仓位，等待信号
- Probe: 试探仓 (30%)，等待确认
- Full: 满仓 (100%)，等待追踪
- Trail: 追踪止盈，锁定利润
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from datetime import datetime


class PositionState(Enum):
    """仓位状态"""
    FLAT = "flat"       # 无仓位
    PROBE = "probe"     # 试探仓 30%
    FULL = "full"       # 满仓 100%
    TRAIL = "trail"     # 追踪止盈


@dataclass
class PositionConfig:
    """
    仓位管理配置

    来源: L2滑点回测.py 的 DEFAULT_PARAMS 和 BEST_PARAMS
    """
    # 止损止盈参数
    sl: float = 0.004           # 止损 0.4%
    tp: float = 0.012           # 止盈 1.2%

    # RSI过滤
    rsi_upper: float = 55       # RSI上限 (避免追涨)
    rsi_lower: float = 45       # RSI下限 (避免追跌)

    # 信号阈值
    threshold: float = 0.5      # LSTM概率阈值

    # 仓位比例
    probe_size: float = 0.3     # 试探仓比例 30%
    full_size: float = 1.0      # 满仓比例 100%

    # 追踪止盈
    trail_dd: float = 0.30      # 回撤止盈 30%

    # 派生参数 (自动计算)
    @property
    def probe_sl(self) -> float:
        """试探仓止损"""
        return self.sl  # 0.4%

    @property
    def probe_to_full(self) -> float:
        """试探仓升级阈值"""
        return self.sl  # 0.4%

    @property
    def full_sl(self) -> float:
        """满仓止损"""
        return self.sl + 0.001  # 0.5%

    @property
    def full_to_trail(self) -> float:
        """满仓升级追踪阈值"""
        return self.sl + 0.002  # 0.6%

    @property
    def trail_max(self) -> float:
        """追踪止盈上限"""
        return self.tp  # 1.2%


@dataclass
class Position:
    """仓位信息"""
    direction: int = 0          # 1=多, -1=空
    entry_price: float = 0.0    # 入场价格
    current_size: float = 0.0   # 当前仓位比例 (0.3 或 1.0)
    entry_time: Optional[datetime] = None
    entry_bar_count: int = 0    # 入场时Bar计数
    hold_bars: int = 0          # 持仓Bar数
    peak_profit: float = 0.0    # 峰值利润 (用于追踪)
    highest_price: float = 0.0  # 持仓期最高价
    lowest_price: float = 0.0   # 持仓期最低价
    entry_prob: float = 0.5     # 入场LSTM概率
    entry_rsi: float = 50.0     # 入场RSI


class PositionManager:
    """
    LSTM策略仓位管理器

    三态状态机:
    1. Flat: 无仓位，等待信号
    2. Probe: 试探仓30%，盈利0.4%升级，亏损0.4%止损
    3. Full: 满仓100%，盈利0.6%启动追踪，亏损0.5%止损
    4. Trail: 追踪止盈，盈利1.2%止盈，回撤30%止盈
    """

    def __init__(self, config: PositionConfig = None):
        """
        Args:
            config: 仓位配置
        """
        self.config = config or PositionConfig()
        self._state = PositionState.FLAT
        self._position: Optional[Position] = None

    @property
    def state(self) -> PositionState:
        return self._state

    @property
    def position(self) -> Optional[Position]:
        return self._position

    def is_flat(self) -> bool:
        return self._state == PositionState.FLAT

    def has_position(self) -> bool:
        return self._state != PositionState.FLAT

    def check_entry_signal(self, prob: float, rsi: float) -> int:
        """
        检查入场信号

        Args:
            prob: LSTM预测概率 [0, 1]
            rsi: RSI值

        Returns:
            信号方向: 1=做多, -1=做空, 0=无信号
        """
        if not self.is_flat():
            return 0

        # 基本信号
        if prob > self.config.threshold:
            signal = 1  # 做多
        elif prob < (1 - self.config.threshold):
            signal = -1  # 做空
        else:
            return 0

        # RSI过滤
        if signal == 1 and rsi > self.config.rsi_upper:
            return 0  # RSI过高，不追涨
        if signal == -1 and rsi < self.config.rsi_lower:
            return 0  # RSI过低，不追跌

        return signal

    def enter_position(self, direction: int, price: float, prob: float, rsi: float,
                       bar_count: int = 0) -> bool:
        """
        入场 (进入Probe状态)

        Args:
            direction: 方向 1=多, -1=空
            price: 入场价格
            prob: LSTM概率
            rsi: RSI值
            bar_count: 当前Bar计数

        Returns:
            是否成功入场
        """
        if not self.is_flat():
            return False

        self._position = Position(
            direction=direction,
            entry_price=price,
            current_size=self.config.probe_size,
            entry_time=datetime.now(),
            entry_bar_count=bar_count,
            hold_bars=0,
            peak_profit=0.0,
            highest_price=price,
            lowest_price=price,
            entry_prob=prob,
            entry_rsi=rsi
        )
        self._state = PositionState.PROBE

        return True

    def update(self, current_price: float, pending_signal: int = 0) -> Tuple[bool, str, float]:
        """
        更新仓位状态

        Args:
            current_price: 当前价格
            pending_signal: 待处理信号 (用于反向信号退出)

        Returns:
            (是否退出, 退出原因, 当前盈亏%)
        """
        if self.is_flat() or self._position is None:
            return False, "", 0.0

        # 更新持仓信息
        self._position.hold_bars += 1
        self._position.highest_price = max(self._position.highest_price, current_price)
        self._position.lowest_price = min(self._position.lowest_price, current_price)

        # 计算盈亏
        pnl_pct = self._calculate_pnl(current_price)

        # 更新峰值利润
        if pnl_pct > self._position.peak_profit:
            self._position.peak_profit = pnl_pct

        # 根据状态处理
        if self._state == PositionState.PROBE:
            return self._handle_probe_state(pnl_pct, pending_signal)
        elif self._state == PositionState.FULL:
            return self._handle_full_state(pnl_pct, pending_signal)
        elif self._state == PositionState.TRAIL:
            return self._handle_trail_state(pnl_pct, pending_signal)

        return False, "", pnl_pct

    def _calculate_pnl(self, current_price: float) -> float:
        """计算盈亏百分比"""
        if self._position is None or self._position.entry_price == 0:
            return 0.0

        if self._position.direction == 1:  # 多
            return (current_price - self._position.entry_price) / self._position.entry_price
        else:  # 空
            return (self._position.entry_price - current_price) / self._position.entry_price

    def _handle_probe_state(self, pnl_pct: float, pending_signal: int) -> Tuple[bool, str, float]:
        """
        处理Probe状态

        转换条件:
        - 盈利 >= 0.4%: 升级到Full
        - 亏损 >= 0.4%: 止损退出
        - 反向信号: 退出
        """
        # 检查升级到Full
        if pnl_pct >= self.config.probe_to_full:
            self._upgrade_to_full()
            return False, "", pnl_pct

        # 检查止损
        if pnl_pct <= -self.config.probe_sl:
            return True, "probe_sl", pnl_pct

        # 检查反向信号
        if pending_signal != 0 and pending_signal != self._position.direction:
            return True, "reverse_signal", pnl_pct

        return False, "", pnl_pct

    def _handle_full_state(self, pnl_pct: float, pending_signal: int) -> Tuple[bool, str, float]:
        """
        处理Full状态

        转换条件:
        - 盈利 >= 0.6%: 升级到Trail
        - 亏损 >= 0.5%: 止损退出
        - 反向信号: 退出
        """
        # 检查升级到Trail
        if pnl_pct >= self.config.full_to_trail:
            self._upgrade_to_trail()
            return False, "", pnl_pct

        # 检查止损
        if pnl_pct <= -self.config.full_sl:
            return True, "full_sl", pnl_pct

        # 检查反向信号
        if pending_signal != 0 and pending_signal != self._position.direction:
            return True, "reverse_signal", pnl_pct

        return False, "", pnl_pct

    def _handle_trail_state(self, pnl_pct: float, pending_signal: int) -> Tuple[bool, str, float]:
        """
        处理Trail状态

        退出条件:
        - 盈利 >= 1.2%: 止盈退出
        - 回撤 >= 30%: 追踪止盈退出
        - 反向信号: 退出
        """
        # 检查止盈
        if pnl_pct >= self.config.trail_max:
            return True, "trail_tp", pnl_pct

        # 检查追踪止盈 (回撤30%)
        if self._position.peak_profit > 0:
            drawdown = (self._position.peak_profit - pnl_pct) / self._position.peak_profit
            if drawdown >= self.config.trail_dd:
                return True, "trail_dd", pnl_pct

        # 检查反向信号
        if pending_signal != 0 and pending_signal != self._position.direction:
            return True, "reverse_signal", pnl_pct

        return False, "", pnl_pct

    def _upgrade_to_full(self):
        """升级到Full状态"""
        if self._position:
            self._position.current_size = self.config.full_size
        self._state = PositionState.FULL

    def _upgrade_to_trail(self):
        """升级到Trail状态"""
        self._state = PositionState.TRAIL

    def exit_position(self) -> Optional[Position]:
        """
        退出仓位

        Returns:
            退出前的仓位信息
        """
        position = self._position
        self._position = None
        self._state = PositionState.FLAT
        return position

    def get_status(self) -> dict:
        """获取状态"""
        return {
            'state': self._state.value,
            'has_position': self.has_position(),
            'position': {
                'direction': self._position.direction if self._position else 0,
                'entry_price': self._position.entry_price if self._position else 0,
                'current_size': self._position.current_size if self._position else 0,
                'hold_bars': self._position.hold_bars if self._position else 0,
                'peak_profit': self._position.peak_profit if self._position else 0,
                'entry_prob': self._position.entry_prob if self._position else 0
            } if self._position else None
        }

    def reset(self):
        """重置状态"""
        self._state = PositionState.FLAT
        self._position = None
