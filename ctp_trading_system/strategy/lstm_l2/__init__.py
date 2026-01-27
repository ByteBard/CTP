"""
LSTM L2策略模块
深度学习订单簿分析策略

收益: +2,445.70% (16个月, 2,144笔交易)
胜率: ~84%
注: 2026-01-27 模型缓存更新后的结果
"""

from .lstm_strategy import LSTML2Strategy, LSTMConfig
from .feature_engine import FeatureEngine
from .position_manager import PositionManager, PositionConfig, PositionState

__all__ = ['LSTML2Strategy', 'LSTMConfig', 'FeatureEngine', 'PositionManager', 'PositionConfig', 'PositionState']
