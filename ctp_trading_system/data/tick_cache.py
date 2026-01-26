"""
实时Tick缓存
来源: C:\Repo\future-trading-strategy 的 order_flow_imbalance.py

功能:
- 缓存最近120个tick (约60秒，每500ms一个)
- 自动滚动窗口 (deque实现)
- 提取68个聚合特征用于策略计算
"""

from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import numpy as np


@dataclass
class TickData:
    """CTP Tick数据结构"""
    datetime: str = ""
    last_price: float = 0.0
    bid_price1: float = 0.0
    bid_volume1: int = 0
    ask_price1: float = 0.0
    ask_volume1: int = 0
    volume: int = 0
    turnover: float = 0.0
    open_interest: float = 0.0
    pre_close: float = 0.0
    upper_limit: float = 0.0
    lower_limit: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_ctp(cls, ctp_tick: dict) -> 'TickData':
        """从CTP行情数据创建"""
        return cls(
            datetime=ctp_tick.get('datetime', ''),
            last_price=ctp_tick.get('last_price', 0.0),
            bid_price1=ctp_tick.get('bid_price1', 0.0),
            bid_volume1=ctp_tick.get('bid_volume1', 0),
            ask_price1=ctp_tick.get('ask_price1', 0.0),
            ask_volume1=ctp_tick.get('ask_volume1', 0),
            volume=ctp_tick.get('volume', 0),
            turnover=ctp_tick.get('turnover', 0.0),
            open_interest=ctp_tick.get('open_interest', 0.0),
            pre_close=ctp_tick.get('pre_close', 0.0),
            upper_limit=ctp_tick.get('upper_limit', 0.0),
            lower_limit=ctp_tick.get('lower_limit', 0.0)
        )


class TickCache:
    """
    实时Tick缓存

    来源: order_flow_imbalance.py 的 IMB计算逻辑
    """

    def __init__(self, maxlen: int = 120):
        """
        Args:
            maxlen: 缓存最大长度，默认120个tick (~60秒)
        """
        self.maxlen = maxlen
        self._buffer: deque = deque(maxlen=maxlen)
        self._last_volume: int = 0

    def add_tick(self, tick: TickData):
        """添加tick到缓存"""
        self._buffer.append(tick)

    def add_from_ctp(self, ctp_tick: dict):
        """从CTP原始数据添加"""
        tick = TickData.from_ctp(ctp_tick)
        self.add_tick(tick)

    def is_ready(self) -> bool:
        """缓存是否已满"""
        return len(self._buffer) >= self.maxlen

    def size(self) -> int:
        """当前缓存大小"""
        return len(self._buffer)

    def __len__(self) -> int:
        """返回缓存大小"""
        return len(self._buffer)

    def get_ticks(self) -> List[TickData]:
        """获取所有缓存的tick"""
        return list(self._buffer)

    def get_latest(self) -> Optional[TickData]:
        """获取最新tick"""
        return self._buffer[-1] if self._buffer else None

    def calculate_imb(self) -> float:
        """
        计算IMB (订单流不平衡)

        来源: order_flow_imbalance.py
        IMB = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        Returns:
            IMB值，范围[-1, 1]
        """
        if len(self._buffer) < 2:
            return 0.0

        ticks = list(self._buffer)
        bid_vols = [t.bid_volume1 for t in ticks]
        ask_vols = [t.ask_volume1 for t in ticks]

        total_bid = sum(bid_vols)
        total_ask = sum(ask_vols)

        if total_bid + total_ask == 0:
            return 0.0

        return (total_bid - total_ask) / (total_bid + total_ask)

    def calculate_volatility(self) -> float:
        """
        计算价格波动率

        Returns:
            标准差波动率
        """
        if len(self._buffer) < 2:
            return 0.0

        prices = [t.last_price for t in self._buffer]
        returns = np.diff(prices) / np.array(prices[:-1])

        return float(np.std(returns)) if len(returns) > 0 else 0.0

    def extract_features(self) -> Dict[str, float]:
        """
        提取68个聚合特征

        特征分类:
        - 价格特征 (13个): OHLC, range, mean, std等
        - 成交量特征 (8个): sum, mean, std, VWAP等
        - L2深度特征 (25个): OBI, 盘口压力, 流动性等
        - 订单流特征 (10个): 买卖比, 净成交量等
        - 时间序列特征 (12个): 自相关, tick计数等
        """
        if not self.is_ready():
            return self._get_empty_features()

        ticks = list(self._buffer)
        prices = np.array([t.last_price for t in ticks])
        volumes = np.array([t.volume for t in ticks])
        bid_vols = np.array([t.bid_volume1 for t in ticks])
        ask_vols = np.array([t.ask_volume1 for t in ticks])
        bid_prices = np.array([t.bid_price1 for t in ticks])
        ask_prices = np.array([t.ask_price1 for t in ticks])

        features = {}

        # ========== A. 价格特征 (13个) ==========
        features['price_open'] = float(prices[0])
        features['price_high'] = float(np.max(prices))
        features['price_low'] = float(np.min(prices))
        features['price_close'] = float(prices[-1])
        features['price_mean'] = float(np.mean(prices))
        features['price_std'] = float(np.std(prices))
        features['price_range'] = float(np.max(prices) - np.min(prices))
        features['price_range_pct'] = features['price_range'] / features['price_mean'] if features['price_mean'] > 0 else 0

        # 价格变化
        returns = np.diff(prices) / prices[:-1]
        features['return_total'] = float((prices[-1] - prices[0]) / prices[0]) if prices[0] > 0 else 0
        features['return_mean'] = float(np.mean(returns)) if len(returns) > 0 else 0
        features['return_std'] = float(np.std(returns)) if len(returns) > 0 else 0
        features['return_skew'] = float(self._calc_skewness(returns)) if len(returns) > 2 else 0
        features['return_kurt'] = float(self._calc_kurtosis(returns)) if len(returns) > 3 else 0

        # ========== B. 成交量特征 (8个) ==========
        vol_diffs = np.diff(volumes)
        features['volume_sum'] = float(np.sum(vol_diffs)) if len(vol_diffs) > 0 else 0
        features['volume_mean'] = float(np.mean(vol_diffs)) if len(vol_diffs) > 0 else 0
        features['volume_std'] = float(np.std(vol_diffs)) if len(vol_diffs) > 0 else 0
        features['volume_max'] = float(np.max(vol_diffs)) if len(vol_diffs) > 0 else 0

        # VWAP
        if features['volume_sum'] > 0:
            features['vwap'] = float(np.sum(prices * vol_diffs) / features['volume_sum']) if len(vol_diffs) == len(prices) - 1 else prices[-1]
        else:
            features['vwap'] = float(prices[-1])
        features['vwap_distance'] = (features['price_close'] - features['vwap']) / features['vwap'] if features['vwap'] > 0 else 0
        features['volume_trend'] = float(np.mean(vol_diffs[-10:]) - np.mean(vol_diffs[:10])) if len(vol_diffs) >= 20 else 0
        features['volume_acceleration'] = float(np.mean(np.diff(vol_diffs[-10:]))) if len(vol_diffs) >= 11 else 0

        # ========== C. L2深度特征 (25个) ==========
        # IMB相关
        total_bid = float(np.sum(bid_vols))
        total_ask = float(np.sum(ask_vols))
        features['imb_mean'] = (total_bid - total_ask) / (total_bid + total_ask + 1)
        features['imb_last'] = (bid_vols[-1] - ask_vols[-1]) / (bid_vols[-1] + ask_vols[-1] + 1)

        # IMB序列统计
        imb_series = (bid_vols - ask_vols) / (bid_vols + ask_vols + 1)
        features['imb_std'] = float(np.std(imb_series))
        features['imb_max'] = float(np.max(imb_series))
        features['imb_min'] = float(np.min(imb_series))
        features['imb_range'] = features['imb_max'] - features['imb_min']

        # 盘口深度
        features['depth_total'] = total_bid + total_ask
        features['depth_bid'] = total_bid
        features['depth_ask'] = total_ask
        features['depth_ratio'] = total_bid / (total_ask + 1)

        # 盘口压力
        features['bid_pressure'] = float(np.mean(bid_vols[-10:])) if len(bid_vols) >= 10 else float(np.mean(bid_vols))
        features['ask_pressure'] = float(np.mean(ask_vols[-10:])) if len(ask_vols) >= 10 else float(np.mean(ask_vols))
        features['pressure_ratio'] = features['bid_pressure'] / (features['ask_pressure'] + 1)

        # 价差
        spreads = ask_prices - bid_prices
        features['spread_mean'] = float(np.mean(spreads))
        features['spread_std'] = float(np.std(spreads))
        features['spread_max'] = float(np.max(spreads))
        features['spread_min'] = float(np.min(spreads))

        # 中间价
        mid_prices = (bid_prices + ask_prices) / 2
        features['mid_price'] = float(mid_prices[-1])
        features['mid_price_std'] = float(np.std(mid_prices))
        features['price_vs_mid'] = (prices[-1] - mid_prices[-1]) / mid_prices[-1] if mid_prices[-1] > 0 else 0

        # 流动性
        features['liquidity_bid'] = float(np.mean(bid_vols * bid_prices))
        features['liquidity_ask'] = float(np.mean(ask_vols * ask_prices))
        features['liquidity_total'] = features['liquidity_bid'] + features['liquidity_ask']

        # ========== D. 订单流特征 (10个) ==========
        # 买卖方向推断 (tick rule)
        price_changes = np.diff(prices)
        up_ticks = np.sum(price_changes > 0)
        down_ticks = np.sum(price_changes < 0)
        features['tick_direction_ratio'] = up_ticks / (down_ticks + 1)
        features['net_tick_direction'] = up_ticks - down_ticks

        # 成交量方向
        features['buy_volume_est'] = float(np.sum(vol_diffs[price_changes > 0])) if len(vol_diffs) == len(price_changes) else 0
        features['sell_volume_est'] = float(np.sum(vol_diffs[price_changes < 0])) if len(vol_diffs) == len(price_changes) else 0
        features['net_volume'] = features['buy_volume_est'] - features['sell_volume_est']

        # 订单流强度
        features['order_flow_intensity'] = features['volume_sum'] / (self.maxlen + 1)
        features['order_flow_imbalance'] = features['net_volume'] / (features['volume_sum'] + 1)

        # 大单检测 (简化版)
        vol_threshold = features['volume_mean'] * 3 if features['volume_mean'] > 0 else 100
        large_orders = vol_diffs[vol_diffs > vol_threshold] if len(vol_diffs) > 0 else np.array([])
        features['large_order_count'] = len(large_orders)
        features['large_order_volume'] = float(np.sum(large_orders))

        # ========== E. 时间序列特征 (12个) ==========
        # 自相关
        features['price_autocorr_1'] = float(self._calc_autocorr(prices, 1))
        features['price_autocorr_5'] = float(self._calc_autocorr(prices, 5))
        features['volume_autocorr_1'] = float(self._calc_autocorr(vol_diffs, 1)) if len(vol_diffs) > 1 else 0

        # 趋势
        features['price_trend'] = float(np.polyfit(range(len(prices)), prices, 1)[0]) if len(prices) > 1 else 0
        features['volume_trend_slope'] = float(np.polyfit(range(len(vol_diffs)), vol_diffs, 1)[0]) if len(vol_diffs) > 1 else 0

        # 动量
        features['momentum_5'] = float(prices[-1] - prices[-5]) if len(prices) >= 5 else 0
        features['momentum_10'] = float(prices[-1] - prices[-10]) if len(prices) >= 10 else 0
        features['momentum_20'] = float(prices[-1] - prices[-20]) if len(prices) >= 20 else 0

        # 均值回归
        features['mean_reversion_signal'] = (features['price_close'] - features['price_mean']) / (features['price_std'] + 0.0001)

        # tick统计
        features['tick_count'] = float(len(ticks))
        features['zero_return_ratio'] = float(np.sum(returns == 0) / len(returns)) if len(returns) > 0 else 0
        features['positive_return_ratio'] = float(np.sum(returns > 0) / len(returns)) if len(returns) > 0 else 0

        return features

    def _get_empty_features(self) -> Dict[str, float]:
        """返回空特征字典"""
        feature_names = [
            'price_open', 'price_high', 'price_low', 'price_close', 'price_mean', 'price_std',
            'price_range', 'price_range_pct', 'return_total', 'return_mean', 'return_std',
            'return_skew', 'return_kurt', 'volume_sum', 'volume_mean', 'volume_std', 'volume_max',
            'vwap', 'vwap_distance', 'volume_trend', 'volume_acceleration', 'imb_mean', 'imb_last',
            'imb_std', 'imb_max', 'imb_min', 'imb_range', 'depth_total', 'depth_bid', 'depth_ask',
            'depth_ratio', 'bid_pressure', 'ask_pressure', 'pressure_ratio', 'spread_mean',
            'spread_std', 'spread_max', 'spread_min', 'mid_price', 'mid_price_std', 'price_vs_mid',
            'liquidity_bid', 'liquidity_ask', 'liquidity_total', 'tick_direction_ratio',
            'net_tick_direction', 'buy_volume_est', 'sell_volume_est', 'net_volume',
            'order_flow_intensity', 'order_flow_imbalance', 'large_order_count', 'large_order_volume',
            'price_autocorr_1', 'price_autocorr_5', 'volume_autocorr_1', 'price_trend',
            'volume_trend_slope', 'momentum_5', 'momentum_10', 'momentum_20', 'mean_reversion_signal',
            'tick_count', 'zero_return_ratio', 'positive_return_ratio'
        ]
        return {name: 0.0 for name in feature_names}

    def _calc_skewness(self, data: np.ndarray) -> float:
        """计算偏度"""
        if len(data) < 3:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 3))

    def _calc_kurtosis(self, data: np.ndarray) -> float:
        """计算峰度"""
        if len(data) < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 4) - 3)

    def _calc_autocorr(self, data: np.ndarray, lag: int) -> float:
        """计算自相关系数"""
        if len(data) <= lag:
            return 0.0
        return float(np.corrcoef(data[:-lag], data[lag:])[0, 1])

    def clear(self):
        """清空缓存"""
        self._buffer.clear()
        self._last_volume = 0
