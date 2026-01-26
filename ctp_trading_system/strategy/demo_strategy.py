"""
自动演示策略 DEMO_AUTO
用于展示程序化交易的自动开仓、撤单、平仓流程
"""
import time
import threading
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime


class StrategyState(Enum):
    """策略状态"""
    IDLE = "idle"                    # 空闲
    RUNNING = "running"              # 运行中
    WAITING_OPEN = "waiting_open"    # 等待开仓成交
    WAITING_CANCEL = "waiting_cancel"  # 等待撤单
    HOLDING = "holding"              # 持仓中
    WAITING_CLOSE = "waiting_close"  # 等待平仓成交
    COMPLETED = "completed"          # 完成
    STOPPED = "stopped"              # 已停止


@dataclass
class StrategyConfig:
    """策略配置"""
    instrument_id: str = "IF2602"      # 合约代码
    volume: int = 1                     # 交易数量
    open_timeout: int = 10              # 开仓超时秒数（触发撤单）
    hold_duration: int = 10             # 持仓时间秒数（触发平仓）
    price_offset: float = 50.0          # 开仓价格偏移（用于制造未成交）


class DemoAutoStrategy:
    """
    自动演示策略

    演示流程：
    1. 启动策略，订阅行情
    2. 收到行情后，自动开仓（价格偏移，制造未成交）
    3. 等待超时后，自动撤单
    4. 重新开仓（使用市价，确保成交）
    5. 持仓一段时间后，自动平仓
    """

    def __init__(self, trading_system, config: Optional[StrategyConfig] = None):
        """
        初始化策略

        Args:
            trading_system: 交易系统实例
            config: 策略配置
        """
        self.system = trading_system
        self.config = config or StrategyConfig()

        self.state = StrategyState.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 订单信息
        self._current_order_ref: Optional[str] = None
        self._open_price: float = 0.0
        self._last_price: float = 0.0

        # 回调函数
        self._log_callback: Optional[Callable] = None
        self._state_callback: Optional[Callable] = None

        # 时间记录
        self._open_time: Optional[datetime] = None
        self._hold_time: Optional[datetime] = None

        # 演示阶段
        self._demo_phase = 0  # 0=未开始, 1=第一次开仓, 2=撤单, 3=第二次开仓, 4=平仓

    def register_log_callback(self, callback: Callable):
        """注册日志回调"""
        self._log_callback = callback

    def register_state_callback(self, callback: Callable):
        """注册状态变更回调"""
        self._state_callback = callback

    def _log(self, message: str):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"{timestamp} [STRATEGY] {message}"
        print(log_msg)
        if self._log_callback:
            try:
                self._log_callback("STRATEGY", "INFO", message)
            except:
                pass

    def _update_state(self, new_state: StrategyState):
        """更新状态"""
        old_state = self.state
        self.state = new_state
        self._log(f"状态变更: {old_state.value} -> {new_state.value}")
        if self._state_callback:
            try:
                self._state_callback(new_state.value)
            except:
                pass

    def start(self) -> bool:
        """启动策略"""
        if self._running:
            self._log("策略已在运行中")
            return False

        if not self.system._running:
            self._log("交易系统未运行，无法启动策略")
            return False

        self._running = True
        self._demo_phase = 0
        self._update_state(StrategyState.RUNNING)

        self._log(f"🤖 策略 DEMO_AUTO 启动")
        self._log(f"📋 配置: 合约={self.config.instrument_id}, 数量={self.config.volume}手")
        self._log(f"⏱️ 开仓超时={self.config.open_timeout}秒, 持仓时间={self.config.hold_duration}秒")

        # 启动策略线程
        self._thread = threading.Thread(target=self._run_strategy, daemon=True)
        self._thread.start()

        return True

    def stop(self):
        """停止策略"""
        self._running = False
        self._update_state(StrategyState.STOPPED)
        self._log("🛑 策略已停止")

    def _run_strategy(self):
        """策略主循环"""
        try:
            # 第1步：获取行情
            self._log(f"📊 正在获取 {self.config.instrument_id} 行情...")
            market_data = self.system.gateway.query_market_data(self.config.instrument_id)

            if not market_data:
                self._log("❌ 获取行情失败，策略终止")
                self._update_state(StrategyState.STOPPED)
                return

            self._last_price = market_data.get('last_price', 0)
            upper_limit = market_data.get('upper_limit', 0)
            lower_limit = market_data.get('lower_limit', 0)

            self._log(f"📊 行情: 最新价={self._last_price}, 涨停={upper_limit}, 跌停={lower_limit}")

            time.sleep(2)  # 等待2秒让用户看到

            if not self._running:
                return

            # 第2步：自动开仓（价格偏移，制造未成交）
            self._demo_phase = 1
            open_price = self._last_price - self.config.price_offset  # 低于市价，不会成交
            self._log(f"{'='*50}")
            self._log(f"🟢 【自动开仓】策略触发开仓信号")
            self._log(f"🟢 合约={self.config.instrument_id}, 方向=买, 数量={self.config.volume}手")
            self._log(f"🟢 价格={open_price}（低于市价{self.config.price_offset}点，预期不成交）")

            self._update_state(StrategyState.WAITING_OPEN)
            order_ref = self.system.gateway.open_position(
                self.config.instrument_id,
                direction=self.system.gateway.Direction.BUY,
                price=open_price,
                volume=self.config.volume
            )

            if order_ref:
                self._current_order_ref = order_ref
                self._open_time = datetime.now()
                self._log(f"✅ 开仓订单已提交，订单号={order_ref}")
                self._log(f"📸 【截图时机1】自动开仓已触发")
            else:
                self._log("❌ 开仓失败")
                self._update_state(StrategyState.STOPPED)
                return

            # 等待开仓超时
            self._log(f"⏳ 等待 {self.config.open_timeout} 秒...")
            for i in range(self.config.open_timeout):
                if not self._running:
                    return
                time.sleep(1)
                remaining = self.config.open_timeout - i - 1
                if remaining > 0 and remaining % 3 == 0:
                    self._log(f"⏳ 剩余 {remaining} 秒触发撤单...")

            if not self._running:
                return

            # 第3步：自动撤单
            self._demo_phase = 2
            self._log(f"{'='*50}")
            self._log(f"🟡 【自动撤单】挂单超时 {self.config.open_timeout} 秒未成交")
            self._log(f"🟡 策略触发自动撤单信号")

            self._update_state(StrategyState.WAITING_CANCEL)
            success = self.system.gateway.cancel_order(
                self.config.instrument_id,
                self._current_order_ref
            )

            if success:
                self._log(f"✅ 撤单请求已发送，订单号={self._current_order_ref}")
                self._log(f"📸 【截图时机2】自动撤单已触发")
            else:
                self._log("⚠️ 撤单请求失败（可能已成交）")

            time.sleep(3)  # 等待撤单确认

            if not self._running:
                return

            # 第4步：重新开仓（使用接近市价，确保成交）
            self._demo_phase = 3
            # 使用涨停价确保成交
            open_price_2 = upper_limit if upper_limit > 0 else self._last_price + 10
            self._log(f"{'='*50}")
            self._log(f"🟢 【自动开仓】策略重新触发开仓信号")
            self._log(f"🟢 合约={self.config.instrument_id}, 方向=买, 数量={self.config.volume}手")
            self._log(f"🟢 价格={open_price_2}（涨停价，确保成交）")

            self._update_state(StrategyState.WAITING_OPEN)
            order_ref_2 = self.system.gateway.open_position(
                self.config.instrument_id,
                direction=self.system.gateway.Direction.BUY,
                price=open_price_2,
                volume=self.config.volume
            )

            if order_ref_2:
                self._current_order_ref = order_ref_2
                self._log(f"✅ 开仓订单已提交，订单号={order_ref_2}")
            else:
                self._log("❌ 开仓失败，策略终止")
                self._update_state(StrategyState.STOPPED)
                return

            time.sleep(3)  # 等待成交

            self._update_state(StrategyState.HOLDING)
            self._hold_time = datetime.now()
            self._log(f"✅ 开仓成交，开始持仓计时")

            # 等待持仓时间
            self._log(f"⏳ 持仓等待 {self.config.hold_duration} 秒后自动平仓...")
            for i in range(self.config.hold_duration):
                if not self._running:
                    return
                time.sleep(1)
                remaining = self.config.hold_duration - i - 1
                if remaining > 0 and remaining % 3 == 0:
                    self._log(f"⏳ 剩余 {remaining} 秒触发平仓...")

            if not self._running:
                return

            # 第5步：自动平仓
            self._demo_phase = 4
            # 使用跌停价确保成交
            close_price = lower_limit if lower_limit > 0 else self._last_price - 10
            self._log(f"{'='*50}")
            self._log(f"🔴 【自动平仓】持仓超过 {self.config.hold_duration} 秒")
            self._log(f"🔴 策略触发自动平仓信号")
            self._log(f"🔴 合约={self.config.instrument_id}, 方向=卖, 数量={self.config.volume}手")
            self._log(f"🔴 价格={close_price}（跌停价，确保成交）")

            self._update_state(StrategyState.WAITING_CLOSE)
            order_ref_3 = self.system.gateway.close_position(
                self.config.instrument_id,
                direction=self.system.gateway.Direction.SELL,
                price=close_price,
                volume=self.config.volume,
                close_today=True
            )

            if order_ref_3:
                self._log(f"✅ 平仓订单已提交，订单号={order_ref_3}")
                self._log(f"📸 【截图时机3】自动平仓已触发")
            else:
                self._log("❌ 平仓失败")

            time.sleep(3)  # 等待成交

            # 完成
            self._update_state(StrategyState.COMPLETED)
            self._log(f"{'='*50}")
            self._log(f"🎉 策略演示完成！")
            self._log(f"📸 请确认已截图：自动开仓、自动撤单、自动平仓")
            self._running = False

        except Exception as e:
            self._log(f"❌ 策略异常: {str(e)}")
            self._update_state(StrategyState.STOPPED)
            self._running = False

    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            "name": "DEMO_AUTO",
            "state": self.state.value,
            "running": self._running,
            "phase": self._demo_phase,
            "config": {
                "instrument_id": self.config.instrument_id,
                "volume": self.config.volume,
                "open_timeout": self.config.open_timeout,
                "hold_duration": self.config.hold_duration
            }
        }
