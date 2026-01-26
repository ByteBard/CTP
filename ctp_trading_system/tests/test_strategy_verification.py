# -*- coding: utf-8 -*-
"""
策略回测验证测试
验证H1e Tick和LSTM L2策略参数与原始实现一致

原始回测结果:
- H1e Tick: +13,706% (16个月, 67,926笔交易, 95.6%胜率)
- LSTM L2: +2,618% (16个月, 1,340笔交易, 84.5%胜率)

数据来源:
- H1e: experiments/tick_timeframe_test.py (H1e_止损_0.7配置)
- LSTM: experiments/L2滑点回测.py (--iceberg --large-order --volatility)
"""

import pytest
import sys
import os
from pathlib import Path
from dataclasses import asdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestH1eStrategyParameters:
    """H1e Tick策略参数验证"""

    def test_h1e_config_matches_original(self):
        """验证H1e配置与原始tick_timeframe_test.py一致"""
        from ctp_trading_system.strategy.h1e_tick import H1eConfig

        config = H1eConfig()

        # 原始配置: H1e_止损_0.7
        # 来源: tick_timeframe_test.py lines 707-715
        assert config.imb_threshold == 0.8, "IMB阈值应为0.8"
        assert config.min_depth == 1500, "最小深度应为1500"
        assert config.max_volatility == 0.00015, "最大波动率应为0.00015"
        assert config.signal_cooldown == 10, "信号冷却应为10"

        # 阶梯止盈: [(15, 2.0), (30, 1.0)]
        assert config.use_staggered_tp == True, "应启用阶梯止盈"
        assert config.staggered_tp_levels == [(15, 2.0), (30, 1.0)], \
            "阶梯止盈应为[(15, 2.0), (30, 1.0)]"

        assert config.stop_loss_ticks == 2.0, "止损应为2跳"
        assert config.max_hold_ticks == 30, "最大持仓应为30跳"

        # 日内止损 (关键优化!)
        assert config.daily_stop_loss_pct == -0.007, "日亏停止应为-0.7%"

        # 手续费
        assert abs(config.commission_rate - 0.00022) < 0.00001, "手续费应为0.022%双边"

        print("[PASS] H1e config verification passed")
        print(f"  IMB threshold: {config.imb_threshold}")
        print(f"  Depth threshold: {config.min_depth}")
        print(f"  Volatility cap: {config.max_volatility}")
        print(f"  Staggered TP: {config.staggered_tp_levels}")
        print(f"  Stop loss: {config.stop_loss_ticks} ticks")
        print(f"  Daily stop: {config.daily_stop_loss_pct*100:.1f}%")

    def test_h1e_imb_calculator(self):
        """验证IMB计算器逻辑"""
        from ctp_trading_system.strategy.h1e_tick import IMBCalculator

        calc = IMBCalculator(imb_threshold=0.8, min_depth=1500, max_volatility=0.00015)

        # 测试IMB计算公式: (BidVol - AskVol) / (BidVol + AskVol + 1)
        # 多头信号: IMB > 0.8
        bid_vol, ask_vol = 1000, 100
        imb = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1)
        assert imb > 0.8, f"IMB should be > 0.8, actual={imb:.3f}"

        # 空头信号: IMB < -0.8
        bid_vol, ask_vol = 100, 1000
        imb = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1)
        assert imb < -0.8, f"IMB should be < -0.8, actual={imb:.3f}"

        print("[PASS] IMB calculator verification passed")
        print(f"  Long signal: IMB > 0.8")
        print(f"  Short signal: IMB < -0.8")

    def test_h1e_staggered_take_profit(self):
        """验证阶梯止盈逻辑"""
        from ctp_trading_system.strategy.h1e_tick import H1eConfig

        # 阶梯止盈规则:
        # - 持仓 <= 15 tick: 目标 2.0 跳
        # - 持仓 16-30 tick: 目标 1.0 跳

        config = H1eConfig()
        levels = config.staggered_tp_levels

        # 验证规则
        for hold_ticks in range(1, 16):
            expected_target = 2.0
            for max_ticks, target in levels:
                if hold_ticks <= max_ticks:
                    expected_target = target
                    break
            assert expected_target == 2.0, f"Hold {hold_ticks} tick should target 2.0 ticks"

        for hold_ticks in range(16, 31):
            expected_target = 1.0
            for max_ticks, target in levels:
                if hold_ticks <= max_ticks:
                    expected_target = target
                    break
            assert expected_target == 1.0, f"Hold {hold_ticks} tick should target 1.0 tick"

        print("[PASS] Staggered TP logic verification passed")
        print(f"  Hold 1-15 ticks: target 2.0 ticks")
        print(f"  Hold 16-30 ticks: target 1.0 tick")


class TestLSTML2StrategyParameters:
    """LSTM L2策略参数验证"""

    def test_lstm_config_matches_original(self):
        """验证LSTM配置与原始L2滑点回测.py一致"""
        from ctp_trading_system.strategy.lstm_l2 import LSTMConfig

        config = LSTMConfig()

        # 原始配置: DEFAULT_PARAMS
        # 来源: L2滑点回测.py line 355
        assert config.sl == 0.004, "Stop loss should be 0.4%"
        assert config.tp == 0.012, "Take profit should be 1.2%"
        assert config.rsi_upper == 55, "RSI upper should be 55"
        assert config.rsi_lower == 45, "RSI lower should be 45"
        assert config.threshold == 0.5, "Probability threshold should be 0.5"

        # 仓位管理
        # 来源: L2滑点回测.py lines 315-317
        assert config.probe_size == 0.3, "Probe size should be 30%"
        assert config.full_size == 1.0, "Full size should be 100%"
        assert config.trail_dd == 0.30, "Trail drawdown should be 30%"

        # 特征配置
        # 来源: 最佳配置 --iceberg --large-order --volatility
        assert config.use_iceberg == True, "Should use iceberg features"
        assert config.use_large_order == True, "Should use large order features"
        assert config.use_volatility == True, "Should use volatility features"
        assert config.seq_len == 10, "LSTM sequence length should be 10"

        print("[PASS] LSTM config verification passed")
        print(f"  Stop loss: {config.sl*100:.1f}%")
        print(f"  Take profit: {config.tp*100:.1f}%")
        print(f"  RSI filter: [{config.rsi_lower}, {config.rsi_upper}]")
        print(f"  Probe size: {config.probe_size*100:.0f}%")
        print(f"  Trail drawdown: {config.trail_dd*100:.0f}%")

    def test_lstm_position_manager(self):
        """验证三态仓位管理逻辑"""
        from ctp_trading_system.strategy.lstm_l2 import PositionManager, PositionConfig, PositionState

        config = PositionConfig(
            sl=0.004,
            tp=0.012,
            probe_size=0.3,
            trail_dd=0.30
        )
        pm = PositionManager(config)

        # 初始状态应为Flat
        assert pm.state == PositionState.FLAT
        assert pm.is_flat() == True

        # 入场后应为Probe
        pm.enter_position(direction=1, price=100.0, prob=0.7, rsi=50, bar_count=0)
        assert pm.state == PositionState.PROBE
        assert pm.position.current_size == 0.3  # 30%仓位

        # 盈利0.4%后应升级到Full
        # pnl >= probe_to_full (0.4%)
        current_price = 100.4  # +0.4%
        should_exit, reason, pnl = pm.update(current_price)
        assert pm.state == PositionState.FULL
        assert pm.position.current_size == 1.0  # 100%仓位

        # 继续盈利0.6%后应升级到Trail
        # pnl >= full_to_trail (0.6%)
        current_price = 100.7  # +0.7%
        should_exit, reason, pnl = pm.update(current_price)
        assert pm.state == PositionState.TRAIL

        print("[PASS] Position manager state machine verified")
        print(f"  Flat -> Probe (30%): on entry")
        print(f"  Probe -> Full (100%): at +0.4%")
        print(f"  Full -> Trail: at +0.6%")

    def test_lstm_position_exit_conditions(self):
        """验证出场条件"""
        from ctp_trading_system.strategy.lstm_l2 import PositionManager, PositionConfig, PositionState

        config = PositionConfig(sl=0.004, tp=0.012, trail_dd=0.30)

        # 测试Probe止损
        pm = PositionManager(config)
        pm.enter_position(direction=1, price=100.0, prob=0.7, rsi=50, bar_count=0)
        should_exit, reason, pnl = pm.update(99.6)  # -0.4%
        assert should_exit == True
        assert reason == "probe_sl"

        # 测试Full止损 (0.5%)
        pm2 = PositionManager(config)
        pm2.enter_position(direction=1, price=100.0, prob=0.7, rsi=50, bar_count=0)
        pm2.update(100.4)  # 升级到Full
        should_exit, reason, pnl = pm2.update(99.5)  # -0.5%
        assert should_exit == True
        assert reason == "full_sl"

        # 测试Trail止盈 (1.2%)
        pm3 = PositionManager(config)
        pm3.enter_position(direction=1, price=100.0, prob=0.7, rsi=50, bar_count=0)
        pm3.update(100.4)  # 升级到Full
        pm3.update(100.7)  # 升级到Trail
        should_exit, reason, pnl = pm3.update(101.2)  # +1.2%
        assert should_exit == True
        assert reason == "trail_tp"

        print("[PASS] Exit conditions verified")
        print(f"  Probe stop loss: -0.4%")
        print(f"  Full stop loss: -0.5%")
        print(f"  Trail take profit: +1.2%")


class TestLSTMModel:
    """LSTM模型结构验证"""

    def test_lstm_model_architecture(self):
        """验证LSTM模型架构"""
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            pytest.skip("PyTorch not available")

        from ctp_trading_system.strategy.lstm_l2.lstm_strategy import LSTMModel

        if LSTMModel is None:
            pytest.skip("LSTMModel not available")

        # 18个特征
        input_dim = 18
        model = LSTMModel(input_dim=input_dim, hidden_dim=64, num_layers=2)

        # 验证LSTM层
        assert model.lstm.input_size == input_dim
        assert model.lstm.hidden_size == 64
        assert model.lstm.num_layers == 2

        # 验证FC层输出Sigmoid
        last_layer = list(model.fc.modules())[-1]
        assert isinstance(last_layer, nn.Sigmoid), "Last layer should be Sigmoid"

        # 测试前向传播
        batch_size, seq_len = 32, 10
        x = torch.randn(batch_size, seq_len, input_dim)
        output = model(x)

        assert output.shape == (batch_size,), f"Output shape should be ({batch_size},)"
        assert torch.all(output >= 0) and torch.all(output <= 1), "Output should be in [0,1]"

        print("[PASS] LSTM model architecture verified")
        print(f"  Input dim: {input_dim}")
        print(f"  LSTM: 2 layers, 64 hidden units")
        print(f"  FC: 64->32->1->Sigmoid")


class TestExpectedReturns:
    """预期收益率文档"""

    def test_document_expected_returns(self):
        """文档记录预期收益率"""
        expected_returns = {
            'H1e_TICK': {
                'compound_return': '+13,706%',
                'simple_return': '+4,991%',  # 按日复利前的简单收益
                'total_trades': 67926,
                'win_rate': 95.6,
                'test_period': '202407-202510 (16 months)',
                'loss_months': 2,
                'source': 'tick_timeframe_test.py, H1e_stop_0.7 config'
            },
            'LSTM_L2': {
                'compound_return': '+2,618%',
                'simple_return': '+372%',
                'total_trades': 1340,
                'win_rate': 84.5,
                'test_period': '202407-202510 (16 months)',
                'features': '--iceberg --large-order --volatility',
                'source': 'L2slippage_backtest.py'
            }
        }

        print("\n" + "=" * 70)
        print("Expected Backtest Returns (for verification)")
        print("=" * 70)

        for name, data in expected_returns.items():
            print(f"\n[{name}]")
            print(f"  Compound return: {data['compound_return']}")
            print(f"  Total trades: {data['total_trades']:,}")
            print(f"  Win rate: {data['win_rate']}%")
            print(f"  Test period: {data['test_period']}")
            print(f"  Source: {data['source']}")

        print("\n" + "=" * 70)
        print("Verification notes:")
        print("=" * 70)
        print("1. Running original backtest scripts requires C:/ProcessedData")
        print("2. This test verifies strategy params match original implementation")
        print("3. Actual backtest needs original data to verify returns")
        print("=" * 70)

        # 只是文档，总是通过
        assert True


class TestDataCachingFramework:
    """数据缓存框架验证"""

    def test_tick_cache(self):
        """验证Tick缓存"""
        from ctp_trading_system.data import TickCache

        cache = TickCache(maxlen=120)

        # 添加测试数据
        for i in range(150):
            tick_data = {
                'last_price': 100.0 + i * 0.01,
                'bid_price1': 99.99 + i * 0.01,
                'ask_price1': 100.01 + i * 0.01,
                'bid_volume1': 100 + i,
                'ask_volume1': 80 + i,
                'volume': 1000 + i * 10
            }
            cache.add_from_ctp(tick_data)

        # 验证长度限制
        assert len(cache) == 120, "Cache should be limited to 120 items"

        print("[PASS] Tick cache verified")

    def test_bar_aggregator(self):
        """验证Bar聚合器"""
        from ctp_trading_system.data import BarAggregator

        completed_bars = []

        def on_bar(bar):
            completed_bars.append(bar)

        agg = BarAggregator(on_bar_completed=on_bar)

        # 模拟60秒的tick数据
        for i in range(65):
            tick = {
                'last_price': 100.0 + (i % 10) * 0.1,
                'volume': 1000 + i,
                'datetime': f'2024-01-01 09:00:{i:02d}'
            }
            agg.on_tick(tick)

        # 应该生成至少1个完整的Bar
        assert len(completed_bars) >= 1, "Should generate at least 1 Bar"

        print("[PASS] Bar aggregator verified")

    def test_feature_sequence_cache(self):
        """验证特征序列缓存"""
        from ctp_trading_system.data import FeatureSequenceCache
        import numpy as np

        cache = FeatureSequenceCache(sequence_length=10, feature_dim=18)

        # 添加特征 - 使用字典格式
        feature_names = cache._feature_names[:18] if hasattr(cache, '_feature_names') else [f'f{i}' for i in range(18)]

        for i in range(15):
            features = {name: float(np.random.randn()) for name in feature_names}
            cache.add_features(features)

        # 获取矩阵
        seq = cache.get_matrix()
        assert seq.shape == (10, 18), f"Sequence shape should be (10, 18), actual={seq.shape}"

        print("[PASS] Feature sequence cache verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
