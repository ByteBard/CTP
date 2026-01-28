"""
行情 API
提供行情订阅/退订和实时数据查询
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter

from ..app import get_trading_system, queue_log

router = APIRouter()


class SubscribeRequest(BaseModel):
    """订阅请求"""
    instrument_ids: List[str]


class SubscribeResponse(BaseModel):
    """订阅响应"""
    success: bool
    message: str


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe_market_data(request: SubscribeRequest):
    """订阅行情"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return SubscribeResponse(success=False, message="行情网关未初始化")
    if not md.is_logged_in():
        return SubscribeResponse(success=False, message="行情未登录")

    success = md.subscribe(request.instrument_ids)
    if success:
        queue_log("MARKET", "INFO", f"订阅行情: {', '.join(request.instrument_ids)}")
        return SubscribeResponse(success=True, message="订阅成功")
    return SubscribeResponse(success=False, message="订阅失败")


@router.post("/unsubscribe", response_model=SubscribeResponse)
def unsubscribe_market_data(request: SubscribeRequest):
    """退订行情"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return SubscribeResponse(success=False, message="行情网关未初始化")
    if not md.is_logged_in():
        return SubscribeResponse(success=False, message="行情未登录")

    success = md.unsubscribe(request.instrument_ids)
    if success:
        queue_log("MARKET", "INFO", f"退订行情: {', '.join(request.instrument_ids)}")
        return SubscribeResponse(success=True, message="退订成功")
    return SubscribeResponse(success=False, message="退订失败")


@router.get("/data")
def get_all_market_data():
    """获取所有已订阅的行情数据"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return {"success": False, "message": "行情网关未初始化"}

    return {"success": True, "data": md.get_market_data()}


@router.get("/data/{instrument_id}")
def get_instrument_market_data(instrument_id: str):
    """获取指定合约行情数据"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return {"success": False, "message": "行情网关未初始化"}

    data = md.get_market_data(instrument_id)
    if data:
        return {"success": True, "data": data}
    return {"success": False, "message": f"无{instrument_id}行情数据"}


@router.get("/subscribed")
def get_subscribed():
    """获取已订阅合约列表"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return {"success": False, "message": "行情网关未初始化"}

    return {"success": True, "data": md.get_subscribed()}


@router.get("/status")
def get_md_status():
    """获取行情连接状态"""
    system = get_trading_system()
    md = getattr(system, 'md_gateway', None)

    if not md:
        return {"connected": False, "logged_in": False, "available": False}

    return {
        "connected": md.is_connected(),
        "logged_in": md.is_logged_in(),
        "available": True,
        "subscribed_count": len(md.get_subscribed()),
    }
