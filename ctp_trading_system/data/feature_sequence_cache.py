"""
特征序列缓存
来源: C:\Repo\future-trading-strategy\策略代码\LSTM_L2滑点回测.py

功能:
- 缓存最近10个时间步的68个特征
- 形成[10, 68]的特征矩阵用于LSTM输入
- 支持特征标准化
"""

from collections import deque
from typing import List, Dict, Optional, Any
import numpy as np


class FeatureSequenceCache:
    """
    特征序列缓存

    来源: LSTM_L2滑点回测.py

    功能:
    - 缓存最近10个时间步的68个特征
    - 形成[10, 68]的特征矩阵用于LSTM输入
    - 支持特征标准化
    """

    # 标准特征名列表 (68个)
    FEATURE_NAMES = [
        # 价格特征 (8)
        'return_1min', 'return_5min', 'return_15min', 'return_30min',
        'volatility_1min', 'volatility_5min', 'volatility_15min', 'volatility_30min',

        # 成交量特征 (8)
        'volume_sum', 'volume_mean', 'volume_std', 'volume_ratio',
        'turnover_sum', 'turnover_mean', 'vwap', 'vwap_distance',

        # 订单流特征 (12)
        'tick_imbalance', 'volume_imbalance', 'aggressive_buy_ratio', 'aggressive_sell_ratio',
        'net_aggressive_ratio', 'order_flow_intensity', 'buy_volume_pct', 'sell_volume_pct',
        'large_order_ratio', 'large_order_imbalance', 'order_arrival_rate', 'trade_intensity',

        # 冰山单特征 (8)
        'iceberg_imbalance', 'bid_iceberg_strength', 'ask_iceberg_strength',
        'has_bid_iceberg', 'has_ask_iceberg', 'bid_iceberg_count', 'ask_iceberg_count',
        'iceberg_pressure',

        # 大单特征 (6)
        'large_buy_count', 'large_sell_count', 'large_buy_volume', 'large_sell_volume',
        'large_net_volume', 'large_order_momentum',

        # 技术指标 (14)
        'rsi_14', 'rsi_7', 'ema_10', 'ema_30', 'ema_ratio',
        'momentum_5', 'momentum_10', 'momentum_20',
        'macd', 'macd_signal', 'macd_hist',
        'bollinger_upper', 'bollinger_lower', 'bollinger_pct',

        # 盘口特征 (8)
        'obi', 'spread', 'spread_pct', 'depth_ratio',
        'bid_depth_total', 'ask_depth_total', 'mid_price_change', 'price_vs_mid',

        # 滞后特征 (4)
        'return_lag1', 'return_lag2', 'return_lag3', 'imb_lag1'
    ]

    def __init__(self, sequence_length: int = 10, feature_dim: int = 68):
        """
        Args:
            sequence_length: 序列长度，默认10
            feature_dim: 特征维度，默认68
        """
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim
        self._buffer: deque = deque(maxlen=sequence_length)
        self._scaler: Any = None  # sklearn StandardScaler
        self._feature_names: List[str] = self.FEATURE_NAMES[:feature_dim]

    def set_scaler(self, scaler: Any):
        """
        设置标准化器 (从模型加载)

        Args:
            scaler: sklearn StandardScaler 实例
        """
        self._scaler = scaler

    def set_feature_names(self, names: List[str]):
        """
        设置特征名列表

        Args:
            names: 特征名列表
        """
        self._feature_names = names[:self.feature_dim]

    def add_features(self, features: Dict[str, float]):
        """
        添加一个时间步的特征

        Args:
            features: 特征字典 {feature_name: value}
        """
        # 按固定顺序提取特征
        feature_array = np.zeros(self.feature_dim)

        for i, name in enumerate(self._feature_names):
            if i >= self.feature_dim:
                break
            feature_array[i] = features.get(name, 0.0)

        self._buffer.append(feature_array)

    def add_feature_array(self, feature_array: np.ndarray):
        """
        直接添加特征数组

        Args:
            feature_array: 特征数组 (feature_dim,)
        """
        if len(feature_array) != self.feature_dim:
            # 补齐或截断
            padded = np.zeros(self.feature_dim)
            padded[:min(len(feature_array), self.feature_dim)] = feature_array[:self.feature_dim]
            feature_array = padded

        self._buffer.append(feature_array)

    def is_ready(self) -> bool:
        """是否有足够的序列长度"""
        return len(self._buffer) >= self.sequence_length

    def size(self) -> int:
        """当前缓存大小"""
        return len(self._buffer)

    def get_matrix(self) -> np.ndarray:
        """
        获取特征矩阵 [sequence_length, feature_dim]

        Returns:
            原始特征矩阵
        """
        if not self.is_ready():
            # 返回零矩阵
            return np.zeros((self.sequence_length, self.feature_dim))

        return np.array(list(self._buffer))

    def get_scaled_matrix(self) -> np.ndarray:
        """
        获取标准化后的特征矩阵

        Returns:
            标准化后的[sequence_length, feature_dim]矩阵
        """
        matrix = self.get_matrix()

        if self._scaler is not None:
            # 展平 -> 标准化 -> 重塑
            original_shape = matrix.shape
            flat = matrix.reshape(1, -1)

            try:
                scaled_flat = self._scaler.transform(flat)
                return scaled_flat.reshape(original_shape)
            except Exception as e:
                print(f"[FeatureSequenceCache] 标准化失败: {e}")
                return matrix

        return matrix

    def get_lstm_input(self) -> np.ndarray:
        """
        获取LSTM输入张量 [1, sequence_length, feature_dim]

        Returns:
            可直接输入LSTM的张量
        """
        matrix = self.get_scaled_matrix()
        return matrix.reshape(1, self.sequence_length, self.feature_dim)

    def get_feature_dict(self) -> Dict[str, List[float]]:
        """
        获取特征字典格式

        Returns:
            {feature_name: [value_t-9, ..., value_t]}
        """
        matrix = self.get_matrix()
        result = {}

        for i, name in enumerate(self._feature_names):
            if i >= self.feature_dim:
                break
            result[name] = matrix[:, i].tolist()

        return result

    def get_latest_features(self) -> Dict[str, float]:
        """
        获取最新一个时间步的特征

        Returns:
            特征字典
        """
        if len(self._buffer) == 0:
            return {name: 0.0 for name in self._feature_names}

        latest = self._buffer[-1]
        return {name: float(latest[i]) for i, name in enumerate(self._feature_names) if i < len(latest)}

    def clear(self):
        """清空缓存"""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return f"FeatureSequenceCache(size={len(self._buffer)}/{self.sequence_length}, dim={self.feature_dim})"
