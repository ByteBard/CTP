"""
交易上下文
来源: C:\Repo\future-trading-strategy\live\trade_context.py

功能:
- 记录交易全链路数据
- 支持事后复盘验证
- 完整快照用于100%复现
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from datetime import datetime
import hashlib
import json
import numpy as np


@dataclass
class L1Snapshot:
    """L1行情快照"""
    last_price: float = 0.0
    bid_price1: float = 0.0
    bid_volume1: int = 0
    ask_price1: float = 0.0
    ask_volume1: int = 0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0
    timestamp_ms: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_tick(cls, tick_data: dict) -> 'L1Snapshot':
        """从tick数据创建"""
        return cls(
            last_price=tick_data.get('last_price', 0.0),
            bid_price1=tick_data.get('bid_price1', 0.0),
            bid_volume1=tick_data.get('bid_volume1', 0),
            ask_price1=tick_data.get('ask_price1', 0.0),
            ask_volume1=tick_data.get('ask_volume1', 0),
            volume=tick_data.get('volume', 0),
            turnover=tick_data.get('turnover', 0.0),
            open_interest=tick_data.get('open_interest', 0.0),
            timestamp_ms=int(tick_data.get('timestamp', 0) * 1000) if 'timestamp' in tick_data else 0
        )


@dataclass
class L2Snapshot:
    """L2深度快照 (5档)"""
    bid_prices: List[float] = field(default_factory=list)
    bid_volumes: List[int] = field(default_factory=list)
    ask_prices: List[float] = field(default_factory=list)
    ask_volumes: List[int] = field(default_factory=list)
    timestamp_ms: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SignalContext:
    """
    信号上下文
    记录信号生成时的所有相关数据
    """
    # 特征值
    feature_values: Dict[str, float] = field(default_factory=dict)

    # H1e策略特有
    imb_value: float = 0.0
    depth_value: int = 0
    volatility: float = 0.0
    imb_threshold: float = 0.0

    # LSTM策略特有
    prediction_prob: float = 0.5
    prediction_class: int = 0  # 0=持有, 1=做多, 2=做空
    rsi_value: float = 50.0
    lstm_hidden_state: Optional[List[float]] = None

    # 信号
    signal_direction: int = 0  # 1=多, -1=空, 0=无
    signal_strength: str = ""  # weak/medium/strong
    signal_reason: str = ""  # 信号生成原因

    def to_dict(self) -> Dict:
        result = asdict(self)
        # 处理numpy类型
        if result.get('lstm_hidden_state') is not None:
            result['lstm_hidden_state'] = [float(x) for x in result['lstm_hidden_state']]
        return result


@dataclass
class ExecutionContext:
    """
    执行上下文
    记录订单执行的详细信息
    """
    # 订单信息
    order_ref: str = ""
    order_sys_id: str = ""
    order_type: str = ""  # LIMIT/MARKET
    order_price: float = 0.0
    order_volume: int = 0

    # 成交信息
    fill_price: float = 0.0
    fill_volume: int = 0
    fill_time: str = ""

    # 滑点分析
    slippage_ticks: float = 0.0
    slippage_pct: float = 0.0

    # 延迟统计 (毫秒)
    signal_to_order_ms: int = 0
    order_to_ack_ms: int = 0
    ack_to_fill_ms: int = 0
    total_latency_ms: int = 0

    # 状态
    status: str = ""  # pending/filled/cancelled/rejected

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TradeContext:
    """
    完整交易上下文

    来源: C:\Repo\future-trading-strategy\live\trade_context.py

    用途:
    - 记录交易全链路数据
    - 支持事后复盘验证
    - 100%可复现 (保存完整缓存快照)
    """

    # ========== 基本信息 ==========
    trade_id: str = ""
    symbol: str = ""
    strategy_name: str = ""  # H1e_TICK / LSTM_L2
    trade_type: str = ""  # entry / exit
    timestamp: str = ""

    # ========== L1/L2快照 ==========
    l1_snapshot: Optional[L1Snapshot] = None
    l2_snapshot: Optional[L2Snapshot] = None

    # ========== 完整缓存快照 (用于100%复现) ==========
    # Tick窗口 (120个tick, ~6KB)
    tick_window: Optional[List[Dict]] = None

    # Bar序列 (10根bar, ~1KB)
    bar_sequence: Optional[List[Dict]] = None

    # 特征矩阵 ([10, 68], ~3KB)
    feature_matrix: Optional[List[List[float]]] = None
    feature_matrix_scaled: Optional[List[List[float]]] = None

    # ========== 信号上下文 ==========
    signal: Optional[SignalContext] = None

    # ========== 执行上下文 ==========
    execution: Optional[ExecutionContext] = None

    # ========== 元数据 ==========
    model_version: str = ""
    strategy_version: str = ""
    config_snapshot: Optional[Dict] = None

    def generate_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.symbol}_{self.timestamp}_{self.trade_type}_{datetime.now().microsecond}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}

        # 基本字段
        result['trade_id'] = self.trade_id
        result['symbol'] = self.symbol
        result['strategy_name'] = self.strategy_name
        result['trade_type'] = self.trade_type
        result['timestamp'] = self.timestamp

        # 快照
        result['l1_snapshot'] = self.l1_snapshot.to_dict() if self.l1_snapshot else None
        result['l2_snapshot'] = self.l2_snapshot.to_dict() if self.l2_snapshot else None

        # 缓存快照
        result['tick_window'] = self.tick_window
        result['bar_sequence'] = self.bar_sequence
        result['feature_matrix'] = self.feature_matrix
        result['feature_matrix_scaled'] = self.feature_matrix_scaled

        # 上下文
        result['signal'] = self.signal.to_dict() if self.signal else None
        result['execution'] = self.execution.to_dict() if self.execution else None

        # 元数据
        result['model_version'] = self.model_version
        result['strategy_version'] = self.strategy_version
        result['config_snapshot'] = self.config_snapshot

        return result

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False, indent=indent)

    def to_summary(self) -> Dict[str, Any]:
        """
        转换为摘要 (不含大型数据)
        用于JSON可读摘要文件
        """
        summary = {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'strategy_name': self.strategy_name,
            'trade_type': self.trade_type,
            'timestamp': self.timestamp,
            'model_version': self.model_version,
            'strategy_version': self.strategy_version
        }

        # L1摘要
        if self.l1_snapshot:
            summary['l1'] = {
                'last_price': self.l1_snapshot.last_price,
                'bid': f"{self.l1_snapshot.bid_price1}x{self.l1_snapshot.bid_volume1}",
                'ask': f"{self.l1_snapshot.ask_price1}x{self.l1_snapshot.ask_volume1}"
            }

        # 信号摘要
        if self.signal:
            summary['signal'] = {
                'direction': self.signal.signal_direction,
                'strength': self.signal.signal_strength,
                'imb': self.signal.imb_value,
                'prob': self.signal.prediction_prob
            }

        # 执行摘要
        if self.execution:
            summary['execution'] = {
                'order_ref': self.execution.order_ref,
                'fill_price': self.execution.fill_price,
                'slippage_pct': self.execution.slippage_pct,
                'latency_ms': self.execution.total_latency_ms
            }

        return summary

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeContext':
        """从字典创建"""
        ctx = cls(
            trade_id=data.get('trade_id', ''),
            symbol=data.get('symbol', ''),
            strategy_name=data.get('strategy_name', ''),
            trade_type=data.get('trade_type', ''),
            timestamp=data.get('timestamp', ''),
            model_version=data.get('model_version', ''),
            strategy_version=data.get('strategy_version', ''),
            config_snapshot=data.get('config_snapshot')
        )

        # L1/L2快照
        if data.get('l1_snapshot'):
            ctx.l1_snapshot = L1Snapshot(**data['l1_snapshot'])
        if data.get('l2_snapshot'):
            ctx.l2_snapshot = L2Snapshot(**data['l2_snapshot'])

        # 缓存快照
        ctx.tick_window = data.get('tick_window')
        ctx.bar_sequence = data.get('bar_sequence')
        ctx.feature_matrix = data.get('feature_matrix')
        ctx.feature_matrix_scaled = data.get('feature_matrix_scaled')

        # 上下文
        if data.get('signal'):
            ctx.signal = SignalContext(**data['signal'])
        if data.get('execution'):
            ctx.execution = ExecutionContext(**data['execution'])

        return ctx

    def get_size_estimate(self) -> int:
        """
        估算数据大小 (字节)

        Returns:
            估算大小
        """
        size = 0

        # 基本字段 ~200B
        size += 200

        # Tick窗口 (120 * 50B = 6KB)
        if self.tick_window:
            size += len(self.tick_window) * 50

        # Bar序列 (10 * 100B = 1KB)
        if self.bar_sequence:
            size += len(self.bar_sequence) * 100

        # 特征矩阵 (10 * 68 * 8B = 5.4KB)
        if self.feature_matrix:
            size += 10 * 68 * 8

        # 其他
        size += 500

        return size
