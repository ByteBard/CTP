"""
L2盘口深度缓存
来源: C:\Repo\future-trading-strategy 的 iceberg_detection.py

功能:
- 缓存最新5档盘口数据
- 计算订单簿不平衡 (OBI)
- 检测冰山单/大单
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
import numpy as np


@dataclass
class L2Depth:
    """L2深度数据 (5档)"""
    bid_prices: List[float] = field(default_factory=list)
    bid_volumes: List[int] = field(default_factory=list)
    ask_prices: List[float] = field(default_factory=list)
    ask_volumes: List[int] = field(default_factory=list)
    timestamp_ms: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_ctp(cls, tick_data: dict) -> 'L2Depth':
        """
        从CTP tick数据创建L2深度
        注: CTP仅提供1档，这里兼容处理
        """
        bid_prices = []
        bid_volumes = []
        ask_prices = []
        ask_volumes = []

        # 尝试获取5档数据
        for i in range(1, 6):
            bp = tick_data.get(f'bid_price{i}', 0)
            bv = tick_data.get(f'bid_volume{i}', 0)
            ap = tick_data.get(f'ask_price{i}', 0)
            av = tick_data.get(f'ask_volume{i}', 0)

            if bp > 0:
                bid_prices.append(bp)
                bid_volumes.append(bv)
            if ap > 0:
                ask_prices.append(ap)
                ask_volumes.append(av)

        # 如果只有1档，补充
        if len(bid_prices) == 0 and tick_data.get('bid_price1', 0) > 0:
            bid_prices = [tick_data.get('bid_price1', 0)]
            bid_volumes = [tick_data.get('bid_volume1', 0)]

        if len(ask_prices) == 0 and tick_data.get('ask_price1', 0) > 0:
            ask_prices = [tick_data.get('ask_price1', 0)]
            ask_volumes = [tick_data.get('ask_volume1', 0)]

        return cls(
            bid_prices=bid_prices,
            bid_volumes=bid_volumes,
            ask_prices=ask_prices,
            ask_volumes=ask_volumes,
            timestamp_ms=int(tick_data.get('timestamp', 0) * 1000) if 'timestamp' in tick_data else 0
        )


class L2DepthBuffer:
    """
    L2深度缓存

    来源: iceberg_detection.py

    功能:
    - 缓存最新5档盘口数据
    - 计算订单簿不平衡 (OBI)
    - 检测冰山单/大单
    """

    def __init__(self, max_history: int = 100):
        """
        Args:
            max_history: 历史快照最大数量
        """
        self._current_depth: Optional[L2Depth] = None
        self._depth_history: List[L2Depth] = []
        self._max_history = max_history

        # 冰山单检测参数
        self._iceberg_threshold = 0.5  # 波动阈值
        self._large_order_multiplier = 3.0  # 大单判定倍数

    def update(self, depth: L2Depth):
        """更新最新盘口"""
        self._current_depth = depth
        self._depth_history.append(depth)
        if len(self._depth_history) > self._max_history:
            self._depth_history.pop(0)

    def update_from_tick(self, tick_data: dict):
        """从tick数据更新"""
        depth = L2Depth.from_ctp(tick_data)
        self.update(depth)

    def get_obi(self) -> float:
        """
        计算订单簿不平衡 (Order Book Imbalance)

        OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)

        Returns:
            OBI值，范围[-1, 1]
        """
        if not self._current_depth:
            return 0.0

        bid_vol = sum(self._current_depth.bid_volumes)
        ask_vol = sum(self._current_depth.ask_volumes)

        if bid_vol + ask_vol == 0:
            return 0.0

        return (bid_vol - ask_vol) / (bid_vol + ask_vol)

    def get_spread(self) -> float:
        """
        计算买卖价差

        Returns:
            价差 (ask1 - bid1)
        """
        if not self._current_depth:
            return 0.0

        if not self._current_depth.ask_prices or not self._current_depth.bid_prices:
            return 0.0

        return self._current_depth.ask_prices[0] - self._current_depth.bid_prices[0]

    def get_mid_price(self) -> float:
        """
        计算中间价

        Returns:
            中间价 (ask1 + bid1) / 2
        """
        if not self._current_depth:
            return 0.0

        if not self._current_depth.ask_prices or not self._current_depth.bid_prices:
            return 0.0

        return (self._current_depth.ask_prices[0] + self._current_depth.bid_prices[0]) / 2

    def detect_iceberg(self) -> Dict[str, any]:
        """
        检测冰山单

        来源: iceberg_detection.py

        检测逻辑:
        - 盘口显示量小，但连续成交量大
        - 多次相同价位的小单挂单

        Returns:
            冰山单检测结果字典
        """
        if len(self._depth_history) < 10:
            return {
                'has_bid_iceberg': False,
                'has_ask_iceberg': False,
                'bid_iceberg_strength': 0.0,
                'ask_iceberg_strength': 0.0,
                'bid_iceberg_count': 0,
                'ask_iceberg_count': 0
            }

        recent_depths = self._depth_history[-10:]

        bid_vols = [sum(d.bid_volumes) for d in recent_depths]
        ask_vols = [sum(d.ask_volumes) for d in recent_depths]

        bid_mean = np.mean(bid_vols) if bid_vols else 0
        ask_mean = np.mean(ask_vols) if ask_vols else 0
        bid_std = np.std(bid_vols) if len(bid_vols) > 1 else 0
        ask_std = np.std(ask_vols) if len(ask_vols) > 1 else 0

        # 波动大可能有冰山单
        has_bid_iceberg = bid_std > bid_mean * self._iceberg_threshold if bid_mean > 0 else False
        has_ask_iceberg = ask_std > ask_mean * self._iceberg_threshold if ask_mean > 0 else False

        # 计算强度
        bid_strength = bid_std / (bid_mean + 1) if bid_mean > 0 else 0
        ask_strength = ask_std / (ask_mean + 1) if ask_mean > 0 else 0

        # 统计冰山单次数 (量突然减少又恢复)
        bid_iceberg_count = 0
        ask_iceberg_count = 0

        for i in range(1, len(bid_vols) - 1):
            # 量突然减少50%以上，然后恢复
            if bid_vols[i] < bid_vols[i-1] * 0.5 and bid_vols[i+1] > bid_vols[i] * 1.5:
                bid_iceberg_count += 1
            if ask_vols[i] < ask_vols[i-1] * 0.5 and ask_vols[i+1] > ask_vols[i] * 1.5:
                ask_iceberg_count += 1

        return {
            'has_bid_iceberg': has_bid_iceberg,
            'has_ask_iceberg': has_ask_iceberg,
            'bid_iceberg_strength': float(bid_strength),
            'ask_iceberg_strength': float(ask_strength),
            'bid_iceberg_count': bid_iceberg_count,
            'ask_iceberg_count': ask_iceberg_count
        }

    def detect_large_order(self) -> Dict[str, any]:
        """
        检测大单

        来源: large_order_detection.py

        Returns:
            大单检测结果字典
        """
        if len(self._depth_history) < 20:
            return {
                'has_large_bid': False,
                'has_large_ask': False,
                'large_bid_volume': 0,
                'large_ask_volume': 0,
                'large_order_imbalance': 0.0
            }

        recent_depths = self._depth_history[-20:]

        # 计算历史均值
        bid_vols = [sum(d.bid_volumes) for d in recent_depths[:-1]]
        ask_vols = [sum(d.ask_volumes) for d in recent_depths[:-1]]

        bid_mean = np.mean(bid_vols) if bid_vols else 0
        ask_mean = np.mean(ask_vols) if ask_vols else 0

        # 当前量
        current_bid = sum(self._current_depth.bid_volumes) if self._current_depth else 0
        current_ask = sum(self._current_depth.ask_volumes) if self._current_depth else 0

        # 大单判定
        threshold_bid = bid_mean * self._large_order_multiplier
        threshold_ask = ask_mean * self._large_order_multiplier

        has_large_bid = current_bid > threshold_bid if threshold_bid > 0 else False
        has_large_ask = current_ask > threshold_ask if threshold_ask > 0 else False

        # 计算不平衡
        total = current_bid + current_ask
        imbalance = (current_bid - current_ask) / total if total > 0 else 0

        return {
            'has_large_bid': has_large_bid,
            'has_large_ask': has_large_ask,
            'large_bid_volume': current_bid if has_large_bid else 0,
            'large_ask_volume': current_ask if has_large_ask else 0,
            'large_order_imbalance': float(imbalance)
        }

    def get_features(self) -> Dict[str, float]:
        """
        获取L2深度特征

        Returns:
            特征字典
        """
        features = {}

        # 基础特征
        features['obi'] = self.get_obi()
        features['spread'] = self.get_spread()
        features['mid_price'] = self.get_mid_price()

        # 冰山单特征
        iceberg = self.detect_iceberg()
        features['has_bid_iceberg'] = float(iceberg['has_bid_iceberg'])
        features['has_ask_iceberg'] = float(iceberg['has_ask_iceberg'])
        features['bid_iceberg_strength'] = iceberg['bid_iceberg_strength']
        features['ask_iceberg_strength'] = iceberg['ask_iceberg_strength']
        features['iceberg_imbalance'] = features['bid_iceberg_strength'] - features['ask_iceberg_strength']

        # 大单特征
        large = self.detect_large_order()
        features['has_large_bid'] = float(large['has_large_bid'])
        features['has_large_ask'] = float(large['has_large_ask'])
        features['large_order_imbalance'] = large['large_order_imbalance']

        # 深度特征
        if self._current_depth:
            features['bid_depth_total'] = float(sum(self._current_depth.bid_volumes))
            features['ask_depth_total'] = float(sum(self._current_depth.ask_volumes))
            features['depth_ratio'] = features['bid_depth_total'] / (features['ask_depth_total'] + 1)
        else:
            features['bid_depth_total'] = 0.0
            features['ask_depth_total'] = 0.0
            features['depth_ratio'] = 1.0

        return features

    def get_snapshot(self) -> Optional[L2Depth]:
        """获取当前快照"""
        return self._current_depth

    def clear(self):
        """清空缓存"""
        self._current_depth = None
        self._depth_history.clear()
