"""
LSTM特征工程引擎
来源: L2滑点回测.py

生成18-93个特征用于LSTM预测:
- 基础特征 (10): OHLCV, RSI等
- 冰山单特征 (7): 买卖方冰山单检测
- 大单特征 (4): 大单检测
- 波动率特征 (7): 多时间窗口波动率
"""

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class BarData:
    """K线数据"""
    datetime: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0


class FeatureEngine:
    """
    LSTM特征工程引擎

    来源: L2滑点回测.py 的特征计算逻辑

    最佳配置 (18特征): 基础 + 冰山单 + 大单 + 波动率
    """

    # 18个核心特征名
    FEATURE_NAMES = [
        # 基础特征 (10)
        'open', 'high', 'low', 'close', 'volume',
        'return_1', 'return_5', 'return_10',
        'rsi_14', 'volume_ratio',

        # 冰山单特征 (7) - 需要L2数据
        'bid_iceberg_count', 'bid_iceberg_strength',
        'ask_iceberg_count', 'ask_iceberg_strength',
        'iceberg_imbalance', 'has_bid_iceberg', 'has_ask_iceberg',

        # 大单特征 (4) - 需要L2数据
        'large_buy_count', 'large_sell_count',
        'large_order_ratio', 'large_order_imbalance',

        # 波动率特征 (7)
        'volatility_5', 'volatility_15', 'volatility_30',
        'volatility_ratio', 'price_range_5', 'price_range_15', 'return_abs'
    ]

    def __init__(self, use_iceberg: bool = True, use_large_order: bool = True,
                 use_volatility: bool = True):
        """
        Args:
            use_iceberg: 是否使用冰山单特征
            use_large_order: 是否使用大单特征
            use_volatility: 是否使用波动率特征
        """
        self.use_iceberg = use_iceberg
        self.use_large_order = use_large_order
        self.use_volatility = use_volatility

        # Bar历史缓存
        self._bar_buffer: deque = deque(maxlen=60)
        self._close_buffer: deque = deque(maxlen=60)
        self._volume_buffer: deque = deque(maxlen=60)

        # L2数据缓存
        self._l2_buffer: deque = deque(maxlen=100)

    def add_bar(self, bar: BarData):
        """添加K线数据"""
        self._bar_buffer.append(bar)
        self._close_buffer.append(bar.close)
        self._volume_buffer.append(bar.volume)

    def add_bar_from_dict(self, bar_dict: dict):
        """从字典添加K线"""
        bar = BarData(
            datetime=bar_dict.get('datetime', ''),
            open=bar_dict.get('open', 0),
            high=bar_dict.get('high', 0),
            low=bar_dict.get('low', 0),
            close=bar_dict.get('close', 0),
            volume=bar_dict.get('volume', 0),
            turnover=bar_dict.get('turnover', 0),
            open_interest=bar_dict.get('open_interest', 0)
        )
        self.add_bar(bar)

    def add_l2_data(self, l2_data: dict):
        """添加L2盘口数据"""
        self._l2_buffer.append(l2_data)

    def is_ready(self, min_bars: int = 15) -> bool:
        """是否有足够的数据"""
        return len(self._bar_buffer) >= min_bars

    def calculate_features(self) -> Dict[str, float]:
        """
        计算所有特征

        Returns:
            特征字典 {feature_name: value}
        """
        if not self.is_ready():
            return self._get_empty_features()

        features = {}

        # 基础特征
        features.update(self._calc_base_features())

        # 冰山单特征
        if self.use_iceberg:
            features.update(self._calc_iceberg_features())

        # 大单特征
        if self.use_large_order:
            features.update(self._calc_large_order_features())

        # 波动率特征
        if self.use_volatility:
            features.update(self._calc_volatility_features())

        return features

    def _calc_base_features(self) -> Dict[str, float]:
        """计算基础特征 (10个)"""
        features = {}
        bars = list(self._bar_buffer)
        closes = list(self._close_buffer)
        volumes = list(self._volume_buffer)

        if not bars:
            return features

        latest = bars[-1]

        # OHLCV
        features['open'] = latest.open
        features['high'] = latest.high
        features['low'] = latest.low
        features['close'] = latest.close
        features['volume'] = float(latest.volume)

        # 收益率
        if len(closes) >= 2:
            features['return_1'] = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] > 0 else 0
        else:
            features['return_1'] = 0

        if len(closes) >= 6:
            features['return_5'] = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] > 0 else 0
        else:
            features['return_5'] = 0

        if len(closes) >= 11:
            features['return_10'] = (closes[-1] - closes[-11]) / closes[-11] if closes[-11] > 0 else 0
        else:
            features['return_10'] = 0

        # RSI
        features['rsi_14'] = self._calc_rsi(closes, 14)

        # 成交量比
        if len(volumes) >= 20:
            avg_vol = np.mean(list(volumes)[-20:])
            features['volume_ratio'] = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        else:
            features['volume_ratio'] = 1.0

        return features

    def _calc_iceberg_features(self) -> Dict[str, float]:
        """
        计算冰山单特征 (7个)

        来源: iceberg_detection.py
        """
        features = {
            'bid_iceberg_count': 0,
            'bid_iceberg_strength': 0.0,
            'ask_iceberg_count': 0,
            'ask_iceberg_strength': 0.0,
            'iceberg_imbalance': 0.0,
            'has_bid_iceberg': 0,
            'has_ask_iceberg': 0
        }

        if len(self._l2_buffer) < 10:
            return features

        recent_l2 = list(self._l2_buffer)[-10:]

        # 分析买卖盘变化模式检测冰山单
        bid_vols = [d.get('bid_volume1', 0) for d in recent_l2]
        ask_vols = [d.get('ask_volume1', 0) for d in recent_l2]

        # 冰山单检测: 量突然减少又恢复
        bid_drops = 0
        ask_drops = 0

        for i in range(1, len(bid_vols) - 1):
            if bid_vols[i] < bid_vols[i-1] * 0.5 and bid_vols[i+1] > bid_vols[i] * 1.5:
                bid_drops += 1
            if ask_vols[i] < ask_vols[i-1] * 0.5 and ask_vols[i+1] > ask_vols[i] * 1.5:
                ask_drops += 1

        features['bid_iceberg_count'] = bid_drops
        features['ask_iceberg_count'] = ask_drops
        features['has_bid_iceberg'] = 1 if bid_drops > 0 else 0
        features['has_ask_iceberg'] = 1 if ask_drops > 0 else 0

        # 冰山单强度
        bid_std = np.std(bid_vols) if bid_vols else 0
        ask_std = np.std(ask_vols) if ask_vols else 0
        bid_mean = np.mean(bid_vols) if bid_vols else 1
        ask_mean = np.mean(ask_vols) if ask_vols else 1

        features['bid_iceberg_strength'] = bid_std / (bid_mean + 1)
        features['ask_iceberg_strength'] = ask_std / (ask_mean + 1)
        features['iceberg_imbalance'] = features['bid_iceberg_strength'] - features['ask_iceberg_strength']

        return features

    def _calc_large_order_features(self) -> Dict[str, float]:
        """
        计算大单特征 (4个)

        来源: large_order_detection.py
        """
        features = {
            'large_buy_count': 0,
            'large_sell_count': 0,
            'large_order_ratio': 0.0,
            'large_order_imbalance': 0.0
        }

        if len(self._l2_buffer) < 20:
            return features

        recent_l2 = list(self._l2_buffer)[-20:]

        # 计算平均成交量
        volumes = [d.get('volume', 0) for d in recent_l2]
        if not volumes:
            return features

        avg_vol = np.mean(volumes)
        large_threshold = avg_vol * 3  # 3倍均量为大单

        # 统计大单
        large_buys = 0
        large_sells = 0
        total_large = 0

        for i in range(1, len(recent_l2)):
            vol_delta = volumes[i] - volumes[i-1]
            if vol_delta > large_threshold:
                price_change = recent_l2[i].get('last_price', 0) - recent_l2[i-1].get('last_price', 0)
                if price_change > 0:
                    large_buys += 1
                else:
                    large_sells += 1
                total_large += 1

        features['large_buy_count'] = large_buys
        features['large_sell_count'] = large_sells
        features['large_order_ratio'] = total_large / len(recent_l2) if recent_l2 else 0

        total = large_buys + large_sells
        if total > 0:
            features['large_order_imbalance'] = (large_buys - large_sells) / total
        else:
            features['large_order_imbalance'] = 0

        return features

    def _calc_volatility_features(self) -> Dict[str, float]:
        """
        计算波动率特征 (7个)

        来源: volatility_estimation.py
        """
        features = {
            'volatility_5': 0.0,
            'volatility_15': 0.0,
            'volatility_30': 0.0,
            'volatility_ratio': 1.0,
            'price_range_5': 0.0,
            'price_range_15': 0.0,
            'return_abs': 0.0
        }

        closes = list(self._close_buffer)
        bars = list(self._bar_buffer)

        if len(closes) < 5:
            return features

        # 计算收益率序列
        returns = np.diff(closes) / np.array(closes[:-1])

        # 不同窗口波动率
        if len(returns) >= 5:
            features['volatility_5'] = float(np.std(returns[-5:]))
        if len(returns) >= 15:
            features['volatility_15'] = float(np.std(returns[-15:]))
        if len(returns) >= 30:
            features['volatility_30'] = float(np.std(returns[-30:]))

        # 波动率比
        if features['volatility_15'] > 0:
            features['volatility_ratio'] = features['volatility_5'] / features['volatility_15']

        # 价格范围
        if len(bars) >= 5:
            highs = [b.high for b in bars[-5:]]
            lows = [b.low for b in bars[-5:]]
            features['price_range_5'] = (max(highs) - min(lows)) / closes[-1] if closes[-1] > 0 else 0

        if len(bars) >= 15:
            highs = [b.high for b in bars[-15:]]
            lows = [b.low for b in bars[-15:]]
            features['price_range_15'] = (max(highs) - min(lows)) / closes[-1] if closes[-1] > 0 else 0

        # 绝对收益
        if len(returns) > 0:
            features['return_abs'] = abs(returns[-1])

        return features

    def _calc_rsi(self, prices: list, period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50.0

        prices = np.array(prices)
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _get_empty_features(self) -> Dict[str, float]:
        """返回空特征字典"""
        return {name: 0.0 for name in self.FEATURE_NAMES}

    def get_feature_names(self) -> List[str]:
        """获取特征名列表"""
        names = self.FEATURE_NAMES[:10]  # 基础10个

        if self.use_iceberg:
            names.extend(self.FEATURE_NAMES[10:17])  # 冰山单7个

        if self.use_large_order:
            names.extend(self.FEATURE_NAMES[17:21])  # 大单4个

        if self.use_volatility:
            names.extend(self.FEATURE_NAMES[21:28])  # 波动率7个

        return names

    def clear(self):
        """清空缓存"""
        self._bar_buffer.clear()
        self._close_buffer.clear()
        self._volume_buffer.clear()
        self._l2_buffer.clear()
