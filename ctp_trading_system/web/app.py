"""
FastAPI 应用主入口
CTP程序化交易系统 Web UI
"""
import os
import sys
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 添加项目路径
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("CTP程序化交易系统 Web UI 启动中...")
    get_trading_system()
    yield
    # 关闭时
    print("CTP程序化交易系统 Web UI 关闭中...")
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

    # 静态文件
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 模板
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
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
