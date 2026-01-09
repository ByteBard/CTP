"""
监测面板 API
满足评估表：
- 第5项：连接状态监测
- 第6项：单合约重复开仓监测
- 第7项：单合约重复平仓监测
- 第8项：单合约重复撤单监测
- 第9项：账号报单数量监测
- 第10项：账号撤单数量监测
- 第11项：重复报单阈值及预警
- 第12项：报单总笔数阈值及预警
- 第13项：撤单总笔数阈值及预警
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from ..app import get_trading_system
from ..websocket import get_ws_manager

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ThresholdSettings(BaseModel):
    """阈值设置"""
    open_threshold: Optional[int] = None      # 单合约开仓次数阈值
    close_threshold: Optional[int] = None     # 单合约平仓次数阈值
    cancel_threshold: Optional[int] = None    # 单合约撤单次数阈值
    total_order_threshold: Optional[int] = None   # 总报单阈值
    total_cancel_threshold: Optional[int] = None  # 总撤单阈值


class AlertRecord(BaseModel):
    """预警记录"""
    timestamp: str
    level: str
    type: str
    message: str
    instrument_id: Optional[str] = None
    current_value: Optional[int] = None
    threshold_value: Optional[int] = None


# ==================== API端点 ====================

@router.get("/connection")
async def get_connection_status():
    """
    获取连接状态
    评估表第5项：连接状态监测
    """
    system = get_trading_system()

    status_report = system.connection_monitor.get_status_report()

    return {
        "status": status_report.get("current_state", "UNKNOWN"),
        "heartbeat": status_report.get("last_heartbeat"),
        "disconnect_count": status_report.get("disconnect_count", 0),
        "reconnect_count": status_report.get("reconnect_count", 0),
        "connected": system.gateway.is_connected(),
        "logged_in": system.gateway.is_logged_in()
    }


@router.get("/orders")
async def get_order_stats():
    """
    获取报单统计
    评估表第6-10项：报单监测
    """
    system = get_trading_system()

    # 获取汇总报告
    summary = system.order_monitor.get_summary_report()

    # 获取按合约统计
    instrument_stats = []
    stats_by_instrument = system.order_monitor.get_stats_by_instrument()

    for instrument_id, stats in stats_by_instrument.items():
        instrument_stats.append({
            "instrument_id": instrument_id,
            "open_count": stats.get("open_count", 0),
            "close_count": stats.get("close_count", 0),
            "cancel_count": stats.get("cancel_count", 0)
        })

    return {
        "total_orders": summary.get("total_order_count", 0),
        "total_cancels": summary.get("total_cancel_count", 0),
        "by_instrument": instrument_stats,
        "date": summary.get("date")
    }


@router.get("/thresholds")
async def get_thresholds():
    """
    获取阈值设置
    评估表第11-13项：阈值管理
    """
    system = get_trading_system()

    threshold_status = system.threshold_manager.get_threshold_status()

    return {
        "settings": {
            "open_threshold": system.settings.threshold.repeat_open_threshold,
            "close_threshold": system.settings.threshold.repeat_close_threshold,
            "cancel_threshold": system.settings.threshold.repeat_cancel_threshold,
            "total_order_threshold": system.settings.threshold.total_order_threshold,
            "total_cancel_threshold": system.settings.threshold.total_cancel_threshold
        },
        "status": threshold_status
    }


@router.put("/thresholds")
async def update_thresholds(settings: ThresholdSettings):
    """
    更新阈值设置
    评估表第11-13项：阈值设置
    """
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        if settings.open_threshold is not None:
            system.settings.threshold.repeat_open_threshold = settings.open_threshold
        if settings.close_threshold is not None:
            system.settings.threshold.repeat_close_threshold = settings.close_threshold
        if settings.cancel_threshold is not None:
            system.settings.threshold.repeat_cancel_threshold = settings.cancel_threshold
        if settings.total_order_threshold is not None:
            system.settings.threshold.total_order_threshold = settings.total_order_threshold
        if settings.total_cancel_threshold is not None:
            system.settings.threshold.total_cancel_threshold = settings.total_cancel_threshold

        # 更新阈值管理器
        system.threshold_manager.update_thresholds(system.settings.threshold)

        await ws.send_log("MONITOR", "INFO", "阈值设置已更新")

        return {"success": True, "message": "阈值已更新"}

    except Exception as e:
        await ws.send_log("MONITOR", "ERROR", f"更新阈值失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """
    获取预警历史
    评估表第11-13项：预警功能
    """
    system = get_trading_system()

    # 从阈值管理器获取预警历史
    alerts = system.threshold_manager.get_alert_history(limit)

    alert_list = []
    for alert in alerts:
        alert_list.append({
            "timestamp": alert.timestamp.isoformat() if hasattr(alert, 'timestamp') else "",
            "level": alert.alert_level.value if hasattr(alert, 'alert_level') else "WARNING",
            "type": alert.threshold_type.value if hasattr(alert, 'threshold_type') else "",
            "message": alert.message if hasattr(alert, 'message') else "",
            "instrument_id": alert.instrument_id if hasattr(alert, 'instrument_id') else None,
            "current_value": alert.current_value if hasattr(alert, 'current_value') else None,
            "threshold_value": alert.threshold_value if hasattr(alert, 'threshold_value') else None
        })

    return {"alerts": alert_list}


@router.post("/check")
async def trigger_threshold_check():
    """手动触发阈值检查"""
    system = get_trading_system()
    ws = get_ws_manager()

    try:
        # 触发阈值检查
        system.threshold_manager.check_all_thresholds()

        await ws.send_log("MONITOR", "INFO", "阈值检查已完成")

        return {"success": True, "message": "阈值检查已完成"}

    except Exception as e:
        await ws.send_log("MONITOR", "ERROR", f"阈值检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_system_summary():
    """获取系统状态汇总"""
    system = get_trading_system()

    return system.get_system_status()
