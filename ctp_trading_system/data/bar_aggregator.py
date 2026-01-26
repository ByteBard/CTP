"""
Bar聚合器
tick级别数据实时聚合成K线

功能:
- tick到1分钟Bar实时聚合
- 每分钟自动切换新Bar
- 支持回调通知完成的Bar
- BarBuffer保存历史Bar用于特征计算
"""

from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Callable, List
from datetime import datetime


@dataclass
class BarData:
    """K线数据结构"""
    datetime: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'BarData':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BarAggregator:
    """
    Tick到Bar实时聚合器

    功能:
    - tick级别实时聚合成1分钟Bar
    - 每分钟自动切换新Bar
    - 支持回调通知完成的Bar
    """

    def __init__(self, on_bar_completed: Optional[Callable[[BarData], None]] = None):
        """
        Args:
            on_bar_completed: Bar完成时的回调函数
        """
        self._current_bar: Optional[BarData] = None
        self._current_minute: Optional[int] = None
        self._on_bar_completed = on_bar_completed
        self._last_volume: int = 0
        self._last_turnover: float = 0.0

    def on_tick(self, tick_data: dict) -> Optional[BarData]:
        """
        处理tick数据

        Args:
            tick_data: CTP tick数据字典

        Returns:
            如果一根Bar完成，返回该Bar，否则返回None
        """
        price = tick_data.get('last_price', 0)
        volume = tick_data.get('volume', 0)
        turnover = tick_data.get('turnover', 0.0)
        open_interest = tick_data.get('open_interest', 0.0)
        timestamp = tick_data.get('datetime', datetime.now().isoformat())

        # 解析分钟
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            current_minute = dt.minute
            bar_datetime = dt.replace(second=0, microsecond=0).isoformat()
        except:
            dt = datetime.now()
            current_minute = dt.minute
            bar_datetime = dt.replace(second=0, microsecond=0).isoformat()

        completed_bar = None

        # 新分钟开始 - 完成旧Bar，开始新Bar
        if self._current_minute is not None and current_minute != self._current_minute:
            completed_bar = self._current_bar
            self._current_bar = None

            # 通知完成
            if completed_bar and self._on_bar_completed:
                self._on_bar_completed(completed_bar)

        # 计算增量
        volume_delta = volume - self._last_volume if self._last_volume > 0 else 0
        turnover_delta = turnover - self._last_turnover if self._last_turnover > 0 else 0

        # 更新当前Bar
        if self._current_bar is None:
            self._current_bar = BarData(
                datetime=bar_datetime,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0,
                turnover=0.0,
                open_interest=open_interest
            )
        else:
            self._current_bar.high = max(self._current_bar.high, price)
            self._current_bar.low = min(self._current_bar.low, price)
            self._current_bar.close = price
            self._current_bar.volume += volume_delta
            self._current_bar.turnover += turnover_delta
            self._current_bar.open_interest = open_interest

        self._current_minute = current_minute
        self._last_volume = volume
        self._last_turnover = turnover

        return completed_bar

    def get_current_bar(self) -> Optional[BarData]:
        """获取当前未完成的Bar"""
        return self._current_bar

    def reset(self):
        """重置聚合器状态"""
        self._current_bar = None
        self._current_minute = None
        self._last_volume = 0
        self._last_turnover = 0.0


class BarBuffer:
    """
    Bar数据缓存
    保存最近N根Bar用于特征计算
    """

    def __init__(self, maxlen: int = 60):
        """
        Args:
            maxlen: 最大缓存数量，默认60根 (1小时)
        """
        self.maxlen = maxlen
        self._buffer: deque = deque(maxlen=maxlen)

    def add_bar(self, bar: BarData):
        """添加Bar"""
        self._buffer.append(bar)

    def get_bars(self) -> List[BarData]:
        """获取所有Bar"""
        return list(self._buffer)

    def size(self) -> int:
        """当前缓存大小"""
        return len(self._buffer)

    def is_ready(self, min_bars: int = 10) -> bool:
        """
        是否有足够的Bar

        Args:
            min_bars: 最小Bar数量
        """
        return len(self._buffer) >= min_bars

    def get_close_series(self) -> List[float]:
        """获取收盘价序列"""
        return [b.close for b in self._buffer]

    def get_high_series(self) -> List[float]:
        """获取最高价序列"""
        return [b.high for b in self._buffer]

    def get_low_series(self) -> List[float]:
        """获取最低价序列"""
        return [b.low for b in self._buffer]

    def get_volume_series(self) -> List[int]:
        """获取成交量序列"""
        return [b.volume for b in self._buffer]

    def get_latest(self, n: int = 1) -> List[BarData]:
        """获取最近N根Bar"""
        bars = list(self._buffer)
        return bars[-n:] if len(bars) >= n else bars

    def clear(self):
        """清空缓存"""
        self._buffer.clear()
