"""
策略控制 API
用于启动/停止自动演示策略
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter

from ..app import get_trading_system
from ..websocket import get_ws_manager
from ctp_trading_system.strategy import DemoAutoStrategy, StrategyConfig

router = APIRouter()

# 全局策略实例
_demo_strategy: Optional[DemoAutoStrategy] = None


class StrategyConfigRequest(BaseModel):
    """策略配置请求"""
    instrument_id: str = "IF2602"
    volume: int = 1
    open_timeout: int = 10
    hold_duration: int = 10


class StrategyResponse(BaseModel):
    """策略响应"""
    success: bool
    message: str
    data: Optional[dict] = None


def _get_strategy() -> Optional[DemoAutoStrategy]:
    """获取策略实例"""
    global _demo_strategy
    return _demo_strategy


def _create_strategy(config: StrategyConfig) -> DemoAutoStrategy:
    """创建策略实例"""
    global _demo_strategy
    system = get_trading_system()
    _demo_strategy = DemoAutoStrategy(system, config)

    # 注册日志回调
    async def log_callback(source, level, message):
        ws = get_ws_manager()
        await ws.send_log(source, level, message)

    def sync_log_callback(source, level, message):
        import asyncio
        ws = get_ws_manager()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(ws.send_log(source, level, message))
            else:
                loop.run_until_complete(ws.send_log(source, level, message))
        except:
            # 如果没有事件循环，创建新的
            asyncio.run(ws.send_log(source, level, message))

    _demo_strategy.register_log_callback(sync_log_callback)

    return _demo_strategy


@router.post("/start", response_model=StrategyResponse)
async def start_strategy(config: StrategyConfigRequest):
    """
    启动自动演示策略
    """
    system = get_trading_system()
    ws = get_ws_manager()

    if not system._running:
        return StrategyResponse(
            success=False,
            message="系统未运行，请先登录"
        )

    # 检查是否已有运行中的策略
    strategy = _get_strategy()
    if strategy and strategy._running:
        return StrategyResponse(
            success=False,
            message="策略已在运行中"
        )

    # 创建策略配置
    strategy_config = StrategyConfig(
        instrument_id=config.instrument_id,
        volume=config.volume,
        open_timeout=config.open_timeout,
        hold_duration=config.hold_duration
    )

    # 创建并启动策略
    strategy = _create_strategy(strategy_config)

    await ws.send_log("STRATEGY", "INFO", f"🤖 正在启动策略 DEMO_AUTO...")
    await ws.send_log("STRATEGY", "INFO", f"📋 合约={config.instrument_id}, 数量={config.volume}手")

    success = strategy.start()

    if success:
        await ws.send_log("STRATEGY", "INFO", "✅ 策略启动成功")
        return StrategyResponse(
            success=True,
            message="策略启动成功",
            data=strategy.get_status()
        )
    else:
        await ws.send_log("STRATEGY", "ERROR", "❌ 策略启动失败")
        return StrategyResponse(
            success=False,
            message="策略启动失败"
        )


@router.post("/stop", response_model=StrategyResponse)
async def stop_strategy():
    """
    停止策略
    """
    ws = get_ws_manager()
    strategy = _get_strategy()

    if not strategy:
        return StrategyResponse(
            success=False,
            message="没有运行中的策略"
        )

    strategy.stop()
    await ws.send_log("STRATEGY", "INFO", "🛑 策略已停止")

    return StrategyResponse(
        success=True,
        message="策略已停止",
        data=strategy.get_status()
    )


@router.get("/status", response_model=StrategyResponse)
async def get_strategy_status():
    """
    获取策略状态
    """
    strategy = _get_strategy()

    if not strategy:
        return StrategyResponse(
            success=True,
            message="无策略运行",
            data={
                "name": "DEMO_AUTO",
                "state": "idle",
                "running": False
            }
        )

    return StrategyResponse(
        success=True,
        message="获取成功",
        data=strategy.get_status()
    )
