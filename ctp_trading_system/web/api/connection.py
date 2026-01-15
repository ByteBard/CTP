"""
连接管理 API
满足评估表第1项：接口适应性（认证功能、登录系统）
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from ..app import get_trading_system
from ..websocket import get_ws_manager

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ConnectRequest(BaseModel):
    """连接请求"""
    broker_id: str = "9999"
    trade_front: str = "tcp://180.168.146.187:10201"


class AuthenticateRequest(BaseModel):
    """认证请求"""
    investor_id: str
    app_id: Optional[str] = "simnow_client_test"
    auth_code: Optional[str] = "0000000000000000"


class LoginRequest(BaseModel):
    """登录请求"""
    investor_id: str
    password: str


class ConnectionResponse(BaseModel):
    """连接响应"""
    success: bool
    message: str
    data: Optional[dict] = None


# ==================== API端点 ====================

@router.post("/connect", response_model=ConnectionResponse)
async def connect(request: ConnectRequest):
    """
    连接CTP服务器
    评估表第1项：连通性
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        # 更新配置
        system.settings.connection.broker_id = request.broker_id
        system.settings.connection.trade_front = request.trade_front

        # 尝试连接
        success = system.gateway.connect(timeout=30)

        if success:
            await ws.send_log("SYSTEM", "INFO", "CTP服务器连接成功")
            await ws.send_status("connection", {"status": "connected"})
            return ConnectionResponse(
                success=True,
                message="连接成功",
                data={"broker_id": request.broker_id, "trade_front": request.trade_front}
            )
        else:
            await ws.send_log("SYSTEM", "ERROR", "CTP服务器连接失败")
            return ConnectionResponse(success=False, message="连接失败")

    except Exception as e:
        await ws.send_log("SYSTEM", "ERROR", f"连接异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/authenticate", response_model=ConnectionResponse)
async def authenticate(request: AuthenticateRequest):
    """
    客户端认证
    评估表第1项：认证功能
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        # 更新认证信息
        system.settings.connection.investor_id = request.investor_id
        if request.app_id:
            system.settings.connection.app_id = request.app_id
        if request.auth_code:
            system.settings.connection.auth_code = request.auth_code

        # 尝试认证
        success = system.gateway.authenticate(timeout=10)

        if success:
            await ws.send_log("SYSTEM", "INFO", "客户端认证成功")
            await ws.send_status("connection", {"status": "authenticated"})
            return ConnectionResponse(success=True, message="认证成功")
        else:
            await ws.send_log("SYSTEM", "ERROR", "客户端认证失败")
            return ConnectionResponse(success=False, message="认证失败")

    except Exception as e:
        await ws.send_log("SYSTEM", "ERROR", f"认证异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=ConnectionResponse)
async def login(request: LoginRequest):
    """
    用户登录
    评估表第1项：登录系统
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        # 更新登录信息
        system.settings.connection.investor_id = request.investor_id
        system.settings.connection.password = request.password

        # 尝试登录
        success = system.gateway.login(timeout=10)

        if success:
            # 确认结算单
            system.gateway.confirm_settlement(timeout=10)

            # 查询合约
            instruments = system.gateway.query_instruments(timeout=60)
            system.validator.update_instruments(instruments)

            # 启动连接监测
            system.connection_monitor.start()
            system._running = True

            await ws.send_log("SYSTEM", "INFO", f"用户 {request.investor_id} 登录成功")
            await ws.send_status("connection", {"status": "logged_in"})
            return ConnectionResponse(
                success=True,
                message="登录成功",
                data={"investor_id": request.investor_id, "instruments_count": len(instruments)}
            )
        else:
            await ws.send_log("SYSTEM", "ERROR", "用户登录失败")
            return ConnectionResponse(success=False, message="登录失败")

    except Exception as e:
        await ws.send_log("SYSTEM", "ERROR", f"登录异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout", response_model=ConnectionResponse)
async def logout():
    """登出"""
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        system.stop()
        await ws.send_log("SYSTEM", "INFO", "已登出")
        await ws.send_status("connection", {"status": "disconnected"})
        return ConnectionResponse(success=True, message="已登出")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取连接状态"""
    system = get_trading_system()

    return {
        "connected": system.gateway.is_connected(),
        "authenticated": getattr(system.gateway, '_authenticated', False),
        "logged_in": system.gateway.is_logged_in(),
        "running": system._running
    }
