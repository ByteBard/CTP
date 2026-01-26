"""
IMB (订单流不平衡) 计算器
来源: tick_timeframe_test.py

IMB公式: (BidVolume - AskVolume) / (BidVolume + AskVolume + 1)
范围: [-1.0, 1.0]
- 正值: 买盘强势
- 负值: 卖盘强势
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np


@dataclass
class IMBSignal:
    """IMB信号数据"""
    imb_value: float = 0.0          # IMB值
    total_depth: int = 0            # 总深度 (买卖量之和)
    volatility: float = 0.0         # 波动率
    direction: int = 0              # 方向: 1=多, -1=空, 0=无
    signal_valid: bool = False      # 信号是否有效
    mid_price: float = 0.0          # 中间价
    bid_price: float = 0.0          # 买一价
    ask_price: float = 0.0          # 卖一价
    timestamp: str = ""             # 时间戳


class IMBCalculator:
    """
    IMB计算器

    来源: tick_timeframe_test.py

    核心逻辑:
    - IMB = (BidVol - AskVol) / (BidVol + AskVol + 1)
    - 信号条件: |IMB| > threshold AND depth > min_depth AND vol < max_vol
    """

    def __init__(self,
                 imb_threshold: float = 0.8,
                 min_depth: int = 1500,
                 max_volatility: float = 0.00015,
                 volatility_window: int = 20):
        """
        Args:
            imb_threshold: IMB阈值，默认0.8
            min_depth: 最小深度，默认1500
            max_volatility: 最大波动率，默认0.00015
            volatility_window: 波动率计算窗口，默认20个tick
        """
        self.imb_threshold = imb_threshold
        self.min_depth = min_depth
        self.max_volatility = max_volatility
        self.volatility_window = volatility_window

        # 价格历史用于计算波动率
        self._price_buffer: deque = deque(maxlen=volatility_window)

        # IMB历史用于计算均线
        self._imb_buffer: deque = deque(maxlen=10)

    def calculate_imb(self, bid_volume: int, ask_volume: int) -> float:
        """
        计算IMB值

        公式: (BidVolume - AskVolume) / (BidVolume + AskVolume + 1)

        Args:
            bid_volume: 买一量
            ask_volume: 卖一量

        Returns:
            IMB值，范围[-1.0, 1.0]
        """
        return (bid_volume - ask_volume) / (bid_volume + ask_volume + 1)

    def calculate_volatility(self) -> float:
        """
        计算价格波动率 (20-tick滚动标准差)

        Returns:
            波动率值
        """
        if len(self._price_buffer) < 2:
            return 0.0

        prices = list(self._price_buffer)
        returns = np.diff(prices) / np.array(prices[:-1])
        return float(np.std(returns)) if len(returns) > 0 else 0.0

    def process_tick(self, tick_data: dict) -> IMBSignal:
        """
        处理tick数据，生成IMB信号

        Args:
            tick_data: CTP tick数据字典，需包含:
                - bid_price1, bid_volume1
                - ask_price1, ask_volume1
                - last_price
                - datetime

        Returns:
            IMBSignal信号数据
        """
        # 提取数据
        bid_price = tick_data.get('bid_price1', 0.0)
        bid_volume = tick_data.get('bid_volume1', 0)
        ask_price = tick_data.get('ask_price1', 0.0)
        ask_volume = tick_data.get('ask_volume1', 0)
        last_price = tick_data.get('last_price', 0.0)
        timestamp = tick_data.get('datetime', '')

        # 更新价格缓存
        if last_price > 0:
            self._price_buffer.append(last_price)

        # 计算IMB
        imb_value = self.calculate_imb(bid_volume, ask_volume)
        self._imb_buffer.append(imb_value)

        # 计算总深度
        total_depth = bid_volume + ask_volume

        # 计算波动率
        volatility = self.calculate_volatility()

        # 计算中间价
        mid_price = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else last_price

        # 检查信号条件
        signal_valid = self._check_signal_conditions(imb_value, total_depth, volatility)

        # 确定方向
        direction = 0
        if signal_valid:
            direction = 1 if imb_value > 0 else -1

        return IMBSignal(
            imb_value=imb_value,
            total_depth=total_depth,
            volatility=volatility,
            direction=direction,
            signal_valid=signal_valid,
            mid_price=mid_price,
            bid_price=bid_price,
            ask_price=ask_price,
            timestamp=timestamp
        )

    def _check_signal_conditions(self, imb: float, depth: int, volatility: float) -> bool:
        """
        检查信号条件

        条件:
        1. |IMB| > imb_threshold (0.8)
        2. depth >= min_depth (1500)
        3. volatility < max_volatility (0.00015)

        Args:
            imb: IMB值
            depth: 总深度
            volatility: 波动率

        Returns:
            是否满足信号条件
        """
        # 条件1: IMB超过阈值
        if abs(imb) <= self.imb_threshold:
            return False

        # 条件2: 深度足够
        if depth < self.min_depth:
            return False

        # 条件3: 波动率在限制内
        if volatility >= self.max_volatility:
            return False

        return True

    def get_imb_ma(self, period: int = 5) -> float:
        """
        获取IMB移动平均

        Args:
            period: 周期

        Returns:
            IMB移动平均值
        """
        if len(self._imb_buffer) < period:
            return 0.0
        return float(np.mean(list(self._imb_buffer)[-period:]))

    def get_signal_strength(self, imb: float) -> str:
        """
        获取信号强度

        Args:
            imb: IMB值

        Returns:
            强度: weak/medium/strong
        """
        abs_imb = abs(imb)
        if abs_imb >= 0.95:
            return "strong"
        elif abs_imb >= 0.9:
            return "medium"
        else:
            return "weak"

    def reset(self):
        """重置计算器状态"""
        self._price_buffer.clear()
        self._imb_buffer.clear()
