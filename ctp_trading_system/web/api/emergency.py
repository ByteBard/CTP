"""
应急处置 API
满足评估表：
- 第20项：暂停交易功能
- 第23项：部分撤单功能
- 第24项：全部撤单功能
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from ..app import get_trading_system
from ..websocket import get_ws_manager

router = APIRouter()


# ==================== 请求/响应模型 ====================

class EmergencyRequest(BaseModel):
    """应急操作请求"""
    reason: Optional[str] = None


class CancelByInstrumentRequest(BaseModel):
    """按合约撤单请求"""
    instrument_id: str
    reason: Optional[str] = None


class EmergencyResponse(BaseModel):
    """应急操作响应"""
    success: bool
    message: str
    data: Optional[dict] = None


# ==================== API端点 ====================

@router.post("/pause", response_model=EmergencyResponse)
async def pause_trading(request: EmergencyRequest):
    """
    暂停交易
    评估表第20项：暂停交易功能
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        reason = request.reason or "手动暂停"
        success = system.emergency_handler.pause_trading(reason)

        if success:
            await ws.send_log("EMERGENCY", "WARNING", f"交易已暂停: {reason}")
            await ws.send_alert("WARNING", "交易暂停", f"交易已暂停，原因：{reason}")
            await ws.send_status("trading", {"paused": True})
            return EmergencyResponse(
                success=True,
                message="交易已暂停",
                data={"reason": reason}
            )
        else:
            return EmergencyResponse(success=False, message="暂停交易失败")

    except Exception as e:
        await ws.send_log("EMERGENCY", "ERROR", f"暂停交易异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=EmergencyResponse)
async def resume_trading(request: EmergencyRequest):
    """
    恢复交易
    评估表第20项：暂停交易功能（恢复）
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        reason = request.reason or "手动恢复"
        success = system.emergency_handler.resume_trading(reason)

        if success:
            await ws.send_log("EMERGENCY", "INFO", f"交易已恢复: {reason}")
            await ws.send_alert("INFO", "交易恢复", f"交易已恢复，原因：{reason}")
            await ws.send_status("trading", {"paused": False})
            return EmergencyResponse(
                success=True,
                message="交易已恢复",
                data={"reason": reason}
            )
        else:
            return EmergencyResponse(success=False, message="恢复交易失败")

    except Exception as e:
        await ws.send_log("EMERGENCY", "ERROR", f"恢复交易异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-by-instrument", response_model=EmergencyResponse)
async def cancel_by_instrument(request: CancelByInstrumentRequest):
    """
    按合约撤单（部分撤单）
    评估表第23项：部分撤单功能
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        reason = request.reason or f"撤销{request.instrument_id}所有订单"
        results = system.emergency_handler.cancel_orders_by_instrument(
            instrument_id=request.instrument_id,
            reason=reason
        )

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        await ws.send_log("EMERGENCY", "INFO",
            f"部分撤单完成: {request.instrument_id}, 成功{success_count}/{total_count}")

        return EmergencyResponse(
            success=True,
            message=f"部分撤单完成，成功{success_count}/{total_count}",
            data={
                "instrument_id": request.instrument_id,
                "total": total_count,
                "success": success_count,
                "results": results
            }
        )

    except Exception as e:
        await ws.send_log("EMERGENCY", "ERROR", f"部分撤单异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-all", response_model=EmergencyResponse)
async def cancel_all_orders(request: EmergencyRequest):
    """
    全部撤单
    评估表第24项：全部撤单功能
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        reason = request.reason or "全部撤单"
        results = system.emergency_handler.cancel_all_orders(reason)

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        await ws.send_log("EMERGENCY", "WARNING",
            f"全部撤单完成: 成功{success_count}/{total_count}")
        await ws.send_alert("WARNING", "全部撤单", f"已撤销{success_count}笔订单")

        return EmergencyResponse(
            success=True,
            message=f"全部撤单完成，成功{success_count}/{total_count}",
            data={
                "total": total_count,
                "success": success_count
            }
        )

    except Exception as e:
        await ws.send_log("EMERGENCY", "ERROR", f"全部撤单异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=EmergencyResponse)
async def emergency_stop(request: EmergencyRequest):
    """
    一键紧急停止
    评估表第20项：暂停交易（紧急模式）
    执行：暂停交易 + 停止策略 + 全部撤单
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        reason = request.reason or "紧急停止"

        await ws.send_alert("CRITICAL", "紧急停止", f"正在执行紧急停止: {reason}")

        system.emergency_handler.emergency_stop(reason)

        await ws.send_log("EMERGENCY", "CRITICAL", f"紧急停止已执行: {reason}")
        await ws.send_status("trading", {"paused": True, "emergency": True})

        return EmergencyResponse(
            success=True,
            message="紧急停止已执行",
            data={"reason": reason}
        )

    except Exception as e:
        await ws.send_log("EMERGENCY", "ERROR", f"紧急停止异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_emergency_status():
    """获取应急状态"""
    system = get_trading_system()

    status = system.emergency_handler.get_status_report()

    return {
        "trading_paused": status.get("trading_paused", False),
        "strategy_stopped": status.get("strategy_stopped", False),
        "pending_orders_count": status.get("pending_orders_count", 0),
        "event_count": status.get("event_count", 0)
    }


@router.get("/history")
async def get_emergency_history(limit: int = 50):
    """获取应急事件历史"""
    system = get_trading_system()

    events = system.emergency_handler.get_event_history(limit)

    event_list = []
    for event in events:
        event_list.append({
            "action": event.action.value if hasattr(event.action, 'value') else str(event.action),
            "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else "",
            "reason": event.reason,
            "success": event.success,
            "details": event.details
        })

    return {"events": event_list}
