"""
报单监测模块
满足评估表要求：
- 第6项：单合约重复开仓交易指令数量监测（建议）
- 第7项：单合约重复平仓交易指令数量监测（建议）
- 第8项：单合约重复撤单交易指令数量监测（建议）
- 第9项：同一账号的报单交易指令数量监测（严重）
- 第10项：同一账号的撤单交易指令数量监测（严重）
"""
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, date
from collections import defaultdict
import threading

from ..logging.trade_logger import get_logger, TradeLogger


@dataclass
class OrderStatistics:
    """报单统计数据"""
    # 单合约统计
    open_count_by_instrument: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    close_count_by_instrument: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cancel_count_by_instrument: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # 账号总计
    total_order_count: int = 0      # 报单总笔数
    total_cancel_count: int = 0     # 撤单总笔数
    total_open_count: int = 0       # 开仓总笔数
    total_close_count: int = 0      # 平仓总笔数

    # 成交统计
    total_trade_count: int = 0      # 成交总笔数
    total_trade_volume: int = 0     # 成交总量

    # 日期
    trading_date: str = ""


@dataclass
class InstrumentOrderStats:
    """单合约报单统计"""
    instrument_id: str
    open_count: int = 0
    close_count: int = 0
    cancel_count: int = 0
    trade_count: int = 0
    last_order_time: Optional[datetime] = None


class OrderMonitor:
    """
    报单监测器
    满足评估表第6-10项要求
    """

    def __init__(self):
        """初始化报单监测器"""
        self.logger: TradeLogger = get_logger()

        # 当日统计
        self._stats = OrderStatistics()
        self._stats.trading_date = date.today().isoformat()

        # 合约详细统计
        self._instrument_stats: Dict[str, InstrumentOrderStats] = {}

        # 回调
        self._order_callbacks: List[Callable] = []
        self._threshold_callbacks: List[Callable] = []

        # 锁
        self._lock = threading.Lock()

        self.logger.log_system("报单监测器初始化完成")

    def _check_and_reset_daily(self):
        """检查并重置日统计"""
        today = date.today().isoformat()
        if self._stats.trading_date != today:
            self.logger.log_system("日期切换，重置统计", {
                "old_date": self._stats.trading_date,
                "new_date": today
            })
            self.reset_statistics()
            self._stats.trading_date = today

    def _get_instrument_stats(self, instrument_id: str) -> InstrumentOrderStats:
        """获取或创建合约统计"""
        if instrument_id not in self._instrument_stats:
            self._instrument_stats[instrument_id] = InstrumentOrderStats(
                instrument_id=instrument_id
            )
        return self._instrument_stats[instrument_id]

    # ==================== 报单计数 ====================

    def count_open_order(self, instrument_id: str, volume: int = 1) -> Dict:
        """
        记录开仓报单
        满足评估表第6项：单合约重复开仓监测
        满足评估表第9项：账号报单总数监测

        Args:
            instrument_id: 合约代码
            volume: 委托数量

        Returns:
            当前统计数据
        """
        with self._lock:
            self._check_and_reset_daily()

            # 更新合约统计
            self._stats.open_count_by_instrument[instrument_id] += 1
            inst_stats = self._get_instrument_stats(instrument_id)
            inst_stats.open_count += 1
            inst_stats.last_order_time = datetime.now()

            # 更新总计
            self._stats.total_order_count += 1
            self._stats.total_open_count += 1

            stats = {
                "instrument_id": instrument_id,
                "action": "OPEN",
                "instrument_open_count": inst_stats.open_count,
                "total_order_count": self._stats.total_order_count,
                "total_open_count": self._stats.total_open_count
            }

            self.logger.log_monitor("开仓报单计数", stats)

            # 触发回调
            self._notify_order_callback("open", instrument_id, stats)

            return stats

    def count_close_order(self, instrument_id: str, volume: int = 1) -> Dict:
        """
        记录平仓报单
        满足评估表第7项：单合约重复平仓监测
        满足评估表第9项：账号报单总数监测

        Args:
            instrument_id: 合约代码
            volume: 委托数量

        Returns:
            当前统计数据
        """
        with self._lock:
            self._check_and_reset_daily()

            # 更新合约统计
            self._stats.close_count_by_instrument[instrument_id] += 1
            inst_stats = self._get_instrument_stats(instrument_id)
            inst_stats.close_count += 1
            inst_stats.last_order_time = datetime.now()

            # 更新总计
            self._stats.total_order_count += 1
            self._stats.total_close_count += 1

            stats = {
                "instrument_id": instrument_id,
                "action": "CLOSE",
                "instrument_close_count": inst_stats.close_count,
                "total_order_count": self._stats.total_order_count,
                "total_close_count": self._stats.total_close_count
            }

            self.logger.log_monitor("平仓报单计数", stats)

            # 触发回调
            self._notify_order_callback("close", instrument_id, stats)

            return stats

    def count_cancel_order(self, instrument_id: str) -> Dict:
        """
        记录撤单
        满足评估表第8项：单合约重复撤单监测
        满足评估表第10项：账号撤单总数监测

        Args:
            instrument_id: 合约代码

        Returns:
            当前统计数据
        """
        with self._lock:
            self._check_and_reset_daily()

            # 更新合约统计
            self._stats.cancel_count_by_instrument[instrument_id] += 1
            inst_stats = self._get_instrument_stats(instrument_id)
            inst_stats.cancel_count += 1
            inst_stats.last_order_time = datetime.now()

            # 更新总计
            self._stats.total_cancel_count += 1

            stats = {
                "instrument_id": instrument_id,
                "action": "CANCEL",
                "instrument_cancel_count": inst_stats.cancel_count,
                "total_cancel_count": self._stats.total_cancel_count
            }

            self.logger.log_monitor("撤单计数", stats)

            # 触发回调
            self._notify_order_callback("cancel", instrument_id, stats)

            return stats

    def count_trade(self, instrument_id: str, volume: int) -> Dict:
        """
        记录成交

        Args:
            instrument_id: 合约代码
            volume: 成交数量

        Returns:
            当前统计数据
        """
        with self._lock:
            self._check_and_reset_daily()

            # 更新合约统计
            inst_stats = self._get_instrument_stats(instrument_id)
            inst_stats.trade_count += 1

            # 更新总计
            self._stats.total_trade_count += 1
            self._stats.total_trade_volume += volume

            stats = {
                "instrument_id": instrument_id,
                "action": "TRADE",
                "volume": volume,
                "instrument_trade_count": inst_stats.trade_count,
                "total_trade_count": self._stats.total_trade_count,
                "total_trade_volume": self._stats.total_trade_volume
            }

            return stats

    def _notify_order_callback(self, action: str, instrument_id: str, stats: dict):
        """通知订单回调"""
        for callback in self._order_callbacks:
            try:
                callback(action, instrument_id, stats)
            except Exception as e:
                self.logger.log_exception(e, "order callback")

    # ==================== 统计查询 ====================

    def get_statistics(self) -> OrderStatistics:
        """获取完整统计数据"""
        with self._lock:
            self._check_and_reset_daily()
            return self._stats

    def get_total_order_count(self) -> int:
        """
        获取账号报单总笔数
        满足评估表第9项
        """
        with self._lock:
            return self._stats.total_order_count

    def get_total_cancel_count(self) -> int:
        """
        获取账号撤单总笔数
        满足评估表第10项
        """
        with self._lock:
            return self._stats.total_cancel_count

    def get_instrument_open_count(self, instrument_id: str) -> int:
        """
        获取单合约开仓次数
        满足评估表第6项
        """
        with self._lock:
            return self._stats.open_count_by_instrument.get(instrument_id, 0)

    def get_instrument_close_count(self, instrument_id: str) -> int:
        """
        获取单合约平仓次数
        满足评估表第7项
        """
        with self._lock:
            return self._stats.close_count_by_instrument.get(instrument_id, 0)

    def get_instrument_cancel_count(self, instrument_id: str) -> int:
        """
        获取单合约撤单次数
        满足评估表第8项
        """
        with self._lock:
            return self._stats.cancel_count_by_instrument.get(instrument_id, 0)

    def get_instrument_stats(self, instrument_id: str) -> Optional[InstrumentOrderStats]:
        """获取合约统计详情"""
        with self._lock:
            return self._instrument_stats.get(instrument_id)

    def get_all_instrument_stats(self) -> Dict[str, InstrumentOrderStats]:
        """获取所有合约统计"""
        with self._lock:
            return dict(self._instrument_stats)

    # ==================== 统计报告 ====================

    def get_summary_report(self) -> dict:
        """获取汇总报告"""
        with self._lock:
            self._check_and_reset_daily()

            return {
                "trading_date": self._stats.trading_date,
                "total_order_count": self._stats.total_order_count,
                "total_cancel_count": self._stats.total_cancel_count,
                "total_open_count": self._stats.total_open_count,
                "total_close_count": self._stats.total_close_count,
                "total_trade_count": self._stats.total_trade_count,
                "total_trade_volume": self._stats.total_trade_volume,
                "instruments_count": len(self._instrument_stats),
                "top_instruments": self._get_top_instruments(5)
            }

    def _get_top_instruments(self, n: int = 5) -> List[dict]:
        """获取交易最活跃的合约"""
        sorted_instruments = sorted(
            self._instrument_stats.values(),
            key=lambda x: x.open_count + x.close_count + x.cancel_count,
            reverse=True
        )[:n]

        return [
            {
                "instrument_id": s.instrument_id,
                "open_count": s.open_count,
                "close_count": s.close_count,
                "cancel_count": s.cancel_count,
                "trade_count": s.trade_count
            }
            for s in sorted_instruments
        ]

    def log_statistics(self):
        """记录当前统计到日志"""
        report = self.get_summary_report()
        self.logger.log_order_statistics(report)

    # ==================== 管理 ====================

    def reset_statistics(self):
        """重置统计数据"""
        with self._lock:
            self._stats = OrderStatistics()
            self._stats.trading_date = date.today().isoformat()
            self._instrument_stats.clear()

        self.logger.log_system("报单统计已重置")

    def register_order_callback(self, callback: Callable):
        """注册报单回调"""
        self._order_callbacks.append(callback)

    def unregister_order_callback(self, callback: Callable):
        """注销报单回调"""
        if callback in self._order_callbacks:
            self._order_callbacks.remove(callback)
