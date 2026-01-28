"""
FastAPI 应用主入口
CTP程序化交易系统 Web UI
"""
import os
import sys
import asyncio
import threading
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware


def get_resource_path(relative_path: str) -> str:
    """获取资源文件路径（支持PyInstaller打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后，资源在 _MEIPASS 目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


# 添加项目路径
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ctp_trading_system.config.settings import Settings
from ctp_trading_system.main import TradingSystem

# 全局交易系统实例
_trading_system: Optional[TradingSystem] = None


def get_trading_system() -> TradingSystem:
    """获取交易系统实例"""
    global _trading_system
    if _trading_system is None:
        _trading_system = TradingSystem()
    return _trading_system


def set_trading_system(system: TradingSystem):
    """设置交易系统实例"""
    global _trading_system
    _trading_system = system


# 订单更新队列（用于从同步回调传递到异步WebSocket）
_order_update_queue = []
_trade_update_queue = []
_alert_queue = []
_error_queue = []
_log_queue = []
_update_queue_lock = threading.Lock()


def queue_log(log_type: str, level: str, message: str, data: dict = None):
    """线程安全地将日志消息加入队列（供同步代码使用）"""
    with _update_queue_lock:
        _log_queue.append({"log_type": log_type, "level": level, "message": message, "data": data})


def queue_alert(level: str, title: str, message: str):
    """线程安全地将预警消息加入队列（供同步代码使用）"""
    with _update_queue_lock:
        _alert_queue.append({"level": level, "type": title, "message": message, "instrument_id": "", "current_value": 0, "threshold_value": 0})


def queue_order_update(order: dict):
    """线程安全地将订单更新加入队列（供同步代码使用）"""
    with _update_queue_lock:
        _order_update_queue.append(order)


def _on_order_callback(order_data: dict):
    """网关订单回调 - 从同步CTP线程调用"""
    with _update_queue_lock:
        _order_update_queue.append(order_data.copy())


def _on_trade_callback(trade_data: dict):
    """网关成交回调 - 从同步CTP线程调用"""
    with _update_queue_lock:
        _trade_update_queue.append(trade_data.copy())


def _on_error_callback(error_type: str, order_info: dict, error_info: dict):
    """网关错误回调 - CTP柜台返回的错误"""
    with _update_queue_lock:
        _error_queue.append({
            "error_type": error_type,
            "order_info": order_info.copy(),
            "error_info": error_info.copy()
        })


def _on_alert_callback(alert):
    """阈值告警回调 - 从同步线程调用"""
    with _update_queue_lock:
        _alert_queue.append({
            "type": alert.threshold_type.value,
            "level": alert.alert_level.value,
            "message": alert.message,
            "instrument_id": alert.instrument_id,
            "current_value": alert.current_value,
            "threshold_value": alert.threshold_value
        })


async def _process_order_updates():
    """后台任务：处理订单、成交、告警更新队列，推送到WebSocket"""
    from .websocket import get_ws_manager
    ws = get_ws_manager()

    while True:
        order_updates = []
        trade_updates = []
        alert_updates = []
        error_updates = []
        log_updates = []
        with _update_queue_lock:
            if _order_update_queue:
                order_updates = _order_update_queue.copy()
                _order_update_queue.clear()
            if _trade_update_queue:
                trade_updates = _trade_update_queue.copy()
                _trade_update_queue.clear()
            if _alert_queue:
                alert_updates = _alert_queue.copy()
                _alert_queue.clear()
            if _error_queue:
                error_updates = _error_queue.copy()
                _error_queue.clear()
            if _log_queue:
                log_updates = _log_queue.copy()
                _log_queue.clear()

        # 处理订单更新
        for order in order_updates:
            await ws.send_order_update(order)
            status_text = {
                'a': '已提交', '0': '全部成交', '1': '部分成交',
                '3': '未成交(排队中)', '5': '已撤单'
            }.get(order.get('OrderStatus', ''), order.get('OrderStatus', ''))
            direction = "买" if order.get('Direction', '') == '0' else "卖"
            offset_char = order.get('CombOffsetFlag', '0')
            offset_text = {"0": "开仓", "1": "平仓", "3": "平今", "4": "平昨"}.get(offset_char, offset_char)
            price = order.get('LimitPrice', '')
            vol_total = order.get('VolumeTotal', '')
            vol_traded = order.get('VolumeTraded', '')
            order_ref = order.get('OrderRef', '')
            order_sys_id = order.get('OrderSysID', '')
            instrument = order.get('InstrumentID', '')
            detail = (f"[交易] {offset_text}委托: 合约={instrument}, 方向={direction}, "
                      f"价格={price}, 数量={vol_total}, 已成交={vol_traded}, "
                      f"委托编号={order_sys_id or order_ref}, 状态={status_text}")
            await ws.send_log("TRADE", "INFO", detail)

        # 处理成交回报
        for trade in trade_updates:
            direction = "买" if trade.get('Direction') == '0' else "卖"
            offset_char = trade.get('OffsetFlag', '0')
            offset_text = {"0": "开仓", "1": "平仓", "3": "平今", "4": "平昨"}.get(offset_char, offset_char)
            await ws.send_log(
                "TRADE", "INFO",
                f"[交易] 成交回报: 合约={trade.get('InstrumentID', '')}, "
                f"方向={direction}, 开平={offset_text}, "
                f"价格={trade.get('Price', 0)}, 数量={trade.get('Volume', 0)}, "
                f"成交编号={trade.get('TradeID', '')}, "
                f"委托编号={trade.get('OrderRef', '')}"
            )

            # 成交后查询账户盈亏信息
            try:
                system = get_trading_system()
                if system and system._running:
                    account = system.gateway.query_account(timeout=2)
                    if account:
                        position_profit = account.get('position_profit', 0)
                        close_profit = account.get('close_profit', 0)
                        available = account.get('available', 0)
                        profit_sign = "+" if position_profit >= 0 else ""
                        await ws.send_log(
                            "TRADE", "INFO",
                            f"💰 账户盈亏: 持仓盈亏={profit_sign}{position_profit:.2f}元 "
                            f"平仓盈亏={close_profit:.2f}元 可用资金={available:.2f}元"
                        )
            except Exception as e:
                pass  # 盈亏查询失败不影响主流程

        # 处理阈值告警
        for alert in alert_updates:
            level = "WARNING" if alert.get('level') == 'WARNING' else "ERROR"
            instrument = alert.get('instrument_id', '')
            msg = alert.get('message', '')
            await ws.send_alert(level, "阈值预警", msg)
            await ws.send_log(
                "ALERT", level,
                f"阈值预警: {msg}"
            )

        # 处理CTP柜台错误
        for error in error_updates:
            error_info = error.get('error_info', {})
            order_info = error.get('order_info', {})
            error_id = error_info.get('ErrorID', 0)
            error_msg = error_info.get('ErrorMsg', '未知错误')
            instrument = order_info.get('instrument_id', '')
            direction = order_info.get('direction', '')
            offset = order_info.get('offset', '')
            price = order_info.get('price', '')
            volume = order_info.get('volume', '')
            detail = (f"CTP柜台返回错误: [ErrorID={error_id}] {error_msg} "
                      f"| 合约={instrument}, 方向={direction}, 开平={offset}, "
                      f"价格={price}, 数量={volume}")
            await ws.send_log("ERROR", "ERROR", detail)
            await ws.send_alert("ERROR", "CTP柜台错误", f"[ErrorID={error_id}] {error_msg}")

        # 处理日志队列
        for log in log_updates:
            await ws.send_log(log["log_type"], log["level"], log["message"], log.get("data"))

        await asyncio.sleep(0.1)  # 100ms检查一次


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("CTP程序化交易系统 Web UI 启动中...")
    system = get_trading_system()

    # 注册订单、成交和错误回调
    system.gateway.register_callback("on_order", _on_order_callback)
    system.gateway.register_callback("on_trade", _on_trade_callback)
    system.gateway.register_callback("on_error", _on_error_callback)

    # 注册阈值告警回调
    system.threshold_manager.register_alert_callback(_on_alert_callback)

    # 启动订单更新处理任务
    order_task = asyncio.create_task(_process_order_updates())

    yield

    # 关闭时
    print("CTP程序化交易系统 Web UI 关闭中...")
    order_task.cancel()
    try:
        await order_task
    except asyncio.CancelledError:
        pass

    if _trading_system and _trading_system._running:
        _trading_system.stop()


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="CTP程序化交易系统",
        description="符合 T/ZQX 0004-2025 期货程序化交易系统功能测试指引",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 静态文件（支持打包后路径）
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后
        static_dir = os.path.join(sys._MEIPASS, "ctp_trading_system", "web", "static")
        templates_dir = os.path.join(sys._MEIPASS, "ctp_trading_system", "web", "templates")
    else:
        # 开发环境
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 模板
    templates = Jinja2Templates(directory=templates_dir)

    # 注册API路由
    from .api import api_router
    app.include_router(api_router)

    # 注册WebSocket
    from .websocket import setup_websocket
    setup_websocket(app)

    # 主页路由
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """主页"""
        return templates.TemplateResponse("index.html", {"request": request})

    # 健康检查
    @app.get("/health")
    async def health():
        """健康检查"""
        system = get_trading_system()
        return {
            "status": "ok",
            "system_running": system._running if system else False
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ctp_trading_system.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
