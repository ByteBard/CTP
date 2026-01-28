"""
交易操作 API
满足评估表：
- 第2项：开仓指令
- 第3项：平仓指令
- 第4项：撤单指令
- 第14-19项：错误防范（交易指令检查）
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from ..app import get_trading_system, queue_log, queue_alert, queue_order_update

router = APIRouter()


# ==================== 请求/响应模型 ====================

class OrderRequest(BaseModel):
    """报单请求"""
    instrument_id: str
    price: float
    volume: int
    direction: str = "buy"  # buy | sell
    offset: str = "open"    # open | close | close_today
    skip_validation: bool = False  # 跳过前端校验，让委托直接发到CTP柜台
    # 高级参数
    exchange_id: Optional[str] = None
    price_type: Optional[str] = None    # limit | market | best
    time_condition: Optional[str] = None  # GFD | IOC | GTC
    volume_condition: Optional[str] = None  # any | min | all
    min_volume: Optional[int] = None


class CancelRequest(BaseModel):
    """撤单请求"""
    instrument_id: str
    order_ref: str


class ValidateRequest(BaseModel):
    """验证请求"""
    instrument_id: str
    direction: str = "buy"
    offset: str = "open"
    price: float
    volume: int


def _resolve_advanced_params(request: 'OrderRequest') -> dict:
    """将前端高级参数转换为gateway参数"""
    params = {}
    if request.price_type:
        price_type_map = {"limit": "2", "market": "1", "best": "3"}
        params["order_price_type"] = price_type_map.get(request.price_type, "2")
    if request.time_condition:
        tc_map = {"GFD": "3", "IOC": "1", "GTC": "2"}
        params["time_condition"] = tc_map.get(request.time_condition, "3")
    if request.volume_condition:
        vc_map = {"any": "1", "min": "2", "all": "3"}
        params["volume_condition"] = vc_map.get(request.volume_condition, "1")
    return params


class OrderResponse(BaseModel):
    """报单响应"""
    success: bool
    message: str
    order_ref: Optional[str] = None
    data: Optional[dict] = None


class ValidationError(BaseModel):
    """验证错误"""
    code: str
    message: str


class ValidateResponse(BaseModel):
    """验证响应"""
    valid: bool
    errors: List[ValidationError] = []


# ==================== API端点 ====================

@router.post("/open", response_model=OrderResponse)
def open_position(request: OrderRequest):
    """
    开仓
    评估表第2项：开仓指令
    注意：使用 def（同步）以避免GIL死锁，FastAPI会在线程池中运行
    """
    try:
        system = get_trading_system()

        if not system._running:
            queue_log("TRADE", "WARNING", "系统未运行，无法开仓")
            return OrderResponse(success=False, message="系统未运行，请先登录")

        if system.emergency_handler.is_trading_paused():
            queue_log("TRADE", "WARNING", "交易已暂停，无法开仓")
            return OrderResponse(success=False, message="交易已暂停")

        if not request.skip_validation:
            # 同步账户和持仓信息到验证器（用于资金/持仓验证）
            try:
                account = system.gateway.query_account(timeout=2)
                if account:
                    system.validator.update_account(account)
                positions = system.gateway.query_position(timeout=2)
                if positions:
                    system.validator.update_positions(positions)
            except:
                pass

            direction = '0' if request.direction == "buy" else '1'
            validation_result = system.validator.validate_order(
                instrument_id=request.instrument_id,
                direction=direction,
                offset='0',
                price=request.price,
                volume=request.volume
            )

            if not validation_result.is_valid:
                error_msg = validation_result.error_message or "验证失败"
                queue_log("TRADE", "ERROR", f"指令验证失败: {error_msg}")
                queue_alert("ERROR", "指令验证失败", error_msg)
                return OrderResponse(success=False, message=error_msg)

            if request.direction == "buy":
                order_ref = system.open_long(
                    instrument_id=request.instrument_id,
                    price=request.price,
                    volume=request.volume
                )
            else:
                order_ref = system.open_short(
                    instrument_id=request.instrument_id,
                    price=request.price,
                    volume=request.volume
                )
        else:
            # 跳过校验，直接通过gateway发送到CTP柜台
            queue_log("TRADE", "WARNING", "已跳过前端校验，委托将直接发送到CTP柜台")
            from ctp_trading_system.core.ctp_gateway import Direction
            direction = Direction.BUY if request.direction == "buy" else Direction.SELL
            system.order_monitor.count_open_order(request.instrument_id, request.volume)
            adv = _resolve_advanced_params(request)
            order_ref = system.gateway.open_position(
                instrument_id=request.instrument_id,
                direction=direction,
                price=request.price,
                volume=request.volume,
                **adv
            )

        if order_ref:
            queue_log("TRADE", "INFO",
                f"开仓报单已提交: {request.instrument_id} {request.direction} {request.volume}@{request.price}")
            queue_order_update({
                "order_ref": order_ref,
                "instrument_id": request.instrument_id,
                "direction": request.direction,
                "offset": "open",
                "price": request.price,
                "volume": request.volume,
                "status": "submitted"
            })
            return OrderResponse(
                success=True,
                message="报单已提交",
                order_ref=order_ref
            )
        else:
            queue_log("TRADE", "ERROR", f"开仓报单失败: {request.instrument_id}")
            return OrderResponse(success=False, message="报单失败，请检查合约代码和验证信息")

    except Exception as e:
        queue_log("TRADE", "ERROR", f"开仓异常: {str(e)}")
        return OrderResponse(success=False, message=f"开仓异常: {str(e)}")


@router.post("/close", response_model=OrderResponse)
def close_position(request: OrderRequest):
    """
    平仓
    评估表第3项：平仓指令
    """
    system = get_trading_system()

    if not system._running:
        return OrderResponse(success=False, message="系统未运行")

    if system.emergency_handler.is_trading_paused():
        queue_log("TRADE", "WARNING", "交易已暂停，无法平仓")
        return OrderResponse(success=False, message="交易已暂停")

    try:
        close_today = request.offset == "close_today"

        if not request.skip_validation:
            direction = '1' if request.direction == "sell" else '0'
            validation_result = system.validator.validate_order(
                instrument_id=request.instrument_id,
                direction=direction,
                offset='1',
                price=request.price,
                volume=request.volume
            )

            if not validation_result.is_valid:
                error_msg = validation_result.error_message or "验证失败"
                queue_log("TRADE", "ERROR", f"指令验证失败: {error_msg}")
                queue_alert("ERROR", "指令验证失败", error_msg)
                return OrderResponse(success=False, message=error_msg)

            if request.direction == "sell":
                order_ref = system.close_long(
                    instrument_id=request.instrument_id,
                    price=request.price,
                    volume=request.volume,
                    close_today=close_today
                )
            else:
                order_ref = system.close_short(
                    instrument_id=request.instrument_id,
                    price=request.price,
                    volume=request.volume,
                    close_today=close_today
                )
        else:
            queue_log("TRADE", "WARNING", "已跳过前端校验，委托将直接发送到CTP柜台")
            from ctp_trading_system.core.ctp_gateway import Direction
            direction = Direction.SELL if request.direction == "sell" else Direction.BUY
            system.order_monitor.count_close_order(request.instrument_id, request.volume)
            adv = _resolve_advanced_params(request)
            order_ref = system.gateway.close_position(
                instrument_id=request.instrument_id,
                direction=direction,
                price=request.price,
                volume=request.volume,
                close_today=close_today,
                **adv
            )

        if order_ref:
            queue_log("TRADE", "INFO",
                f"平仓报单已提交: {request.instrument_id} {request.direction} {request.volume}@{request.price}")
            queue_order_update({
                "order_ref": order_ref,
                "instrument_id": request.instrument_id,
                "direction": request.direction,
                "offset": request.offset,
                "price": request.price,
                "volume": request.volume,
                "status": "submitted"
            })
            return OrderResponse(
                success=True,
                message="报单已提交",
                order_ref=order_ref
            )
        else:
            queue_log("TRADE", "ERROR", "平仓报单失败")
            return OrderResponse(success=False, message="报单失败，请检查验证信息")

    except Exception as e:
        queue_log("TRADE", "ERROR", f"平仓异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel", response_model=OrderResponse)
def cancel_order(request: CancelRequest):
    """
    撤单
    评估表第4项：撤单指令
    """
    system = get_trading_system()

    if not system._running:
        return OrderResponse(success=False, message="系统未运行")

    try:
        success = system.cancel_order(
            instrument_id=request.instrument_id,
            order_ref=request.order_ref
        )

        if success:
            queue_log("TRADE", "INFO",
                f"撤单已提交: {request.instrument_id} {request.order_ref}")
            queue_order_update({
                "order_ref": request.order_ref,
                "instrument_id": request.instrument_id,
                "status": "cancelling"
            })
            return OrderResponse(success=True, message="撤单已提交")
        else:
            queue_log("TRADE", "ERROR", "撤单失败")
            return OrderResponse(success=False, message="撤单失败")

    except Exception as e:
        queue_log("TRADE", "ERROR", f"撤单异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ValidateResponse)
def validate_order(request: ValidateRequest):
    """
    验证交易指令
    评估表第14-19项：错误防范
    """
    system = get_trading_system()

    try:
        # 转换方向和开平
        direction = '0' if request.direction == "buy" else '1'
        offset = '0' if request.offset == "open" else '1'

        # 调用验证器
        result = system.validator.validate_order(
            instrument_id=request.instrument_id,
            direction=direction,
            offset=offset,
            price=request.price,
            volume=request.volume
        )

        errors = []
        if not result.is_valid:
            # 解析错误信息
            error_msg = result.error_message or ""

            if "合约" in error_msg or "instrument" in error_msg.lower():
                errors.append(ValidationError(
                    code="INVALID_INSTRUMENT",
                    message=error_msg
                ))
            elif "价格" in error_msg or "price" in error_msg.lower():
                errors.append(ValidationError(
                    code="INVALID_PRICE",
                    message=error_msg
                ))
            elif "数量" in error_msg or "volume" in error_msg.lower():
                errors.append(ValidationError(
                    code="INVALID_VOLUME",
                    message=error_msg
                ))
            elif "资金" in error_msg or "margin" in error_msg.lower():
                errors.append(ValidationError(
                    code="INSUFFICIENT_MARGIN",
                    message=error_msg
                ))
            elif "持仓" in error_msg or "position" in error_msg.lower():
                errors.append(ValidationError(
                    code="INSUFFICIENT_POSITION",
                    message=error_msg
                ))
            elif "交易时间" in error_msg or "trading time" in error_msg.lower():
                errors.append(ValidationError(
                    code="NON_TRADING_TIME",
                    message=error_msg
                ))
            else:
                errors.append(ValidationError(
                    code="VALIDATION_ERROR",
                    message=error_msg
                ))

            queue_log("TRADE", "WARNING", f"验证失败: {error_msg}")

        return ValidateResponse(valid=result.is_valid, errors=errors)

    except Exception as e:
        queue_log("TRADE", "ERROR", f"验证异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
def get_orders():
    """获取当前委托列表"""
    system = get_trading_system()

    # 从网关获取订单
    orders = getattr(system.gateway, '_orders', {})

    order_list = []
    for order_ref, order in orders.items():
        # 订单数据是字典格式，使用 .get() 访问
        direction = order.get('Direction', '0') if isinstance(order, dict) else getattr(order, 'Direction', '0')
        offset = order.get('CombOffsetFlag', '0') if isinstance(order, dict) else getattr(order, 'CombOffsetFlag', '0')
        status = order.get('OrderStatus', '') if isinstance(order, dict) else getattr(order, 'OrderStatus', '')

        order_list.append({
            "order_ref": order_ref,
            "instrument_id": order.get('InstrumentID', '') if isinstance(order, dict) else getattr(order, 'InstrumentID', ''),
            "direction": "buy" if direction == '0' else "sell",
            "offset": "open" if (offset[0] if offset else '0') == '0' else "close",
            "price": order.get('LimitPrice', 0) if isinstance(order, dict) else getattr(order, 'LimitPrice', 0),
            "volume": order.get('VolumeTotal', 0) if isinstance(order, dict) else getattr(order, 'VolumeTotalOriginal', 0),
            "volume_traded": order.get('VolumeTraded', 0) if isinstance(order, dict) else getattr(order, 'VolumeTraded', 0),
            "status": _get_order_status(status)
        })

    return {"orders": order_list}


@router.get("/instruments")
def get_instruments():
    """获取合约列表"""
    system = get_trading_system()

    instruments = getattr(system.validator, '_instruments', {})

    return {
        "count": len(instruments),
        "instruments": list(instruments.keys())[:100]  # 只返回前100个
    }


@router.get("/market_data/{instrument_id}")
def get_market_data(instrument_id: str):
    """
    查询合约行情数据
    返回最新价、涨跌停价等信息
    """
    system = get_trading_system()

    if not system._running:
        return {"success": False, "message": "系统未运行，请先登录"}

    market_data = system.gateway.query_market_data(instrument_id)

    if market_data:
        return {
            "success": True,
            "data": market_data
        }
    else:
        return {
            "success": False,
            "message": f"无法获取{instrument_id}的行情数据"
        }


@router.get("/account")
def get_account():
    """
    查询资金账户
    返回可用资金、持仓盈亏等
    """
    system = get_trading_system()

    if not system._running:
        return {"success": False, "message": "系统未运行，请先登录"}

    account = system.gateway.query_account(timeout=5)

    if account:
        return {
            "success": True,
            "data": account
        }
    else:
        return {
            "success": False,
            "message": "无法获取账户信息"
        }


@router.get("/positions")
def get_positions():
    """
    查询持仓
    返回各合约持仓和盈亏
    """
    system = get_trading_system()

    if not system._running:
        return {"success": False, "message": "系统未运行，请先登录"}

    positions = system.gateway.query_position(timeout=5)

    if positions:
        return {
            "success": True,
            "data": positions
        }
    else:
        return {
            "success": True,
            "data": {},
            "message": "无持仓"
        }


@router.get("/exchanges")
def get_exchanges():
    """查询交易所列表"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    exchanges = system.gateway.query_exchanges(timeout=5)
    return {"success": True, "data": exchanges}


@router.get("/products")
def get_products(exchange_id: str = ""):
    """查询产品列表"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    products = system.gateway.query_products(exchange_id=exchange_id, timeout=10)
    return {"success": True, "data": products}


@router.get("/position_details")
def get_position_details(instrument_id: str = ""):
    """查询持仓明细"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    details = system.gateway.query_position_detail(instrument_id=instrument_id, timeout=5)
    return {"success": True, "data": details}


@router.get("/investor")
def get_investor():
    """查询投资者信息"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    info = system.gateway.query_investor(timeout=5)
    if info:
        return {"success": True, "data": info}
    return {"success": False, "message": "无法获取投资者信息"}


@router.get("/trading_codes")
def get_trading_codes():
    """查询交易编码"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    codes = system.gateway.query_trading_codes(timeout=5)
    return {"success": True, "data": codes}


@router.get("/order_comm_rate/{instrument_id}")
def get_order_comm_rate(instrument_id: str):
    """查询报单手续费"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    rate = system.gateway.query_order_comm_rate(instrument_id, timeout=5)
    if rate:
        return {"success": True, "data": rate}
    return {"success": False, "message": f"无法获取{instrument_id}的报单手续费"}


@router.get("/margin_rate/{instrument_id}")
def get_margin_rate(instrument_id: str):
    """查询保证金率"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    rate = system.gateway.query_margin_rate(instrument_id, timeout=5)
    if rate:
        return {"success": True, "data": rate}
    return {"success": False, "message": f"无法获取{instrument_id}的保证金率"}


@router.get("/commission_rate/{instrument_id}")
def get_commission_rate(instrument_id: str):
    """查询手续费率"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    rate = system.gateway.query_commission_rate(instrument_id, timeout=5)
    if rate:
        return {"success": True, "data": rate}
    return {"success": False, "message": f"无法获取{instrument_id}的手续费率"}


@router.get("/trades")
def get_trades(instrument_id: str = ""):
    """查询成交列表"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    trades = system.gateway.query_trades(instrument_id=instrument_id, timeout=5)
    trade_list = list(trades.values()) if trades else []
    return {"success": True, "data": trade_list}


@router.get("/instrument_status")
def get_instrument_status():
    """查询合约交易状态"""
    system = get_trading_system()
    if not system._running:
        return {"success": False, "message": "系统未运行"}
    status = system.gateway.get_instrument_status()
    return {"success": True, "data": status}


def _get_order_status(status: str) -> str:
    """转换订单状态"""
    status_map = {
        '0': 'all_traded',      # 全部成交
        '1': 'part_traded',     # 部分成交还在队列中
        '2': 'part_traded_not', # 部分成交不在队列中
        '3': 'not_traded',      # 未成交还在队列中
        '4': 'not_traded_not',  # 未成交不在队列中
        '5': 'canceled',        # 撤单
        'a': 'unknown',         # 未知
        'b': 'not_touched',     # 尚未触发
        'c': 'touched'          # 已触发
    }
    return status_map.get(status, 'unknown')
