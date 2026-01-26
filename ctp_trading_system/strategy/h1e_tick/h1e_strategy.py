"""
H1e Tick策略
IMB订单流不平衡高频策略

来源: tick_timeframe_test.py, production_config.py

收益: +13,706% (16个月, 67,926笔交易)
胜率: 95.6%

核心逻辑:
1. 信号: |IMB| > 0.8 且 深度 > 1500 且 波动率 < 0.00015
2. 入场: IMB > 0 做多, IMB < 0 做空
3. 出场: 阶梯止盈 [(15,2.0), (30,1.0)], 止损2跳
4. 风控: 日亏-0.7%停止交易 (关键!)
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Optional, Callable, List, Tuple, Dict, Any
import threading
import logging

from .imb_calculator import IMBCalculator, IMBSignal
from ...data import TickCache, TradeContext, ContextManager, L1Snapshot
from ...data.trade_context import SignalContext, ExecutionContext
from ...risk import RiskEngine

logger = logging.getLogger(__name__)


class PositionState(Enum):
    """持仓状态"""
    FLAT = "flat"           # 无仓位
    HOLDING = "holding"     # 持仓中
    PENDING = "pending"     # 挂单中


@dataclass
class H1eConfig:
    """
    H1e策略配置

    来源: production_config.py 的 H1e_止损_0.7 配置
    """
    # 合约配置
    instrument_id: str = "rb2505"
    tick_size: float = 1.0          # 最小变动价位

    # 入场条件
    imb_threshold: float = 0.8      # IMB阈值
    min_depth: int = 1500           # 最小深度
    max_volatility: float = 0.00015 # 最大波动率
    signal_cooldown: int = 10       # 信号冷却tick数

    # 出场条件 - 阶梯止盈
    use_staggered_tp: bool = True
    staggered_tp_levels: List[Tuple[int, float]] = field(
        default_factory=lambda: [(15, 2.0), (30, 1.0)]
    )  # [(持仓tick数, 目标利润跳数)]
    stop_loss_ticks: float = 2.0    # 止损跳数
    max_hold_ticks: int = 30        # 最大持仓tick数
    timeout_action: str = "discard" # 超时动作: discard/market_exit

    # 日内风控 (关键!)
    daily_stop_loss_pct: float = -0.007  # 日亏-0.7%停止 (H1e核心!)
    max_daily_trades: int = 500

    # 仓位管理
    position_size: int = 1          # 每笔手数
    max_position: int = 1           # 最大持仓

    # 成本
    commission_rate: float = 0.00011 * 2  # 双边手续费 0.022%


@dataclass
class H1ePosition:
    """持仓信息"""
    direction: int = 0              # 1=多, -1=空
    entry_price: float = 0.0        # 入场价格
    entry_time: Optional[datetime] = None
    entry_tick_count: int = 0       # 入场时tick计数
    size: int = 0                   # 持仓手数
    highest_price: float = 0.0      # 持仓期最高价
    lowest_price: float = 0.0       # 持仓期最低价
    hold_ticks: int = 0             # 持仓tick数
    order_ref: str = ""             # 订单引用
    entry_imb: float = 0.0          # 入场IMB值
    entry_depth: int = 0            # 入场深度


class H1eTickStrategy:
    """
    H1e Tick策略

    来源: tick_timeframe_test.py

    核心逻辑:
    1. 使用IMB (订单流不平衡) 作为入场信号
    2. 阶梯止盈: 前15个tick目标2跳，之后目标1跳
    3. 止损2跳
    4. 日亏-0.7%停止交易 (关键优化!)
    """

    def __init__(self, trading_system, config: H1eConfig = None):
        """
        Args:
            trading_system: CTP交易系统实例
            config: 策略配置
        """
        self.system = trading_system
        self.config = config or H1eConfig()

        # 核心组件
        self._imb_calculator = IMBCalculator(
            imb_threshold=self.config.imb_threshold,
            min_depth=self.config.min_depth,
            max_volatility=self.config.max_volatility
        )
        self._tick_cache = TickCache(maxlen=120)
        self._context_manager = ContextManager()

        # 状态
        self._state = PositionState.FLAT
        self._position: Optional[H1ePosition] = None
        self._running = False
        self._tick_count = 0
        self._last_signal_tick = 0

        # 日内统计
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._daily_stop_triggered = False
        self._last_trade_date: Optional[datetime] = None

        # 回调
        self._log_callback: Optional[Callable] = None

        # 交易记录
        self._trades: List[Dict] = []

    def register_log_callback(self, callback: Callable):
        """注册日志回调"""
        self._log_callback = callback

    def _log(self, level: str, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"{timestamp} [H1e] {message}"
        print(log_msg)
        logger.info(log_msg)
        if self._log_callback:
            try:
                self._log_callback("H1e_TICK", level, message)
            except:
                pass

    def start(self) -> bool:
        """启动策略"""
        if self._running:
            self._log("WARN", "策略已在运行中")
            return False

        self._running = True
        self._state = PositionState.FLAT
        self._position = None
        self._tick_count = 0
        self._last_signal_tick = 0

        # 启动上下文管理器
        self._context_manager.start()

        self._log("INFO", f"策略启动: {self.config.instrument_id}")
        self._log("INFO", f"IMB阈值={self.config.imb_threshold}, "
                         f"深度>{self.config.min_depth}, "
                         f"波动率<{self.config.max_volatility}")
        self._log("INFO", f"止盈={self.config.staggered_tp_levels}, "
                         f"止损={self.config.stop_loss_ticks}跳")
        self._log("INFO", f"日亏停止={self.config.daily_stop_loss_pct*100:.1f}% (关键!)")

        return True

    def stop(self):
        """停止策略"""
        self._running = False
        self._context_manager.stop()
        self._log("INFO", f"策略停止, 日交易{self._daily_trades}笔, 日收益{self._daily_pnl*100:.4f}%")

    def on_tick(self, tick_data: dict):
        """
        处理tick数据 (策略核心入口)

        Args:
            tick_data: CTP tick数据
        """
        if not self._running:
            return

        self._tick_count += 1

        # 检查新交易日
        self._check_new_day(tick_data)

        # 检查日内止损
        if self._daily_stop_triggered:
            return

        # 添加到tick缓存
        self._tick_cache.add_from_ctp(tick_data)

        # 计算IMB信号
        signal = self._imb_calculator.process_tick(tick_data)

        # 根据状态处理
        if self._state == PositionState.FLAT:
            self._handle_flat_state(signal, tick_data)
        elif self._state == PositionState.HOLDING:
            self._handle_holding_state(signal, tick_data)

    def _check_new_day(self, tick_data: dict):
        """检查是否新交易日"""
        try:
            tick_time = tick_data.get('datetime', '')
            if isinstance(tick_time, str) and tick_time:
                dt = datetime.fromisoformat(tick_time.replace('Z', ''))
            else:
                dt = datetime.now()

            if self._last_trade_date is None or self._last_trade_date.date() != dt.date():
                # 新交易日，重置日内统计
                if self._last_trade_date is not None:
                    self._log("INFO", f"新交易日，上日收益: {self._daily_pnl*100:.4f}%")

                self._daily_pnl = 0.0
                self._daily_trades = 0
                self._daily_stop_triggered = False
                self._last_trade_date = dt
                self._log("INFO", f"日内统计已重置")
        except:
            pass

    def _handle_flat_state(self, signal: IMBSignal, tick_data: dict):
        """处理空仓状态"""
        # 检查日内止损
        if self._daily_pnl <= self.config.daily_stop_loss_pct:
            self._daily_stop_triggered = True
            self._log("WARN", f"日亏损{self._daily_pnl*100:.2f}%触发止损，停止交易")
            return

        # 检查日交易数
        if self._daily_trades >= self.config.max_daily_trades:
            return

        # 检查信号冷却
        if self._tick_count - self._last_signal_tick < self.config.signal_cooldown:
            return

        # 检查信号有效性
        if not signal.signal_valid:
            return

        # 生成入场信号
        self._enter_position(signal, tick_data)

    def _handle_holding_state(self, signal: IMBSignal, tick_data: dict):
        """处理持仓状态"""
        if self._position is None:
            self._state = PositionState.FLAT
            return

        # 更新持仓信息
        self._position.hold_ticks += 1
        last_price = tick_data.get('last_price', 0)

        if last_price > 0:
            self._position.highest_price = max(self._position.highest_price, last_price)
            self._position.lowest_price = min(self._position.lowest_price, last_price)

        # 计算盈亏
        pnl_ticks = self._calculate_pnl_ticks(last_price)

        # 检查出场条件
        exit_reason = self._check_exit_conditions(pnl_ticks)

        if exit_reason:
            self._exit_position(last_price, exit_reason, tick_data)

    def _calculate_pnl_ticks(self, current_price: float) -> float:
        """计算盈亏跳数"""
        if self._position is None or self._position.entry_price == 0:
            return 0.0

        if self._position.direction == 1:  # 多
            return (current_price - self._position.entry_price) / self.config.tick_size
        else:  # 空
            return (self._position.entry_price - current_price) / self.config.tick_size

    def _check_exit_conditions(self, pnl_ticks: float) -> Optional[str]:
        """
        检查出场条件

        来源: tick_timeframe_test.py 的阶梯止盈逻辑

        Returns:
            退出原因，或None表示不退出
        """
        if self._position is None:
            return None

        hold_ticks = self._position.hold_ticks

        # 1. 检查止损
        if pnl_ticks <= -self.config.stop_loss_ticks:
            return "stop_loss"

        # 2. 检查阶梯止盈
        if self.config.use_staggered_tp:
            for max_ticks, target_profit in self.config.staggered_tp_levels:
                if hold_ticks <= max_ticks and pnl_ticks >= target_profit:
                    return f"take_profit_{target_profit}"

        # 3. 检查最大持仓时间
        if hold_ticks >= self.config.max_hold_ticks:
            if self.config.timeout_action == "discard":
                return "timeout_discard"
            else:
                return "timeout_exit"

        return None

    def _enter_position(self, signal: IMBSignal, tick_data: dict):
        """入场"""
        direction = signal.direction
        entry_price = signal.mid_price

        if entry_price <= 0:
            return

        # 创建持仓
        self._position = H1ePosition(
            direction=direction,
            entry_price=entry_price,
            entry_time=datetime.now(),
            entry_tick_count=self._tick_count,
            size=self.config.position_size,
            highest_price=entry_price,
            lowest_price=entry_price,
            hold_ticks=0,
            entry_imb=signal.imb_value,
            entry_depth=signal.total_depth
        )

        self._state = PositionState.HOLDING
        self._last_signal_tick = self._tick_count

        direction_str = "多" if direction == 1 else "空"
        self._log("INFO", f"[ENTRY] {direction_str} @ {entry_price:.2f}, "
                         f"IMB={signal.imb_value:.3f}, 深度={signal.total_depth}")

        # 发送订单到CTP
        self._send_entry_order(direction, entry_price)

        # 保存交易上下文
        self._save_entry_context(signal, tick_data)

    def _exit_position(self, exit_price: float, reason: str, tick_data: dict):
        """出场"""
        if self._position is None:
            return

        # 如果是discard，不实际执行
        if reason == "timeout_discard":
            self._log("INFO", f"[DISCARD] 超时{self._position.hold_ticks}tick未达标，放弃")
            self._position = None
            self._state = PositionState.FLAT
            return

        # 计算盈亏
        pnl_ticks = self._calculate_pnl_ticks(exit_price)
        pnl_pct = pnl_ticks * self.config.tick_size / self._position.entry_price
        cost_pct = self.config.commission_rate
        net_pnl_pct = pnl_pct - cost_pct

        # 更新日内统计
        self._daily_pnl += net_pnl_pct
        self._daily_trades += 1

        direction_str = "多" if self._position.direction == 1 else "空"
        self._log("INFO", f"[EXIT] {direction_str} @ {exit_price:.2f}, "
                         f"原因={reason}, PnL={pnl_ticks:.1f}跳, "
                         f"净收益={net_pnl_pct*100:.4f}%")
        self._log("INFO", f"[DAILY] 交易{self._daily_trades}笔, 日收益={self._daily_pnl*100:.4f}%")

        # 记录交易
        trade = {
            'trade_id': len(self._trades) + 1,
            'direction': self._position.direction,
            'entry_price': self._position.entry_price,
            'exit_price': exit_price,
            'entry_imb': self._position.entry_imb,
            'entry_depth': self._position.entry_depth,
            'hold_ticks': self._position.hold_ticks,
            'pnl_ticks': pnl_ticks,
            'net_pnl_pct': net_pnl_pct,
            'exit_reason': reason,
            'entry_time': self._position.entry_time.isoformat() if self._position.entry_time else '',
            'exit_time': datetime.now().isoformat()
        }
        self._trades.append(trade)

        # 发送平仓订单
        self._send_exit_order(self._position.direction, exit_price)

        # 保存交易上下文
        self._save_exit_context(exit_price, reason, tick_data)

        # 清除持仓
        self._position = None
        self._state = PositionState.FLAT

    def _send_entry_order(self, direction: int, price: float):
        """发送入场订单到CTP"""
        try:
            if not hasattr(self.system, 'gateway') or self.system.gateway is None:
                return

            direction_str = 'BUY' if direction == 1 else 'SELL'
            order_ref = self.system.gateway.open_position(
                self.config.instrument_id,
                direction=direction_str,
                price=price,
                volume=self.config.position_size
            )
            if order_ref and self._position:
                self._position.order_ref = order_ref
        except Exception as e:
            self._log("ERROR", f"发送入场订单失败: {e}")

    def _send_exit_order(self, direction: int, price: float):
        """发送出场订单到CTP"""
        try:
            if not hasattr(self.system, 'gateway') or self.system.gateway is None:
                return

            # 平仓方向与持仓方向相反
            close_direction = 'SELL' if direction == 1 else 'BUY'
            self.system.gateway.close_position(
                self.config.instrument_id,
                direction=close_direction,
                price=price,
                volume=self.config.position_size,
                close_today=True
            )
        except Exception as e:
            self._log("ERROR", f"发送出场订单失败: {e}")

    def _save_entry_context(self, signal: IMBSignal, tick_data: dict):
        """保存入场上下文"""
        try:
            ctx = TradeContext(
                symbol=self.config.instrument_id,
                strategy_name="H1e_TICK",
                trade_type="entry",
                timestamp=datetime.now().isoformat(),
                strategy_version="1.0",
                l1_snapshot=L1Snapshot.from_tick(tick_data),
                tick_window=[t.to_dict() for t in self._tick_cache.get_ticks()[-30:]],
                signal=SignalContext(
                    imb_value=signal.imb_value,
                    depth_value=signal.total_depth,
                    volatility=signal.volatility,
                    signal_direction=signal.direction,
                    signal_strength=self._imb_calculator.get_signal_strength(signal.imb_value)
                )
            )
            self._context_manager.save(ctx)
        except Exception as e:
            self._log("WARN", f"保存入场上下文失败: {e}")

    def _save_exit_context(self, exit_price: float, reason: str, tick_data: dict):
        """保存出场上下文"""
        try:
            ctx = TradeContext(
                symbol=self.config.instrument_id,
                strategy_name="H1e_TICK",
                trade_type="exit",
                timestamp=datetime.now().isoformat(),
                strategy_version="1.0",
                l1_snapshot=L1Snapshot.from_tick(tick_data),
                signal=SignalContext(
                    signal_reason=reason
                ),
                execution=ExecutionContext(
                    fill_price=exit_price
                )
            )
            self._context_manager.save(ctx)
        except Exception as e:
            self._log("WARN", f"保存出场上下文失败: {e}")

    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            'name': 'H1e_TICK',
            'running': self._running,
            'state': self._state.value,
            'tick_count': self._tick_count,
            'daily_pnl': self._daily_pnl,
            'daily_pnl_pct': f"{self._daily_pnl*100:.4f}%",
            'daily_trades': self._daily_trades,
            'daily_stop': self._daily_stop_triggered,
            'position': {
                'direction': self._position.direction if self._position else 0,
                'entry_price': self._position.entry_price if self._position else 0,
                'hold_ticks': self._position.hold_ticks if self._position else 0,
                'entry_imb': self._position.entry_imb if self._position else 0
            } if self._position else None,
            'config': {
                'instrument_id': self.config.instrument_id,
                'imb_threshold': self.config.imb_threshold,
                'daily_stop_loss': f"{self.config.daily_stop_loss_pct*100:.1f}%"
            }
        }

    def get_trades(self) -> List[Dict]:
        """获取交易记录"""
        return self._trades.copy()

    def get_daily_stats(self) -> dict:
        """获取日内统计"""
        if not self._trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl_pct': 0
            }

        winning = [t for t in self._trades if t['net_pnl_pct'] > 0]
        return {
            'total_trades': len(self._trades),
            'winning_trades': len(winning),
            'win_rate': len(winning) / len(self._trades) if self._trades else 0,
            'total_pnl_pct': sum(t['net_pnl_pct'] for t in self._trades),
            'avg_pnl_pct': sum(t['net_pnl_pct'] for t in self._trades) / len(self._trades)
        }
