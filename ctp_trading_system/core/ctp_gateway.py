"""
CTP网关核心模块
满足评估表要求：
- 第1项：认证功能、登录系统
- 第2项：开仓指令
- 第3项：平仓指令
- 第4项：撤单指令
"""
import os
import time
import threading
from typing import Optional, Dict, Callable, Any, List
from enum import Enum
from dataclasses import dataclass

# CTP API导入（使用openctp-ctp或官方ctp库）
try:
    from openctp_ctp import tdapi, mdapi
except ImportError:
    try:
        from ctp import tdapi, mdapi
    except ImportError:
        # 模拟模式，用于测试
        tdapi = None
        mdapi = None

from ..config.settings import Settings, ConnectionConfig
from ..logging.trade_logger import get_logger, TradeLogger


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


class CtpTraderSpi:
    """
    交易回调处理类
    处理CTP交易API的所有回调
    """

    def __init__(self, gateway: "CtpGateway"):
        self.gateway = gateway
        self.logger: TradeLogger = get_logger()

    def OnFrontConnected(self):
        """连接成功回调"""
        self.logger.log_connection("CONNECTED", self.gateway.config.trade_front)
        self.gateway._on_front_connected()

    def OnFrontDisconnected(self, nReason: int):
        """连接断开回调"""
        reason_map = {
            0x1001: "网络读失败",
            0x1002: "网络写失败",
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文",
        }
        reason_msg = reason_map.get(nReason, f"未知原因({nReason})")
        self.logger.log_connection("DISCONNECTED", error_msg=reason_msg)
        self.gateway._on_front_disconnected(nReason)

    def OnHeartBeatWarning(self, nTimeLapse: int):
        """心跳警告"""
        self.logger.log_heartbeat(nTimeLapse)

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        """客户端认证响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.logger.log_authenticate(
                success=False,
                error_msg=pRspInfo.ErrorMsg,
                error_code=pRspInfo.ErrorID
            )
            self.gateway._on_authenticate_failed(pRspInfo.ErrorID, pRspInfo.ErrorMsg)
        else:
            self.logger.log_authenticate(success=True)
            self.gateway._on_authenticate_success()

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登录响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.logger.log_login(
                investor_id=self.gateway.config.investor_id,
                success=False,
                error_msg=pRspInfo.ErrorMsg,
                error_code=pRspInfo.ErrorID
            )
            self.gateway._on_login_failed(pRspInfo.ErrorID, pRspInfo.ErrorMsg)
        else:
            self.logger.log_login(
                investor_id=self.gateway.config.investor_id,
                success=True,
                trading_day=pRspUserLogin.TradingDay if pRspUserLogin else "",
                front_id=pRspUserLogin.FrontID if pRspUserLogin else 0,
                session_id=pRspUserLogin.SessionID if pRspUserLogin else 0
            )
            self.gateway._on_login_success(pRspUserLogin)

    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
        """登出响应"""
        self.logger.log_system("用户登出", {
            "investor_id": pUserLogout.UserID if pUserLogout else ""
        })

    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
        """报单录入响应（错误时）"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.logger.log_error(
                "报单失败",
                error_code=pRspInfo.ErrorID,
                error_msg=pRspInfo.ErrorMsg,
                instrument_id=pInputOrder.InstrumentID if pInputOrder else ""
            )
            self.gateway._on_order_error(pInputOrder, pRspInfo)

    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        """撤单响应（错误时）"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.logger.log_error(
                "撤单失败",
                error_code=pRspInfo.ErrorID,
                error_msg=pRspInfo.ErrorMsg,
                order_ref=pInputOrderAction.OrderRef if pInputOrderAction else ""
            )
            self.gateway._on_cancel_error(pInputOrderAction, pRspInfo)

    def OnRtnOrder(self, pOrder):
        """报单回报"""
        if pOrder:
            self.logger.log_order_status(
                order_ref=pOrder.OrderRef,
                status=pOrder.OrderStatus,
                status_msg=pOrder.StatusMsg,
                instrument_id=pOrder.InstrumentID,
                direction=pOrder.Direction,
                offset=pOrder.CombOffsetFlag,
                volume_total=pOrder.VolumeTotal,
                volume_traded=pOrder.VolumeTraded
            )
            self.gateway._on_order(pOrder)

    def OnRtnTrade(self, pTrade):
        """成交回报"""
        if pTrade:
            self.logger.log_trade(
                instrument_id=pTrade.InstrumentID,
                direction=pTrade.Direction,
                offset=pTrade.OffsetFlag,
                price=pTrade.Price,
                volume=pTrade.Volume,
                trade_id=pTrade.TradeID,
                order_ref=pTrade.OrderRef
            )
            self.gateway._on_trade(pTrade)

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        """报单错误回报"""
        if pRspInfo:
            self.logger.log_error(
                "报单错误回报",
                error_code=pRspInfo.ErrorID,
                error_msg=pRspInfo.ErrorMsg
            )

    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo):
        """撤单错误回报"""
        if pRspInfo:
            self.logger.log_error(
                "撤单错误回报",
                error_code=pRspInfo.ErrorID,
                error_msg=pRspInfo.ErrorMsg
            )

    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast):
        """查询合约响应"""
        if pInstrument:
            self.gateway._on_instrument(pInstrument)
        if bIsLast:
            self.gateway._on_instrument_query_complete()

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        """查询资金账户响应"""
        if pTradingAccount:
            self.gateway._on_account(pTradingAccount)

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        """查询持仓响应"""
        if pInvestorPosition:
            self.gateway._on_position(pInvestorPosition)
        if bIsLast:
            self.gateway._on_position_query_complete()

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        """结算单确认响应"""
        self.logger.log_system("结算单确认完成")
        self.gateway._on_settlement_confirmed()

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        """错误响应"""
        if pRspInfo:
            self.logger.log_error(
                "CTP错误",
                error_code=pRspInfo.ErrorID,
                error_msg=pRspInfo.ErrorMsg
            )


class CtpGateway:
    """
    CTP交易网关
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
        self._td_api = None
        self._md_api = None
        self._spi = None

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
        self._account: Optional[Any] = None
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
        if tdapi is None:
            self.logger.log_error("CTP API未安装，请安装openctp-ctp")
            return False

        self.logger.log_system("开始连接CTP服务器", {
            "trade_front": self.config.trade_front
        })

        # 创建流文件目录
        os.makedirs(self.config.flow_path, exist_ok=True)

        # 创建API实例
        self._td_api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi(
            self.config.flow_path
        )

        # 创建SPI实例
        self._spi = CtpTraderSpi(self)

        # 注册SPI
        self._td_api.RegisterSpi(self._spi)

        # 注册前置
        self._td_api.RegisterFront(self.config.trade_front)

        # 订阅私有流和公有流
        self._td_api.SubscribePrivateTopic(2)  # THOST_TERT_QUICK
        self._td_api.SubscribePublicTopic(2)

        # 初始化连接
        self._connect_event.clear()
        self._td_api.Init()

        # 等待连接
        if not self._connect_event.wait(timeout):
            self.logger.log_error("连接超时")
            return False

        return self._connected

    def _on_front_connected(self):
        """连接成功回调处理"""
        self._connected = True
        self._connect_event.set()

        # 触发回调
        for callback in self._callbacks.get("on_connected", []):
            try:
                callback()
            except Exception as e:
                self.logger.log_exception(e, "on_connected callback")

    def _on_front_disconnected(self, reason: int):
        """连接断开回调处理"""
        self._connected = False
        self._authenticated = False
        self._logged_in = False

        # 触发回调
        for callback in self._callbacks.get("on_disconnected", []):
            try:
                callback(reason)
            except Exception as e:
                self.logger.log_exception(e, "on_disconnected callback")

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

        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID = self.config.broker_id
        req.UserID = self.config.investor_id
        req.AppID = self.config.app_id
        req.AuthCode = self.config.auth_code

        self._auth_event.clear()
        ret = self._td_api.ReqAuthenticate(req, self._get_request_id())

        if ret != 0:
            self.logger.log_error("认证请求发送失败", error_code=ret)
            return False

        if not self._auth_event.wait(timeout):
            self.logger.log_error("认证超时")
            return False

        return self._authenticated

    def _on_authenticate_success(self):
        """认证成功"""
        self._authenticated = True
        self._auth_event.set()

    def _on_authenticate_failed(self, error_code: int, error_msg: str):
        """认证失败"""
        self._authenticated = False
        self._auth_event.set()

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

        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.config.broker_id
        req.UserID = self.config.investor_id
        req.Password = self.config.password

        self._login_event.clear()
        ret = self._td_api.ReqUserLogin(req, self._get_request_id())

        if ret != 0:
            self.logger.log_error("登录请求发送失败", error_code=ret)
            return False

        if not self._login_event.wait(timeout):
            self.logger.log_error("登录超时")
            return False

        return self._logged_in

    def _on_login_success(self, login_info):
        """登录成功"""
        self._logged_in = True
        if login_info:
            self._front_id = login_info.FrontID
            self._session_id = login_info.SessionID
            self._trading_day = login_info.TradingDay
            self._order_ref = int(login_info.MaxOrderRef) if login_info.MaxOrderRef else 0
        self._login_event.set()

    def _on_login_failed(self, error_code: int, error_msg: str):
        """登录失败"""
        self._logged_in = False
        self._login_event.set()

    def confirm_settlement(self, timeout: int = 10) -> bool:
        """确认结算单"""
        if not self._logged_in:
            return False

        req = tdapi.CThostFtdcSettlementInfoConfirmField()
        req.BrokerID = self.config.broker_id
        req.InvestorID = self.config.investor_id

        self._settlement_event.clear()
        ret = self._td_api.ReqSettlementInfoConfirm(req, self._get_request_id())

        if ret != 0:
            return False

        return self._settlement_event.wait(timeout)

    def _on_settlement_confirmed(self):
        """结算单确认完成"""
        self._settlement_event.set()

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

        req = tdapi.CThostFtdcInputOrderActionField()
        req.BrokerID = self.config.broker_id
        req.InvestorID = self.config.investor_id
        req.InstrumentID = instrument_id
        req.OrderRef = order_ref
        req.FrontID = self._front_id
        req.SessionID = self._session_id
        req.ActionFlag = '0'  # 撤单

        if exchange_id:
            req.ExchangeID = exchange_id
        if order_sys_id:
            req.OrderSysID = order_sys_id

        ret = self._td_api.ReqOrderAction(req, self._get_request_id())

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

        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = self.config.broker_id
        req.InvestorID = self.config.investor_id
        req.InstrumentID = instrument_id
        req.OrderRef = order_ref
        req.Direction = direction.value
        req.CombOffsetFlag = offset.value
        req.CombHedgeFlag = '1'  # 投机
        req.LimitPrice = price
        req.VolumeTotalOriginal = volume
        req.OrderPriceType = '2'  # 限价
        req.TimeCondition = '3'   # 当日有效
        req.VolumeCondition = '1' # 任意数量
        req.ContingentCondition = '1'  # 立即
        req.ForceCloseReason = '0'  # 非强平
        req.IsAutoSuspend = 0
        req.MinVolume = 1

        ret = self._td_api.ReqOrderInsert(req, self._get_request_id())

        if ret != 0:
            self.logger.log_error("报单请求发送失败", error_code=ret)
            return None

        return order_ref

    def _on_order(self, order):
        """订单回报处理"""
        if order:
            self._orders[order.OrderRef] = order
            for callback in self._callbacks.get("on_order", []):
                try:
                    callback(order)
                except Exception as e:
                    self.logger.log_exception(e, "on_order callback")

    def _on_trade(self, trade):
        """成交回报处理"""
        for callback in self._callbacks.get("on_trade", []):
            try:
                callback(trade)
            except Exception as e:
                self.logger.log_exception(e, "on_trade callback")

    def _on_order_error(self, order, rsp_info):
        """报单错误处理"""
        for callback in self._callbacks.get("on_error", []):
            try:
                callback("order_error", order, rsp_info)
            except Exception as e:
                self.logger.log_exception(e, "on_error callback")

    def _on_cancel_error(self, action, rsp_info):
        """撤单错误处理"""
        for callback in self._callbacks.get("on_error", []):
            try:
                callback("cancel_error", action, rsp_info)
            except Exception as e:
                self.logger.log_exception(e, "on_error callback")

    # ==================== 查询功能 ====================

    def query_instruments(self, timeout: int = 30) -> Dict[str, Any]:
        """查询合约"""
        if not self._logged_in:
            return {}

        req = tdapi.CThostFtdcQryInstrumentField()
        self._instruments.clear()
        self._instrument_event.clear()

        ret = self._td_api.ReqQryInstrument(req, self._get_request_id())
        if ret != 0:
            return {}

        self._instrument_event.wait(timeout)
        return self._instruments

    def _on_instrument(self, instrument):
        """合约查询回调"""
        if instrument:
            self._instruments[instrument.InstrumentID] = {
                "instrument_id": instrument.InstrumentID,
                "exchange_id": instrument.ExchangeID,
                "instrument_name": instrument.InstrumentName,
                "product_class": instrument.ProductClass,
                "volume_multiple": instrument.VolumeMultiple,
                "price_tick": instrument.PriceTick,
                "max_order_volume": instrument.MaxLimitOrderVolume,
                "min_order_volume": instrument.MinLimitOrderVolume,
            }

    def _on_instrument_query_complete(self):
        """合约查询完成"""
        self.settings.instruments = self._instruments
        self._instrument_event.set()

    def query_account(self) -> Optional[Dict]:
        """查询资金账户"""
        if not self._logged_in:
            return None

        req = tdapi.CThostFtdcQryTradingAccountField()
        req.BrokerID = self.config.broker_id
        req.InvestorID = self.config.investor_id

        ret = self._td_api.ReqQryTradingAccount(req, self._get_request_id())
        if ret != 0:
            return None

        time.sleep(1)  # 等待响应
        return self._account

    def _on_account(self, account):
        """资金账户查询回调"""
        if account:
            self._account = {
                "available": account.Available,
                "balance": account.Balance,
                "frozen_margin": account.FrozenMargin,
                "frozen_commission": account.FrozenCommission,
            }

    def query_position(self) -> Dict[str, Any]:
        """查询持仓"""
        if not self._logged_in:
            return {}

        req = tdapi.CThostFtdcQryInvestorPositionField()
        req.BrokerID = self.config.broker_id
        req.InvestorID = self.config.investor_id

        self._positions.clear()
        ret = self._td_api.ReqQryInvestorPosition(req, self._get_request_id())
        if ret != 0:
            return {}

        time.sleep(1)  # 等待响应
        return self._positions

    def _on_position(self, position):
        """持仓查询回调"""
        if position and position.InstrumentID:
            key = f"{position.InstrumentID}_{position.PosiDirection}"
            self._positions[key] = {
                "instrument_id": position.InstrumentID,
                "direction": position.PosiDirection,
                "position": position.Position,
                "today_position": position.TodayPosition,
                "yd_position": position.YdPosition,
            }

    def _on_position_query_complete(self):
        """持仓查询完成"""
        pass

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
        if self._td_api:
            self._td_api.Release()
            self._td_api = None
        self._connected = False
        self._authenticated = False
        self._logged_in = False
