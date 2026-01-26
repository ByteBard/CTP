"""
交易记录数据模型
整合自两个高收益策略的TradeDetail
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TradeDirection(Enum):
    """交易方向"""
    LONG = 1
    SHORT = -1


class ExitReason(Enum):
    """退出原因"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAIL_STOP = "trail_stop"
    IMB_REVERSAL = "imb_reversal"
    TIMEOUT = "timeout"
    MANUAL = "manual"
    PROBE_SL = "probe_sl"
    FULL_SL = "full_sl"
    TRAIL_EXIT = "trail_exit"


@dataclass
class TradeRecord:
    """
    统一交易记录模型

    整合自:
    - L2滑点回测.py TradeDetail (80+字段)
    - tick_timeframe_test.py TickTradeDetail
    """

    # ========== A. 定位与标识 ==========
    id: Optional[int] = None              # 数据库主键
    trade_id: int = 0                     # 策略内序号
    global_id: str = ""                   # 全局唯一ID
    strategy_name: str = ""               # 策略名: H1e_TICK / LSTM_L2
    config_name: str = ""                 # 配置名称
    symbol: str = ""                      # 合约代码
    run_id: str = ""                      # 运行批次ID

    # ========== B. 时间字段 ==========
    signal_datetime: Optional[datetime] = None  # 信号时间
    entry_datetime: Optional[datetime] = None   # 入场时间
    exit_datetime: Optional[datetime] = None    # 出场时间
    signal_timestamp_ms: int = 0          # 信号毫秒时间戳
    entry_timestamp_ms: int = 0           # 入场毫秒时间戳
    exit_timestamp_ms: int = 0            # 出场毫秒时间戳

    # ========== C. 方向与仓位 ==========
    direction: int = 0                    # 1=多, -1=空
    volume: int = 1                       # 手数
    position_state: str = ""              # 仓位状态: probe/full/trail
    hold_duration_seconds: float = 0      # 持仓时长(秒)
    hold_bars: int = 0                    # 持仓bar数 (LSTM)
    hold_ticks: int = 0                   # 持仓tick数 (H1e)

    # ========== D. 价格与执行 ==========
    signal_price: float = 0.0             # 信号价格
    entry_price: float = 0.0              # 成交价格
    exit_price: float = 0.0               # 平仓价格
    highest_price: float = 0.0            # 持仓期最高价
    lowest_price: float = 0.0             # 持仓期最低价

    # ========== E. 信号质量 (策略特有) ==========
    entry_imb: float = 0.0                # H1e: IMB值
    entry_prob: float = 0.5               # LSTM: 预测概率
    signal_strength: str = ""             # 信号强度: weak/medium/strong
    entry_depth: int = 0                  # 盘口深度
    entry_volatility: float = 0.0         # 入场波动率
    entry_rsi: float = 50.0               # RSI值

    # ========== F. 收益与成本 ==========
    pnl_ticks: float = 0.0                # 盈亏跳数
    gross_pnl_pct: float = 0.0            # 毛收益%
    net_pnl_pct: float = 0.0              # 净收益%
    commission: float = 0.0               # 手续费
    slippage_pct: float = 0.0             # 滑点%
    total_cost_pct: float = 0.0           # 总成本%

    # ========== G. MAE/MFE ==========
    mae_pct: float = 0.0                  # 最大不利偏移%
    mfe_pct: float = 0.0                  # 最大有利偏移%
    r_multiple: float = 0.0               # R倍数

    # ========== H. 退出状态 ==========
    exit_reason: str = ""                 # 退出原因
    final_state: str = ""                 # completed/cancelled/error

    # ========== I. CTP订单关联 ==========
    entry_order_ref: str = ""             # 入场报单引用
    exit_order_ref: str = ""              # 平仓报单引用
    entry_order_sys_id: str = ""          # 交易所入场单号
    exit_order_sys_id: str = ""           # 交易所平仓单号

    # ========== J. 扩展数据 (JSON) ==========
    l2_snapshot_entry: Optional[Dict] = None   # 入场L2盘口快照
    l2_snapshot_exit: Optional[Dict] = None    # 出场L2盘口快照
    extra_data: Optional[Dict] = None          # 其他扩展数据

    # ========== K. 元数据 ==========
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def calculate_pnl(self, tick_size: float = 0.2, tick_value: float = 10.0):
        """
        计算收益

        Args:
            tick_size: 最小变动价位
            tick_value: 每跳价值
        """
        if self.entry_price == 0:
            return

        # 计算跳数
        if self.direction == 1:  # 多
            self.pnl_ticks = (self.exit_price - self.entry_price) / tick_size
        else:  # 空
            self.pnl_ticks = (self.entry_price - self.exit_price) / tick_size

        # 计算百分比
        self.gross_pnl_pct = self.pnl_ticks * tick_size / self.entry_price
        self.net_pnl_pct = self.gross_pnl_pct - self.total_cost_pct

    def calculate_mae_mfe(self):
        """计算MAE/MFE"""
        if self.entry_price == 0:
            return

        if self.direction == 1:  # 多
            self.mfe_pct = (self.highest_price - self.entry_price) / self.entry_price
            self.mae_pct = (self.lowest_price - self.entry_price) / self.entry_price
        else:  # 空
            self.mfe_pct = (self.entry_price - self.lowest_price) / self.entry_price
            self.mae_pct = (self.entry_price - self.highest_price) / self.entry_price
