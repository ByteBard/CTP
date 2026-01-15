"""
CTP网关核心模块
使用 CTP v6.6.8 官方 API (通过 ctp_wrapper)
满足评估表要求：
- 第1项：认证功能、登录系统
- 第2项：开仓指令
- 第3项：平仓指令
- 第4项：撤单指令
"""
import os
import sys
import time
import threading
from typing import Optional, Dict, Callable, Any, List
from enum import Enum
from dataclasses import dataclass

# 添加 ctp_api 路径
ctp_api_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ctp_api')
if ctp_api_path not in sys.path:
    sys.path.insert(0, ctp_api_path)

# 导入我们的 CTP 封装
try:
    from ctp_api import (
        CTPTraderApi,
        Direction as CTPDirection,
        OffsetFlag as CTPOffsetFlag,
        OrderPriceType as CTPOrderPriceType,
        TimeCondition as CTPTimeCondition,
        VolumeCondition as CTPVolumeCondition,
        OrderStatus as CTPOrderStatus,
        ResumeType,
    )
    CTP_API_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入 CTP API: {e}")
    CTP_API_AVAILABLE = False

# 支持直接运行和作为模块导入
try:
    from ..config.settings import Settings, ConnectionConfig
    from ..trade_logging.trade_logger import get_logger, TradeLogger
except ImportError:
    from config.settings import Settings, ConnectionConfig
    from trade_logging.trade_logger import get_logger, TradeLogger


class Direction(Enum):
    """买卖方向"""
    BUY = '0'   # 买
    SELL = '1'  # 卖


class OffsetFlag(Enum):
    """开平标志"""
    OPEN = '0'           # 开仓
    CLOSE = '1'          # 平仓
    FORCE_CLOSE = '2'    # 强平
    CLOSE_TODAY = '3'    # 平今
    CLOSE_YESTERDAY = '4' # 平昨


class OrderStatus(Enum):
    """订单状态"""
    ALL_TRADED = '0'          # 全部成交
    PART_TRADED_QUEUEING = '1' # 部分成交还在队列中
    PART_TRADED_NOT_QUEUEING = '2' # 部分成交不在队列中
    NO_TRADE_QUEUEING = '3'   # 未成交还在队列中
    NO_TRADE_NOT_QUEUEING = '4' # 未成交不在队列中
    CANCELED = '5'            # 撤单
    UNKNOWN = 'a'             # 未知
    NOT_TOUCHED = 'b'         # 尚未触发
    TOUCHED = 'c'             # 已触发


@dataclass
class OrderRequest:
    """报单请求"""
    instrument_id: str       # 合约代码
    direction: Direction     # 买卖方向
    offset: OffsetFlag       # 开平标志
    price: float             # 价格
    volume: int              # 数量
    order_price_type: str = '2'  # 限价单
    time_condition: str = '3'    # GFD
    volume_condition: str = '1'  # 任意数量
    contingent_condition: str = '1'  # 立即


class CtpGateway:
    """
    CTP交易网关
    使用 CTP v6.6.8 官方 API
    满足评估表第1-4项要求
    """

    def __init__(self, settings: Settings):
        """
        初始化CTP网关

        Args:
            settings: 系统配置
        """
        self.settings = settings
        self.config: ConnectionConfig = settings.connection
        self.logger: TradeLogger = get_logger()

        # API实例
        self._api: Optional[CTPTraderApi] = None

        # 状态
        self._connected = False
        self._authenticated = False
        self._logged_in = False
        self._trading_enabled = True

        # 会话信息
        self._front_id = 0
        self._session_id = 0
        self._trading_day = ""
        self._order_ref = 0
        self._request_id = 0

        # 数据缓存
        self._instruments: Dict[str, Any] = {}
        self._positions: Dict[str, Any] = {}
        self._account: Optional[Dict] = None
        self._orders: Dict[str, Any] = {}

        # 回调
        self._callbacks: Dict[str, List[Callable]] = {
            "on_connected": [],
            "on_disconnected": [],
            "on_order": [],
            "on_trade": [],
            "on_error": [],
        }

        # 同步事件
        self._connect_event = threading.Event()
        self._auth_event = threading.Event()
        self._login_event = threading.Event()
        self._settlement_event = threading.Event()
        self._instrument_event = threading.Event()
        self._account_event = threading.Event()
        self._position_event = threading.Event()

        # 锁
        self._lock = threading.Lock()

    def _get_request_id(self) -> int:
        """获取请求ID"""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _get_order_ref(self) -> str:
        """获取报单引用"""
        with self._lock:
            self._order_ref += 1
            return str(self._order_ref)

    def _setup_callbacks(self):
        """设置API回调"""
        if not self._api:
            return

        # 连接回调
        def on_connected():
            self.logger.log_connection("CONNECTED", self.config.trade_front)
            self._connected = True
            self._connect_event.set()
            for callback in self._callbacks.get("on_connected", []):
                try:
                    callback()
                except Exception as e:
                    self.logger.log_exception(e, "on_connected callback")

        def on_disconnected(reason):
            reason_map = {
                0x1001: "网络读失败",
                0x1002: "网络写失败",
                0x2001: "接收心跳超时",
                0x2002: "发送心跳失败",
                0x2003: "收到错误报文",
            }
            reason_msg = reason_map.get(reason, f"未知原因({reason})")
            self.logger.log_connection("DISCONNECTED", error_msg=reason_msg)
            self._connected = False
            self._authenticated = False
            self._logged_in = False
            for callback in self._callbacks.get("on_disconnected", []):
                try:
                    callback(reason)
                except Exception as e:
                    self.logger.log_exception(e, "on_disconnected callback")

        def on_heartbeat_warning(time_lapse):
            self.logger.log_heartbeat(time_lapse)

        # 认证回调
        def on_authenticate(broker_id, user_id, app_id, error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_authenticate(success=False, error_msg=error_msg, error_code=error_id)
                self._authenticated = False
            else:
                self.logger.log_authenticate(success=True)
                self._authenticated = True
            self._auth_event.set()

        # 登录回调
        def on_login(trading_day, login_time, broker_id, user_id, front_id, session_id,
                     max_order_ref, error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_login(
                    investor_id=self.config.investor_id,
                    success=False,
                    error_msg=error_msg,
                    error_code=error_id
                )
                self._logged_in = False
            else:
                self.logger.log_login(
                    investor_id=self.config.investor_id,
                    success=True,
                    trading_day=trading_day,
                    front_id=front_id,
                    session_id=session_id
                )
                self._logged_in = True
                self._front_id = front_id
                self._session_id = session_id
                self._trading_day = trading_day
                if max_order_ref:
                    try:
                        self._order_ref = int(max_order_ref)
                    except:
                        pass
            self._login_event.set()

        def on_logout(broker_id, user_id, error_id, error_msg, request_id, is_last):
            self.logger.log_system("用户登出", {"investor_id": user_id})

        # 结算确认回调
        def on_settlement_confirm(broker_id, investor_id, confirm_date, confirm_time,
                                  error_id, error_msg, request_id, is_last):
            self.logger.log_system("结算单确认完成")
            self._settlement_event.set()

        # 报单回调
        def on_order_insert(broker_id, investor_id, instrument_id, order_ref, direction,
                           offset_flag, price, volume, error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_error(
                    "报单失败",
                    error_code=error_id,
                    error_msg=error_msg,
                    instrument_id=instrument_id
                )
                for callback in self._callbacks.get("on_error", []):
                    try:
                        callback("order_error", {"instrument_id": instrument_id, "order_ref": order_ref},
                                {"ErrorID": error_id, "ErrorMsg": error_msg})
                    except Exception as e:
                        self.logger.log_exception(e, "on_error callback")

        def on_order_action(broker_id, investor_id, instrument_id, order_ref, front_id,
                           session_id, order_sys_id, error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_error(
                    "撤单失败",
                    error_code=error_id,
                    error_msg=error_msg,
                    order_ref=order_ref
                )
                for callback in self._callbacks.get("on_error", []):
                    try:
                        callback("cancel_error", {"order_ref": order_ref},
                                {"ErrorID": error_id, "ErrorMsg": error_msg})
                    except Exception as e:
                        self.logger.log_exception(e, "on_error callback")

        def on_rtn_order(broker_id, investor_id, instrument_id, order_ref, user_id,
                        direction, offset_flag, price, volume_total, volume_traded,
                        order_status, order_sys_id, front_id, session_id,
                        insert_date, insert_time, status_msg):
            self.logger.log_order_status(
                order_ref=order_ref,
                status=chr(order_status) if isinstance(order_status, int) else order_status,
                status_msg=status_msg,
                instrument_id=instrument_id,
                direction=chr(direction) if isinstance(direction, int) else direction,
                offset=chr(offset_flag) if isinstance(offset_flag, int) else offset_flag,
                volume_total=volume_total,
                volume_traded=volume_traded
            )
            order_data = {
                "OrderRef": order_ref,
                "InstrumentID": instrument_id,
                "Direction": chr(direction) if isinstance(direction, int) else direction,
                "CombOffsetFlag": chr(offset_flag) if isinstance(offset_flag, int) else offset_flag,
                "LimitPrice": price,
                "VolumeTotal": volume_total,
                "VolumeTraded": volume_traded,
                "OrderStatus": chr(order_status) if isinstance(order_status, int) else order_status,
                "OrderSysID": order_sys_id,
                "FrontID": front_id,
                "SessionID": session_id,
                "StatusMsg": status_msg,
            }
            self._orders[order_ref] = order_data
            for callback in self._callbacks.get("on_order", []):
                try:
                    callback(order_data)
                except Exception as e:
                    self.logger.log_exception(e, "on_order callback")

        def on_rtn_trade(broker_id, investor_id, instrument_id, order_ref, user_id,
                        trade_id, direction, offset_flag, price, volume,
                        trade_date, trade_time, order_sys_id):
            self.logger.log_trade(
                instrument_id=instrument_id,
                direction=chr(direction) if isinstance(direction, int) else direction,
                offset=chr(offset_flag) if isinstance(offset_flag, int) else offset_flag,
                price=price,
                volume=volume,
                trade_id=trade_id,
                order_ref=order_ref
            )
            trade_data = {
                "TradeID": trade_id,
                "InstrumentID": instrument_id,
                "Direction": chr(direction) if isinstance(direction, int) else direction,
                "OffsetFlag": chr(offset_flag) if isinstance(offset_flag, int) else offset_flag,
                "Price": price,
                "Volume": volume,
                "OrderRef": order_ref,
                "TradeDate": trade_date,
                "TradeTime": trade_time,
            }
            for callback in self._callbacks.get("on_trade", []):
                try:
                    callback(trade_data)
                except Exception as e:
                    self.logger.log_exception(e, "on_trade callback")

        # 查询回调
        def on_qry_instrument(instrument_id, exchange_id, instrument_name, product_id,
                             volume_multiple, price_tick, long_margin_ratio, short_margin_ratio,
                             is_trading, error_id, error_msg, request_id, is_last):
            if instrument_id:
                self._instruments[instrument_id] = {
                    "instrument_id": instrument_id,
                    "exchange_id": exchange_id,
                    "instrument_name": instrument_name,
                    "product_id": product_id,
                    "volume_multiple": volume_multiple,
                    "price_tick": price_tick,
                    "long_margin_ratio": long_margin_ratio,
                    "short_margin_ratio": short_margin_ratio,
                    "is_trading": is_trading,
                }
            if is_last:
                self.settings.instruments = self._instruments
                self._instrument_event.set()

        def on_qry_trading_account(broker_id, account_id, balance, available, frozen_cash,
                                   curr_margin, close_profit, position_profit,
                                   commission, withdraw_quota,
                                   error_id, error_msg, request_id, is_last):
            if account_id:
                self._account = {
                    "account_id": account_id,
                    "balance": balance,
                    "available": available,
                    "frozen_cash": frozen_cash,
                    "curr_margin": curr_margin,
                    "close_profit": close_profit,
                    "position_profit": position_profit,
                    "commission": commission,
                    "withdraw_quota": withdraw_quota,
                }
            if is_last:
                self._account_event.set()

        def on_qry_position(broker_id, investor_id, instrument_id, position_direction,
                           position, yd_position, position_cost, open_cost,
                           use_margin, frozen_margin,
                           error_id, error_msg, request_id, is_last):
            if instrument_id and position > 0:
                key = f"{instrument_id}_{chr(position_direction) if isinstance(position_direction, int) else position_direction}"
                self._positions[key] = {
                    "instrument_id": instrument_id,
                    "direction": chr(position_direction) if isinstance(position_direction, int) else position_direction,
                    "position": position,
                    "yd_position": yd_position,
                    "today_position": position - yd_position,
                    "position_cost": position_cost,
                    "use_margin": use_margin,
                }
            if is_last:
                self._position_event.set()

        def on_error(error_id, error_msg, request_id, is_last):
            self.logger.log_error("CTP错误", error_code=error_id, error_msg=error_msg)

        # 注册回调
        self._api.on_front_connected = on_connected
        self._api.on_front_disconnected = on_disconnected
        self._api.on_heartbeat_warning = on_heartbeat_warning
        self._api.on_rsp_authenticate = on_authenticate
        self._api.on_rsp_user_login = on_login
        self._api.on_rsp_user_logout = on_logout
        self._api.on_rsp_settlement_info_confirm = on_settlement_confirm
        self._api.on_rsp_order_insert = on_order_insert
        self._api.on_rsp_order_action = on_order_action
        self._api.on_rtn_order = on_rtn_order
        self._api.on_rtn_trade = on_rtn_trade
        self._api.on_rsp_qry_instrument = on_qry_instrument
        self._api.on_rsp_qry_trading_account = on_qry_trading_account
        self._api.on_rsp_qry_investor_position = on_qry_position
        self._api.on_rsp_error = on_error

    # ==================== 连接管理 ====================

    def connect(self, timeout: int = 30) -> bool:
        """
        连接到CTP服务器
        满足评估表第1项：连通性

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否连接成功
        """
        if not CTP_API_AVAILABLE:
            self.logger.log_error("CTP API 未加载")
            return False

        self.logger.log_system("开始连接CTP服务器", {
            "trade_front": self.config.trade_front
        })

        # 创建流文件目录
        flow_path = self.config.flow_path
        os.makedirs(flow_path, exist_ok=True)

        # 创建API实例
        self._api = CTPTraderApi()
        self._api.create_api(flow_path)

        # 设置回调
        self._setup_callbacks()

        # 注册前置
        self._api.register_front(self.config.trade_front)

        # 订阅私有流和公有流
        self._api.subscribe_private_topic(ResumeType.QUICK)
        self._api.subscribe_public_topic(ResumeType.QUICK)

        # 初始化连接
        self._connect_event.clear()
        self._api.init()

        # 等待连接
        if not self._connect_event.wait(timeout):
            self.logger.log_error("连接超时")
            return False

        return self._connected

    # ==================== 认证登录 ====================

    def authenticate(self, timeout: int = 10) -> bool:
        """
        客户端认证
        满足评估表第1项：认证功能

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否认证成功
        """
        if not self._connected:
            self.logger.log_error("未连接，无法认证")
            return False

        self.logger.log_system("开始客户端认证")

        self._auth_event.clear()
        ret = self._api.req_authenticate(
            broker_id=self.config.broker_id,
            user_id=self.config.investor_id,
            app_id=self.config.app_id,
            auth_code=self.config.auth_code,
            request_id=self._get_request_id()
        )

        if ret != 0:
            self.logger.log_error("认证请求发送失败", error_code=ret)
            return False

        if not self._auth_event.wait(timeout):
            self.logger.log_error("认证超时")
            return False

        return self._authenticated

    def login(self, timeout: int = 10) -> bool:
        """
        用户登录
        满足评估表第1项：登录系统

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否登录成功
        """
        if not self._authenticated:
            self.logger.log_error("未认证，无法登录")
            return False

        self.logger.log_system("开始用户登录", {
            "investor_id": self.config.investor_id
        })

        self._login_event.clear()
        ret = self._api.req_user_login(
            broker_id=self.config.broker_id,
            user_id=self.config.investor_id,
            password=self.config.password,
            request_id=self._get_request_id()
        )

        if ret != 0:
            self.logger.log_error("登录请求发送失败", error_code=ret)
            return False

        if not self._login_event.wait(timeout):
            self.logger.log_error("登录超时")
            return False

        return self._logged_in

    def confirm_settlement(self, timeout: int = 10) -> bool:
        """确认结算单"""
        if not self._logged_in:
            return False

        self._settlement_event.clear()
        ret = self._api.req_settlement_info_confirm(
            broker_id=self.config.broker_id,
            investor_id=self.config.investor_id,
            request_id=self._get_request_id()
        )

        if ret != 0:
            return False

        return self._settlement_event.wait(timeout)

    # ==================== 交易功能 ====================

    def open_position(self, instrument_id: str, direction: Direction,
                      price: float, volume: int) -> Optional[str]:
        """
        开仓
        满足评估表第2项：开仓指令

        Args:
            instrument_id: 合约代码
            direction: 买卖方向
            price: 价格
            volume: 数量

        Returns:
            报单引用，失败返回None
        """
        return self._send_order(
            instrument_id=instrument_id,
            direction=direction,
            offset=OffsetFlag.OPEN,
            price=price,
            volume=volume
        )

    def close_position(self, instrument_id: str, direction: Direction,
                       price: float, volume: int,
                       close_today: bool = False) -> Optional[str]:
        """
        平仓
        满足评估表第3项：平仓指令

        Args:
            instrument_id: 合约代码
            direction: 买卖方向（平仓方向与持仓方向相反）
            price: 价格
            volume: 数量
            close_today: 是否平今

        Returns:
            报单引用，失败返回None
        """
        offset = OffsetFlag.CLOSE_TODAY if close_today else OffsetFlag.CLOSE
        return self._send_order(
            instrument_id=instrument_id,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume
        )

    def cancel_order(self, instrument_id: str, order_ref: str,
                     exchange_id: str = "", order_sys_id: str = "") -> bool:
        """
        撤单
        满足评估表第4项：撤单指令

        Args:
            instrument_id: 合约代码
            order_ref: 报单引用
            exchange_id: 交易所代码
            order_sys_id: 报单编号

        Returns:
            是否发送成功
        """
        if not self._logged_in or not self._trading_enabled:
            self.logger.log_error("未登录或交易已禁用，无法撤单")
            return False

        self.logger.log_order_cancel(
            instrument_id=instrument_id,
            order_ref=order_ref,
            order_sys_id=order_sys_id
        )

        ret = self._api.req_order_action(
            broker_id=self.config.broker_id,
            investor_id=self.config.investor_id,
            instrument_id=instrument_id,
            order_ref=order_ref,
            front_id=self._front_id,
            session_id=self._session_id,
            exchange_id=exchange_id,
            order_sys_id=order_sys_id,
            request_id=self._get_request_id()
        )

        if ret != 0:
            self.logger.log_error("撤单请求发送失败", error_code=ret)
            return False

        return True

    def _send_order(self, instrument_id: str, direction: Direction,
                    offset: OffsetFlag, price: float, volume: int) -> Optional[str]:
        """发送报单"""
        if not self._logged_in:
            self.logger.log_error("未登录，无法报单")
            return None

        if not self._trading_enabled:
            self.logger.log_error("交易已禁用，无法报单")
            return None

        order_ref = self._get_order_ref()

        self.logger.log_order_insert(
            instrument_id=instrument_id,
            direction=direction.value,
            offset=offset.value,
            price=price,
            volume=volume,
            order_ref=order_ref
        )

        # 转换方向和开平标志
        ctp_direction = CTPDirection.BUY if direction == Direction.BUY else CTPDirection.SELL

        ctp_offset_map = {
            OffsetFlag.OPEN: CTPOffsetFlag.OPEN,
            OffsetFlag.CLOSE: CTPOffsetFlag.CLOSE,
            OffsetFlag.CLOSE_TODAY: CTPOffsetFlag.CLOSE_TODAY,
            OffsetFlag.CLOSE_YESTERDAY: CTPOffsetFlag.CLOSE_YESTERDAY,
            OffsetFlag.FORCE_CLOSE: CTPOffsetFlag.FORCE_CLOSE,
        }
        ctp_offset = ctp_offset_map.get(offset, CTPOffsetFlag.OPEN)

        ret = self._api.req_order_insert(
            broker_id=self.config.broker_id,
            investor_id=self.config.investor_id,
            instrument_id=instrument_id,
            order_ref=order_ref,
            direction=ctp_direction,
            offset_flag=ctp_offset,
            price=price,
            volume=volume,
            request_id=self._get_request_id()
        )

        if ret != 0:
            self.logger.log_error("报单请求发送失败", error_code=ret)
            return None

        return order_ref

    # ==================== 查询功能 ====================

    def query_instruments(self, timeout: int = 30) -> Dict[str, Any]:
        """查询合约"""
        if not self._logged_in:
            return {}

        self._instruments.clear()
        self._instrument_event.clear()

        ret = self._api.req_qry_instrument(
            instrument_id="",
            exchange_id="",
            product_id="",
            request_id=self._get_request_id()
        )
        if ret != 0:
            return {}

        self._instrument_event.wait(timeout)
        return self._instruments

    def query_account(self, timeout: int = 10) -> Optional[Dict]:
        """查询资金账户"""
        if not self._logged_in:
            return None

        self._account_event.clear()
        ret = self._api.req_qry_trading_account(
            broker_id=self.config.broker_id,
            investor_id=self.config.investor_id,
            request_id=self._get_request_id()
        )
        if ret != 0:
            return None

        self._account_event.wait(timeout)
        return self._account

    def query_position(self, timeout: int = 10) -> Dict[str, Any]:
        """查询持仓"""
        if not self._logged_in:
            return {}

        self._positions.clear()
        self._position_event.clear()

        ret = self._api.req_qry_investor_position(
            broker_id=self.config.broker_id,
            investor_id=self.config.investor_id,
            instrument_id="",
            request_id=self._get_request_id()
        )
        if ret != 0:
            return {}

        self._position_event.wait(timeout)
        return self._positions

    # ==================== 交易控制 ====================

    def enable_trading(self):
        """启用交易"""
        self._trading_enabled = True
        self.logger.log_system("交易已启用")

    def disable_trading(self):
        """禁用交易"""
        self._trading_enabled = False
        self.logger.log_system("交易已禁用")

    def is_trading_enabled(self) -> bool:
        """是否可交易"""
        return self._trading_enabled

    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._logged_in

    # ==================== 回调注册 ====================

    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def unregister_callback(self, event: str, callback: Callable):
        """注销回调"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    # ==================== 清理 ====================

    def close(self):
        """关闭连接"""
        self.logger.log_system("关闭CTP连接")
        if self._api:
            self._api.release()
            self._api = None
        self._connected = False
        self._authenticated = False
        self._logged_in = False
