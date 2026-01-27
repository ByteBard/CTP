"""
LSTM L2策略
深度学习订单簿分析策略

来源: L2滑点回测.py

收益: +2,445.70% (16个月, 2,144笔交易)
胜率: ~84%
注: 2026-01-27 模型缓存更新后的结果

核心逻辑:
1. LSTM模型预测1分钟后价格方向
2. 18特征输入: 基础+冰山单+大单+波动率
3. 三态仓位管理: Flat→Probe→Full→Trail
4. 止损止盈: sl=0.4%, tp=1.2%
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
import threading
import logging
import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

from .feature_engine import FeatureEngine
from .position_manager import PositionManager, PositionConfig, PositionState
from ...data import TickCache, BarAggregator, BarBuffer, TradeContext, ContextManager
from ...data import FeatureSequenceCache, L2DepthBuffer
from ...data.trade_context import SignalContext, ExecutionContext, L1Snapshot

logger = logging.getLogger(__name__)


@dataclass
class LSTMConfig:
    """
    LSTM策略配置

    来源: L2滑点回测.py 的 DEFAULT_PARAMS 和 BEST_PARAMS
    """
    # 合约配置
    instrument_id: str = "rb2505"
    tick_size: float = 1.0

    # 模型路径
    model_path: str = ""        # LSTM模型文件
    scaler_path: str = ""       # 标准化器文件

    # 止损止盈
    sl: float = 0.004           # 止损 0.4%
    tp: float = 0.012           # 止盈 1.2%

    # RSI过滤
    rsi_upper: float = 55
    rsi_lower: float = 45

    # 信号阈值
    threshold: float = 0.5

    # 仓位管理
    probe_size: float = 0.3     # 试探仓 30%
    full_size: float = 1.0      # 满仓 100%
    trail_dd: float = 0.30      # 追踪回撤 30%
    order_size: int = 1         # 下单手数

    # 特征配置
    use_iceberg: bool = True
    use_large_order: bool = True
    use_volatility: bool = True
    seq_len: int = 10           # LSTM序列长度

    # 成本
    commission_rate: float = 0.00005  # 手续费 0.005%


# LSTM模型定义
if TORCH_AVAILABLE:
    class LSTMModel(nn.Module):
        """
        LSTM模型

        来源: L2滑点回测.py

        结构: LSTM(2层, 64隐藏) -> FC(32) -> Sigmoid
        """
        def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2):
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                               batch_first=True, dropout=0.2)
            self.fc = nn.Sequential(
                nn.Linear(hidden_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid()
            )

        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            return self.fc(lstm_out[:, -1, :]).squeeze(-1)
else:
    LSTMModel = None


class LSTML2Strategy:
    """
    LSTM L2策略

    来源: L2滑点回测.py

    核心逻辑:
    1. 每分钟Bar完成时进行LSTM推理
    2. 预测概率 > 0.5 做多，< 0.5 做空
    3. RSI过滤避免追涨杀跌
    4. 三态仓位管理控制风险
    """

    def __init__(self, trading_system, config: LSTMConfig = None):
        """
        Args:
            trading_system: CTP交易系统实例
            config: 策略配置
        """
        self.system = trading_system
        self.config = config or LSTMConfig()

        # 核心组件
        self._feature_engine = FeatureEngine(
            use_iceberg=self.config.use_iceberg,
            use_large_order=self.config.use_large_order,
            use_volatility=self.config.use_volatility
        )

        position_config = PositionConfig(
            sl=self.config.sl,
            tp=self.config.tp,
            rsi_upper=self.config.rsi_upper,
            rsi_lower=self.config.rsi_lower,
            threshold=self.config.threshold,
            probe_size=self.config.probe_size,
            full_size=self.config.full_size,
            trail_dd=self.config.trail_dd
        )
        self._position_manager = PositionManager(position_config)

        self._bar_aggregator = BarAggregator(on_bar_completed=self._on_bar_completed)
        self._bar_buffer = BarBuffer(maxlen=60)
        self._feature_cache = FeatureSequenceCache(
            sequence_length=self.config.seq_len,
            feature_dim=18  # 18个特征
        )
        self._l2_buffer = L2DepthBuffer()
        self._context_manager = ContextManager()

        # 模型
        self._model = None
        self._scaler = None
        self._device = 'cpu'

        # 状态
        self._running = False
        self._bar_count = 0
        self._last_prob = 0.5
        self._last_rsi = 50.0

        # 日内统计
        self._daily_pnl = 0.0
        self._daily_trades = 0

        # 回调
        self._log_callback: Optional[Callable] = None

        # 交易记录
        self._trades: List[Dict] = []

    def register_log_callback(self, callback: Callable):
        """注册日志回调"""
        self._log_callback = callback

    def _log(self, level: str, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"{timestamp} [LSTM] {message}"
        print(log_msg)
        logger.info(log_msg)
        if self._log_callback:
            try:
                self._log_callback("LSTM_L2", level, message)
            except:
                pass

    def load_model(self) -> bool:
        """
        加载LSTM模型

        Returns:
            是否成功加载
        """
        if not TORCH_AVAILABLE:
            self._log("WARN", "PyTorch不可用，将使用模拟预测")
            return True

        if not self.config.model_path:
            self._log("WARN", "未指定模型路径，将使用模拟预测")
            return True

        try:
            # 设置设备
            self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._log("INFO", f"使用设备: {self._device}")

            # 加载模型
            input_dim = len(self._feature_engine.get_feature_names())
            self._model = LSTMModel(input_dim=input_dim).to(self._device)
            self._model.load_state_dict(torch.load(self.config.model_path, map_location=self._device))
            self._model.eval()
            self._log("INFO", f"模型加载成功: {self.config.model_path}")

            # 加载标准化器
            if self.config.scaler_path:
                import pickle
                with open(self.config.scaler_path, 'rb') as f:
                    self._scaler = pickle.load(f)
                self._feature_cache.set_scaler(self._scaler)
                self._log("INFO", f"标准化器加载成功: {self.config.scaler_path}")

            return True

        except Exception as e:
            self._log("ERROR", f"加载模型失败: {e}")
            return False

    def start(self) -> bool:
        """启动策略"""
        if self._running:
            self._log("WARN", "策略已在运行中")
            return False

        # 加载模型
        if not self.load_model():
            return False

        self._running = True
        self._bar_count = 0
        self._position_manager.reset()

        # 启动上下文管理器
        self._context_manager.start()

        self._log("INFO", f"策略启动: {self.config.instrument_id}")
        self._log("INFO", f"止损={self.config.sl*100:.1f}%, 止盈={self.config.tp*100:.1f}%")
        self._log("INFO", f"RSI过滤: [{self.config.rsi_lower}, {self.config.rsi_upper}]")
        self._log("INFO", f"仓位: Probe={self.config.probe_size*100:.0f}%, Full={self.config.full_size*100:.0f}%")

        return True

    def stop(self):
        """停止策略"""
        self._running = False
        self._context_manager.stop()
        self._log("INFO", f"策略停止, 日交易{self._daily_trades}笔, 日收益{self._daily_pnl*100:.4f}%")

    def on_tick(self, tick_data: dict):
        """
        处理tick数据

        Args:
            tick_data: CTP tick数据
        """
        if not self._running:
            return

        # 更新L2数据
        self._l2_buffer.update_from_tick(tick_data)
        self._feature_engine.add_l2_data(tick_data)

        # 聚合Bar
        completed_bar = self._bar_aggregator.on_tick(tick_data)

        # 更新持仓状态
        if self._position_manager.has_position():
            current_price = tick_data.get('last_price', 0)
            if current_price > 0:
                self._check_position_update(current_price, tick_data)

    def _on_bar_completed(self, bar):
        """Bar完成回调"""
        if not self._running:
            return

        self._bar_count += 1

        # 添加Bar到缓存
        self._bar_buffer.add_bar(bar)
        self._feature_engine.add_bar(bar)

        # 计算特征
        features = self._feature_engine.calculate_features()
        self._feature_cache.add_features(features)

        # 获取RSI
        self._last_rsi = features.get('rsi_14', 50.0)

        # 如果特征缓存准备好，进行预测
        if self._feature_cache.is_ready():
            self._run_prediction(bar, features)

    def _run_prediction(self, bar, features: dict):
        """运行LSTM预测"""
        # 获取预测概率
        prob = self._predict()
        self._last_prob = prob

        # 检查信号
        signal = self._position_manager.check_entry_signal(prob, self._last_rsi)

        if signal != 0 and self._position_manager.is_flat():
            # 入场
            self._enter_position(signal, bar.close, prob, self._last_rsi, features)

    def _predict(self) -> float:
        """
        LSTM预测

        Returns:
            预测概率 [0, 1]
        """
        if self._model is None or not TORCH_AVAILABLE:
            # 模拟预测 (基于RSI的简单策略)
            if self._last_rsi > 60:
                return 0.3  # 超买，偏向做空
            elif self._last_rsi < 40:
                return 0.7  # 超卖，偏向做多
            else:
                return 0.5

        try:
            # 获取输入
            X = self._feature_cache.get_lstm_input()
            X_tensor = torch.FloatTensor(X).to(self._device)

            # 推理
            with torch.no_grad():
                prob = self._model(X_tensor).cpu().numpy()[0]

            return float(prob)

        except Exception as e:
            self._log("ERROR", f"预测失败: {e}")
            return 0.5

    def _enter_position(self, direction: int, price: float, prob: float, rsi: float, features: dict):
        """入场"""
        success = self._position_manager.enter_position(
            direction=direction,
            price=price,
            prob=prob,
            rsi=rsi,
            bar_count=self._bar_count
        )

        if success:
            direction_str = "多" if direction == 1 else "空"
            self._log("INFO", f"[ENTRY] {direction_str} @ {price:.2f}, "
                             f"Prob={prob:.3f}, RSI={rsi:.1f}, "
                             f"Size={self.config.probe_size*100:.0f}%")

            # 发送订单
            self._send_entry_order(direction, price)

            # 保存上下文
            self._save_entry_context(direction, price, prob, rsi, features)

    def _check_position_update(self, current_price: float, tick_data: dict):
        """检查仓位更新"""
        # 检查是否有待处理信号
        pending_signal = 0
        if self._feature_cache.is_ready():
            pending_signal = self._position_manager.check_entry_signal(self._last_prob, self._last_rsi)
            # 如果已有仓位，只关心反向信号
            if pending_signal == self._position_manager.position.direction:
                pending_signal = 0

        # 更新状态
        should_exit, reason, pnl_pct = self._position_manager.update(current_price, pending_signal)

        # 状态变化日志
        state = self._position_manager.state
        if state == PositionState.FULL and self._position_manager.position.current_size == self.config.full_size:
            self._log("INFO", f"[UPGRADE] Probe → Full, PnL={pnl_pct*100:.2f}%")
        elif state == PositionState.TRAIL:
            self._log("INFO", f"[UPGRADE] Full → Trail, PnL={pnl_pct*100:.2f}%")

        # 退出
        if should_exit:
            self._exit_position(current_price, reason, pnl_pct, tick_data)

    def _exit_position(self, exit_price: float, reason: str, pnl_pct: float, tick_data: dict):
        """退出仓位"""
        position = self._position_manager.exit_position()
        if position is None:
            return

        # 计算净收益
        cost_pct = self.config.commission_rate * 2  # 双边手续费
        net_pnl_pct = pnl_pct - cost_pct

        # 更新日内统计
        self._daily_pnl += net_pnl_pct
        self._daily_trades += 1

        direction_str = "多" if position.direction == 1 else "空"
        self._log("INFO", f"[EXIT] {direction_str} @ {exit_price:.2f}, "
                         f"原因={reason}, PnL={pnl_pct*100:.2f}%, "
                         f"净收益={net_pnl_pct*100:.4f}%")
        self._log("INFO", f"[DAILY] 交易{self._daily_trades}笔, 日收益={self._daily_pnl*100:.4f}%")

        # 记录交易
        trade = {
            'trade_id': len(self._trades) + 1,
            'direction': position.direction,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'entry_prob': position.entry_prob,
            'entry_rsi': position.entry_rsi,
            'hold_bars': position.hold_bars,
            'peak_profit': position.peak_profit,
            'pnl_pct': pnl_pct,
            'net_pnl_pct': net_pnl_pct,
            'exit_reason': reason,
            'entry_time': position.entry_time.isoformat() if position.entry_time else '',
            'exit_time': datetime.now().isoformat()
        }
        self._trades.append(trade)

        # 发送平仓订单
        self._send_exit_order(position.direction, exit_price)

        # 保存上下文
        self._save_exit_context(exit_price, reason, pnl_pct, tick_data)

    def _send_entry_order(self, direction: int, price: float):
        """发送入场订单"""
        try:
            if not hasattr(self.system, 'gateway') or self.system.gateway is None:
                return

            direction_str = 'BUY' if direction == 1 else 'SELL'
            volume = int(self.config.order_size * self.config.probe_size)
            volume = max(1, volume)

            self.system.gateway.open_position(
                self.config.instrument_id,
                direction=direction_str,
                price=price,
                volume=volume
            )
        except Exception as e:
            self._log("ERROR", f"发送入场订单失败: {e}")

    def _send_exit_order(self, direction: int, price: float):
        """发送出场订单"""
        try:
            if not hasattr(self.system, 'gateway') or self.system.gateway is None:
                return

            close_direction = 'SELL' if direction == 1 else 'BUY'
            position = self._position_manager.position
            volume = int(self.config.order_size * (position.current_size if position else 1))
            volume = max(1, volume)

            self.system.gateway.close_position(
                self.config.instrument_id,
                direction=close_direction,
                price=price,
                volume=volume,
                close_today=True
            )
        except Exception as e:
            self._log("ERROR", f"发送出场订单失败: {e}")

    def _save_entry_context(self, direction: int, price: float, prob: float, rsi: float, features: dict):
        """保存入场上下文"""
        try:
            ctx = TradeContext(
                symbol=self.config.instrument_id,
                strategy_name="LSTM_L2",
                trade_type="entry",
                timestamp=datetime.now().isoformat(),
                strategy_version="1.0",
                feature_matrix=self._feature_cache.get_matrix().tolist(),
                signal=SignalContext(
                    prediction_prob=prob,
                    rsi_value=rsi,
                    signal_direction=direction,
                    feature_values=features
                )
            )
            self._context_manager.save(ctx)
        except Exception as e:
            self._log("WARN", f"保存入场上下文失败: {e}")

    def _save_exit_context(self, exit_price: float, reason: str, pnl_pct: float, tick_data: dict):
        """保存出场上下文"""
        try:
            ctx = TradeContext(
                symbol=self.config.instrument_id,
                strategy_name="LSTM_L2",
                trade_type="exit",
                timestamp=datetime.now().isoformat(),
                strategy_version="1.0",
                l1_snapshot=L1Snapshot.from_tick(tick_data),
                signal=SignalContext(
                    signal_reason=reason
                ),
                execution=ExecutionContext(
                    fill_price=exit_price,
                    slippage_pct=0  # 实际滑点需要从订单回报获取
                )
            )
            self._context_manager.save(ctx)
        except Exception as e:
            self._log("WARN", f"保存出场上下文失败: {e}")

    def get_status(self) -> dict:
        """获取策略状态"""
        pm_status = self._position_manager.get_status()
        return {
            'name': 'LSTM_L2',
            'running': self._running,
            'bar_count': self._bar_count,
            'last_prob': self._last_prob,
            'last_rsi': self._last_rsi,
            'daily_pnl': self._daily_pnl,
            'daily_pnl_pct': f"{self._daily_pnl*100:.4f}%",
            'daily_trades': self._daily_trades,
            'position_state': pm_status['state'],
            'position': pm_status['position'],
            'config': {
                'instrument_id': self.config.instrument_id,
                'sl': f"{self.config.sl*100:.1f}%",
                'tp': f"{self.config.tp*100:.1f}%",
                'rsi_filter': f"[{self.config.rsi_lower}, {self.config.rsi_upper}]"
            }
        }

    def get_trades(self) -> List[Dict]:
        """获取交易记录"""
        return self._trades.copy()

    def get_daily_stats(self) -> dict:
        """获取日内统计"""
        if not self._trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl_pct': 0
            }

        winning = [t for t in self._trades if t['net_pnl_pct'] > 0]
        return {
            'total_trades': len(self._trades),
            'winning_trades': len(winning),
            'win_rate': len(winning) / len(self._trades) if self._trades else 0,
            'total_pnl_pct': sum(t['net_pnl_pct'] for t in self._trades),
            'avg_pnl_pct': sum(t['net_pnl_pct'] for t in self._trades) / len(self._trades)
        }
