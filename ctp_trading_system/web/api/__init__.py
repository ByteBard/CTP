"""
API 路由模块
"""

from fastapi import APIRouter

from . import connection
from . import trading
from . import monitor
from . import emergency
from . import logs
from . import strategy
from . import market

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(connection.router, prefix="/connection", tags=["连接管理"])
api_router.include_router(trading.router, prefix="/trading", tags=["交易操作"])
api_router.include_router(monitor.router, prefix="/monitor", tags=["监测面板"])
api_router.include_router(emergency.router, prefix="/emergency", tags=["应急处置"])
api_router.include_router(logs.router, prefix="/logs", tags=["日志管理"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["策略控制"])
api_router.include_router(market.router, prefix="/market", tags=["行情数据"])
