"""
策略管理器
统一管理多策略的启停、切换、仓位分配

功能:
1. 策略注册与管理
2. 手动切换策略
3. 同时运行多策略
4. 仓位分配控制
"""

from typing import Dict, Optional, List, Any
from enum import Enum
from dataclasses import dataclass
import logging

from .h1e_tick import H1eTickStrategy, H1eConfig
from .lstm_l2 import LSTML2Strategy, LSTMConfig
from .demo_strategy import DemoAutoStrategy, StrategyConfig as DemoConfig

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型"""
    H1E_TICK = "H1e_TICK"
    LSTM_L2 = "LSTM_L2"
    DEMO_AUTO = "DEMO_AUTO"


@dataclass
class StrategyAllocation:
    """仓位分配"""
    strategy_type: StrategyType
    allocation_pct: float  # 仓位占比 (0-1)
    max_position: int      # 最大持仓手数


class StrategyManager:
    """
    策略管理器

    功能:
    1. 策略注册与管理
    2. 手动切换策略
    3. 同时运行多策略
    4. 仓位分配控制
    """

    def __init__(self, trading_system):
        """
        Args:
            trading_system: CTP交易系统实例
        """
        self.system = trading_system
        self._strategies: Dict[str, Any] = {}
        self._allocations: Dict[str, StrategyAllocation] = {}
        self._active_strategies: List[str] = []
        self._log_callback = None

    def register_log_callback(self, callback):
        """注册日志回调"""
        self._log_callback = callback

    def _log(self, level: str, message: str):
        """输出日志"""
        logger.info(f"[StrategyManager] {message}")
        if self._log_callback:
            try:
                self._log_callback("STRATEGY_MGR", level, message)
            except:
                pass

    def register_strategy(self,
                          strategy_type: StrategyType,
                          config: dict = None,
                          allocation: StrategyAllocation = None) -> bool:
        """
        注册策略

        Args:
            strategy_type: 策略类型
            config: 策略配置字典
            allocation: 仓位分配

        Returns:
            是否成功注册
        """
        name = strategy_type.value
        config = config or {}

        try:
            if strategy_type == StrategyType.H1E_TICK:
                h1e_config = H1eConfig(**config)
                strategy = H1eTickStrategy(self.system, h1e_config)

            elif strategy_type == StrategyType.LSTM_L2:
                lstm_config = LSTMConfig(**config)
                strategy = LSTML2Strategy(self.system, lstm_config)

            elif strategy_type == StrategyType.DEMO_AUTO:
                demo_config = DemoConfig(**config)
                strategy = DemoAutoStrategy(self.system, demo_config)

            else:
                self._log("ERROR", f"未知策略类型: {strategy_type}")
                return False

            # 注册日志回调
            if self._log_callback and hasattr(strategy, 'register_log_callback'):
                strategy.register_log_callback(self._log_callback)

            self._strategies[name] = strategy

            if allocation:
                self._allocations[name] = allocation

            self._log("INFO", f"策略注册成功: {name}")
            return True

        except Exception as e:
            self._log("ERROR", f"策略注册失败: {name}, 错误: {e}")
            return False

    def start_strategy(self, name: str) -> bool:
        """
        启动指定策略

        Args:
            name: 策略名称

        Returns:
            是否成功启动
        """
        if name not in self._strategies:
            self._log("ERROR", f"策略不存在: {name}")
            return False

        if name in self._active_strategies:
            self._log("WARN", f"策略已在运行: {name}")
            return True

        strategy = self._strategies[name]
        try:
            success = strategy.start()
            if success:
                self._active_strategies.append(name)
                self._log("INFO", f"策略启动成功: {name}")
            else:
                self._log("ERROR", f"策略启动失败: {name}")
            return success
        except Exception as e:
            self._log("ERROR", f"策略启动异常: {name}, 错误: {e}")
            return False

    def stop_strategy(self, name: str) -> bool:
        """
        停止指定策略

        Args:
            name: 策略名称

        Returns:
            是否成功停止
        """
        if name not in self._strategies:
            self._log("ERROR", f"策略不存在: {name}")
            return False

        strategy = self._strategies[name]
        try:
            strategy.stop()
            if name in self._active_strategies:
                self._active_strategies.remove(name)
            self._log("INFO", f"策略已停止: {name}")
            return True
        except Exception as e:
            self._log("ERROR", f"策略停止异常: {name}, 错误: {e}")
            return False

    def switch_strategy(self, from_name: str, to_name: str) -> bool:
        """
        切换策略 (手动)

        1. 停止当前策略
        2. 等待平仓完成
        3. 启动新策略

        Args:
            from_name: 当前策略名称
            to_name: 目标策略名称

        Returns:
            是否成功切换
        """
        self._log("INFO", f"切换策略: {from_name} → {to_name}")

        if from_name in self._active_strategies:
            self.stop_strategy(from_name)

        return self.start_strategy(to_name)

    def set_allocation(self, name: str, allocation_pct: float, max_position: int):
        """
        设置仓位分配

        Args:
            name: 策略名称
            allocation_pct: 仓位占比 (0-1)
            max_position: 最大持仓手数
        """
        if name in self._strategies:
            try:
                strategy_type = StrategyType(name)
                self._allocations[name] = StrategyAllocation(
                    strategy_type=strategy_type,
                    allocation_pct=allocation_pct,
                    max_position=max_position
                )
                self._log("INFO", f"仓位设置: {name}, 占比={allocation_pct*100:.0f}%, 最大={max_position}手")
            except:
                pass

    def get_active_strategies(self) -> List[str]:
        """获取运行中的策略列表"""
        return self._active_strategies.copy()

    def get_all_strategies(self) -> List[str]:
        """获取所有已注册的策略列表"""
        return list(self._strategies.keys())

    def get_strategy(self, name: str):
        """获取策略实例"""
        return self._strategies.get(name)

    def get_all_status(self) -> Dict[str, dict]:
        """获取所有策略状态"""
        status = {}
        for name, strategy in self._strategies.items():
            try:
                strategy_status = strategy.get_status() if hasattr(strategy, 'get_status') else {}
                status[name] = {
                    **strategy_status,
                    'active': name in self._active_strategies,
                    'allocation': {
                        'pct': self._allocations[name].allocation_pct,
                        'max_position': self._allocations[name].max_position
                    } if name in self._allocations else None
                }
            except Exception as e:
                status[name] = {'error': str(e)}
        return status

    def on_tick(self, tick_data: dict):
        """
        Tick数据分发给活跃策略

        Args:
            tick_data: CTP tick数据
        """
        for name in self._active_strategies:
            strategy = self._strategies.get(name)
            if strategy and hasattr(strategy, 'on_tick'):
                try:
                    strategy.on_tick(tick_data)
                except Exception as e:
                    self._log("ERROR", f"策略{name}处理tick异常: {e}")

    def on_bar(self, bar_data: dict):
        """
        Bar数据分发给活跃策略

        Args:
            bar_data: K线数据
        """
        for name in self._active_strategies:
            strategy = self._strategies.get(name)
            if strategy and hasattr(strategy, 'on_bar'):
                try:
                    strategy.on_bar(bar_data)
                except Exception as e:
                    self._log("ERROR", f"策略{name}处理bar异常: {e}")

    def stop_all(self):
        """停止所有策略"""
        for name in self._active_strategies.copy():
            self.stop_strategy(name)

    def get_total_pnl(self) -> float:
        """获取所有策略总收益"""
        total_pnl = 0.0
        for name, strategy in self._strategies.items():
            if hasattr(strategy, 'get_status'):
                status = strategy.get_status()
                total_pnl += status.get('daily_pnl', 0)
        return total_pnl
