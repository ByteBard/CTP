"""
CTP API Python 封装
基于 ctypes 调用 ctp_wrapper.dll

作者: CTP Wrapper
版本: 2.0.0 (对应CTP v6.6.8) - 完整功能版

功能列表:
    - 连接管理: 连接/断开/心跳
    - 认证登录: 认证/登录/登出/改密
    - 结算管理: 结算确认/结算查询
    - 交易功能: 报单/撤单
    - 查询功能: 持仓/资金/订单/成交/合约/行情/保证金率/手续费率
    - 回调处理: 报单回报/成交回报/错误回报
"""

import os
import sys
import ctypes
from ctypes import (
    CDLL, CFUNCTYPE, POINTER,
    c_void_p, c_char_p, c_int, c_double, c_char,
    Structure, byref
)
from typing import Callable, Optional
from datetime import datetime


# ============================================================
# 日志工具
# ============================================================
class Logger:
    """简单的日志记录器"""

    def __init__(self, name: str = "CTP"):
        self.name = name
        self.start_time = datetime.now()

    def _log(self, level: str, msg: str):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] [{level:5}] (+{elapsed:6.2f}s) {msg}")

    def info(self, msg: str):
        self._log("INFO", msg)

    def ok(self, msg: str):
        self._log("OK", msg)

    def error(self, msg: str):
        self._log("ERROR", msg)

    def warn(self, msg: str):
        self._log("WARN", msg)


log = Logger()


# ============================================================
# 常量定义
# ============================================================

# 订阅模式
class ResumeType:
    """订阅重传模式"""
    RESTART = 0  # 从本交易日开始重传
    RESUME = 1   # 从上次收到的续传
    QUICK = 2    # 只传送登录后的流内容
    NONE = 3     # 取消订阅


# 买卖方向
class Direction:
    """买卖方向"""
    BUY = ord('0')   # 买
    SELL = ord('1')  # 卖


# 开平标志
class OffsetFlag:
    """开平标志"""
    OPEN = ord('0')         # 开仓
    CLOSE = ord('1')        # 平仓
    FORCE_CLOSE = ord('2')  # 强平
    CLOSE_TODAY = ord('3')  # 平今
    CLOSE_YESTERDAY = ord('4')  # 平昨
    FORCE_OFF = ord('5')    # 强减
    LOCAL_FORCE_CLOSE = ord('6')  # 本地强平


# 报单价格类型
class OrderPriceType:
    """报单价格类型"""
    ANY_PRICE = ord('1')           # 任意价
    LIMIT_PRICE = ord('2')         # 限价
    BEST_PRICE = ord('3')          # 最优价
    LAST_PRICE = ord('4')          # 最新价
    LAST_PRICE_PLUS_ONE = ord('5') # 最新价浮动上浮1个ticks
    LAST_PRICE_PLUS_TWO = ord('6') # 最新价浮动上浮2个ticks
    LAST_PRICE_PLUS_THREE = ord('7')  # 最新价浮动上浮3个ticks
    ASK_PRICE1 = ord('8')          # 卖一价
    ASK_PRICE1_PLUS_ONE = ord('9') # 卖一价浮动上浮1个ticks
    BID_PRICE1 = ord('A')          # 买一价
    FIVE_LEVEL_PRICE = ord('G')    # 五档价


# 有效期类型
class TimeCondition:
    """有效期类型"""
    IOC = ord('1')  # 立即完成，否则撤销
    GFS = ord('2')  # 本节有效
    GFD = ord('3')  # 当日有效
    GTD = ord('4')  # 指定日期前有效
    GTC = ord('5')  # 撤销前有效
    GFA = ord('6')  # 集合竞价有效


# 成交量类型
class VolumeCondition:
    """成交量类型"""
    ANY = ord('1')  # 任何数量
    MIN = ord('2')  # 最小数量
    ALL = ord('3')  # 全部数量


# 报单状态
class OrderStatus:
    """报单状态"""
    ALL_TRADED = ord('0')       # 全部成交
    PART_TRADED_QUEUEING = ord('1')  # 部分成交还在队列中
    PART_TRADED_NOT_QUEUEING = ord('2')  # 部分成交不在队列中
    NO_TRADE_QUEUEING = ord('3')     # 未成交还在队列中
    NO_TRADE_NOT_QUEUEING = ord('4') # 未成交不在队列中
    CANCELED = ord('5')         # 撤单
    UNKNOWN = ord('a')          # 未知
    NOT_TOUCHED = ord('b')      # 尚未触发
    TOUCHED = ord('c')          # 已触发

    @staticmethod
    def to_string(status: int) -> str:
        """将状态码转换为可读字符串"""
        status_map = {
            ord('0'): "全部成交",
            ord('1'): "部分成交(排队中)",
            ord('2'): "部分成交(已撤)",
            ord('3'): "未成交(排队中)",
            ord('4'): "未成交(已撤)",
            ord('5'): "已撤单",
            ord('a'): "未知",
            ord('b'): "尚未触发",
            ord('c'): "已触发",
        }
        return status_map.get(status, f"未知({chr(status)})")


# 持仓多空方向
class PositionDirection:
    """持仓多空方向"""
    NET = ord('1')    # 净
    LONG = ord('2')   # 多头
    SHORT = ord('3')  # 空头

    @staticmethod
    def to_string(direction: int) -> str:
        """将方向转换为可读字符串"""
        direction_map = {
            ord('1'): "净",
            ord('2'): "多",
            ord('3'): "空",
        }
        return direction_map.get(direction, f"未知({chr(direction)})")


# ============================================================
# 回调函数类型定义
# ============================================================

# 连接回调
OnFrontConnectedCallback = CFUNCTYPE(None)
OnFrontDisconnectedCallback = CFUNCTYPE(None, c_int)
OnHeartBeatWarningCallback = CFUNCTYPE(None, c_int)

# 认证登录回调
OnRspAuthenticateCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspUserLoginCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_int, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspUserLogoutCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspUserPasswordUpdateCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspErrorCallback = CFUNCTYPE(
    None, c_int, c_char_p, c_int, c_int)

# 结算回调
OnRspSettlementInfoConfirmCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspQrySettlementInfoCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

# 报单相关回调
OnRspOrderInsertCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char, c_char, c_double, c_int,
    c_int, c_char_p, c_int, c_int)

OnRspOrderActionCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_int, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRtnOrderCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char_p, c_char, c_char, c_double, c_int, c_int,
    c_char, c_char_p, c_int, c_int,
    c_char_p, c_char_p, c_char_p)

OnRtnTradeCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char_p, c_char_p, c_char, c_char,
    c_double, c_int, c_char_p, c_char_p, c_char_p)

OnErrRtnOrderInsertCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char, c_char, c_double, c_int,
    c_int, c_char_p)

OnErrRtnOrderActionCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p)

# 查询响应回调
OnRspQryOrderCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char, c_char, c_double, c_int, c_int,
    c_char, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspQryTradeCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_char, c_char, c_double, c_int,
    c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspQryInvestorPositionCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char,
    c_int, c_int, c_double, c_double,
    c_double, c_double,
    c_int, c_char_p, c_int, c_int)

OnRspQryTradingAccountCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_double, c_double, c_double,
    c_double, c_double, c_double,
    c_double, c_double,
    c_int, c_char_p, c_int, c_int)

OnRspQryInstrumentCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_double, c_double, c_double, c_int,
    c_int, c_char_p, c_int, c_int)

OnRspQryDepthMarketDataCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_double, c_double, c_double, c_double, c_double,
    c_int, c_double, c_double,
    c_double, c_int, c_double, c_int,
    c_char_p,
    c_int, c_char_p, c_int, c_int)

OnRspQryInstrumentMarginRateCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p,
    c_double, c_double, c_double, c_double,
    c_int, c_char_p, c_int, c_int)

OnRspQryInstrumentCommissionRateCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p,
    c_double, c_double, c_double, c_double, c_double, c_double,
    c_int, c_char_p, c_int, c_int)


# ============================================================
# 回调结构体
# ============================================================
class TraderCallbacks(Structure):
    """回调函数结构体，必须与C++端TraderCallbacks结构体完全一致"""
    _fields_ = [
        # 连接相关
        ("on_front_connected", OnFrontConnectedCallback),
        ("on_front_disconnected", OnFrontDisconnectedCallback),
        ("on_heartbeat_warning", OnHeartBeatWarningCallback),
        # 认证登录
        ("on_rsp_authenticate", OnRspAuthenticateCallback),
        ("on_rsp_user_login", OnRspUserLoginCallback),
        ("on_rsp_user_logout", OnRspUserLogoutCallback),
        ("on_rsp_user_password_update", OnRspUserPasswordUpdateCallback),
        ("on_rsp_error", OnRspErrorCallback),
        # 结算
        ("on_rsp_settlement_info_confirm", OnRspSettlementInfoConfirmCallback),
        ("on_rsp_qry_settlement_info", OnRspQrySettlementInfoCallback),
        # 报单相关
        ("on_rsp_order_insert", OnRspOrderInsertCallback),
        ("on_rsp_order_action", OnRspOrderActionCallback),
        ("on_rtn_order", OnRtnOrderCallback),
        ("on_rtn_trade", OnRtnTradeCallback),
        ("on_err_rtn_order_insert", OnErrRtnOrderInsertCallback),
        ("on_err_rtn_order_action", OnErrRtnOrderActionCallback),
        # 查询响应
        ("on_rsp_qry_order", OnRspQryOrderCallback),
        ("on_rsp_qry_trade", OnRspQryTradeCallback),
        ("on_rsp_qry_investor_position", OnRspQryInvestorPositionCallback),
        ("on_rsp_qry_trading_account", OnRspQryTradingAccountCallback),
        ("on_rsp_qry_instrument", OnRspQryInstrumentCallback),
        ("on_rsp_qry_depth_market_data", OnRspQryDepthMarketDataCallback),
        ("on_rsp_qry_instrument_margin_rate", OnRspQryInstrumentMarginRateCallback),
        ("on_rsp_qry_instrument_commission_rate", OnRspQryInstrumentCommissionRateCallback),
    ]


# ============================================================
# CTP Trader API 封装类
# ============================================================
class CTPTraderApi:
    """
    CTP 交易 API 封装

    使用示例:
        api = CTPTraderApi()
        api.on_front_connected = my_on_connected
        api.on_rsp_user_login = my_on_login
        api.create_api("./flow/")
        api.register_front("tcp://127.0.0.1:17001")
        api.subscribe_private_topic(ResumeType.QUICK)
        api.init()
    """

    def __init__(self, dll_path: str = None):
        """
        初始化 CTP API

        Args:
            dll_path: ctp_wrapper.dll 的路径，默认为当前目录
        """
        self._api = None
        self._dll = None
        self._callbacks = None
        self._callback_refs = []  # 保持回调引用，防止被垃圾回收

        # ========== 用户回调函数 ==========
        # 连接相关
        self.on_front_connected: Optional[Callable] = None
        self.on_front_disconnected: Optional[Callable[[int], None]] = None
        self.on_heartbeat_warning: Optional[Callable[[int], None]] = None

        # 认证登录
        self.on_rsp_authenticate: Optional[Callable] = None
        self.on_rsp_user_login: Optional[Callable] = None
        self.on_rsp_user_logout: Optional[Callable] = None
        self.on_rsp_user_password_update: Optional[Callable] = None
        self.on_rsp_error: Optional[Callable] = None

        # 结算
        self.on_rsp_settlement_info_confirm: Optional[Callable] = None
        self.on_rsp_qry_settlement_info: Optional[Callable] = None

        # 报单相关
        self.on_rsp_order_insert: Optional[Callable] = None
        self.on_rsp_order_action: Optional[Callable] = None
        self.on_rtn_order: Optional[Callable] = None
        self.on_rtn_trade: Optional[Callable] = None
        self.on_err_rtn_order_insert: Optional[Callable] = None
        self.on_err_rtn_order_action: Optional[Callable] = None

        # 查询响应
        self.on_rsp_qry_order: Optional[Callable] = None
        self.on_rsp_qry_trade: Optional[Callable] = None
        self.on_rsp_qry_investor_position: Optional[Callable] = None
        self.on_rsp_qry_trading_account: Optional[Callable] = None
        self.on_rsp_qry_instrument: Optional[Callable] = None
        self.on_rsp_qry_depth_market_data: Optional[Callable] = None
        self.on_rsp_qry_instrument_margin_rate: Optional[Callable] = None
        self.on_rsp_qry_instrument_commission_rate: Optional[Callable] = None

        # 加载DLL
        self._load_dll(dll_path)

    def _load_dll(self, dll_path: str = None):
        """加载 DLL"""
        if dll_path is None:
            dll_path = os.path.dirname(os.path.abspath(__file__))

        # 添加DLL目录到搜索路径
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(dll_path)

        wrapper_dll = os.path.join(dll_path, "ctp_wrapper.dll")

        if not os.path.exists(wrapper_dll):
            raise FileNotFoundError(f"ctp_wrapper.dll not found at {wrapper_dll}")

        log.info(f"Loading DLL: {wrapper_dll}")

        try:
            self._dll = CDLL(wrapper_dll)
            self._setup_functions()
            log.ok("DLL loaded successfully")
        except Exception as e:
            log.error(f"Failed to load DLL: {e}")
            raise

    def _setup_functions(self):
        """设置 DLL 函数签名"""
        # ========== 基础函数 ==========
        self._dll.CreateTraderApi.argtypes = [c_char_p]
        self._dll.CreateTraderApi.restype = c_void_p

        self._dll.ReleaseTraderApi.argtypes = [c_void_p]
        self._dll.ReleaseTraderApi.restype = None

        self._dll.GetApiVersion.argtypes = []
        self._dll.GetApiVersion.restype = c_char_p

        self._dll.RegisterCallbacks.argtypes = [c_void_p, POINTER(TraderCallbacks)]
        self._dll.RegisterCallbacks.restype = None

        self._dll.RegisterFront.argtypes = [c_void_p, c_char_p]
        self._dll.RegisterFront.restype = None

        self._dll.SubscribePrivateTopic.argtypes = [c_void_p, c_int]
        self._dll.SubscribePrivateTopic.restype = None

        self._dll.SubscribePublicTopic.argtypes = [c_void_p, c_int]
        self._dll.SubscribePublicTopic.restype = None

        self._dll.Init.argtypes = [c_void_p]
        self._dll.Init.restype = None

        self._dll.Join.argtypes = [c_void_p]
        self._dll.Join.restype = c_int

        self._dll.GetTradingDay.argtypes = [c_void_p]
        self._dll.GetTradingDay.restype = c_char_p

        # ========== 认证登录 ==========
        self._dll.ReqAuthenticate.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqAuthenticate.restype = c_int

        self._dll.ReqUserLogin.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqUserLogin.restype = c_int

        self._dll.ReqUserLogout.argtypes = [
            c_void_p, c_char_p, c_char_p, c_int]
        self._dll.ReqUserLogout.restype = c_int

        self._dll.ReqUserPasswordUpdate.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqUserPasswordUpdate.restype = c_int

        # ========== 结算 ==========
        self._dll.ReqSettlementInfoConfirm.argtypes = [
            c_void_p, c_char_p, c_char_p, c_int]
        self._dll.ReqSettlementInfoConfirm.restype = c_int

        self._dll.ReqQrySettlementInfo.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQrySettlementInfo.restype = c_int

        # ========== 交易 ==========
        self._dll.ReqOrderInsert.argtypes = [
            c_void_p, c_char_p, c_char_p,
            c_char_p, c_char_p,
            c_char, c_char,
            c_double, c_int,
            c_char, c_char, c_char,
            c_int]
        self._dll.ReqOrderInsert.restype = c_int

        self._dll.ReqOrderAction.argtypes = [
            c_void_p, c_char_p, c_char_p,
            c_char_p, c_char_p,
            c_char_p, c_int, c_int,
            c_char_p, c_int]
        self._dll.ReqOrderAction.restype = c_int

        # ========== 查询 ==========
        self._dll.ReqQryOrder.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryOrder.restype = c_int

        self._dll.ReqQryTrade.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryTrade.restype = c_int

        self._dll.ReqQryInvestorPosition.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryInvestorPosition.restype = c_int

        self._dll.ReqQryTradingAccount.argtypes = [
            c_void_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryTradingAccount.restype = c_int

        self._dll.ReqQryInstrument.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryInstrument.restype = c_int

        self._dll.ReqQryDepthMarketData.argtypes = [
            c_void_p, c_char_p, c_int]
        self._dll.ReqQryDepthMarketData.restype = c_int

        self._dll.ReqQryInstrumentMarginRate.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryInstrumentMarginRate.restype = c_int

        self._dll.ReqQryInstrumentCommissionRate.argtypes = [
            c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.ReqQryInstrumentCommissionRate.restype = c_int

    def _decode(self, s) -> str:
        """解码GBK字符串"""
        if s:
            return s.decode('gbk') if isinstance(s, bytes) else str(s)
        return ""

    def _create_callbacks(self):
        """创建内部回调函数"""
        self._callback_refs.clear()

        # ========== 连接相关 ==========
        def _on_front_connected():
            log.ok("OnFrontConnected - 服务器连接成功")
            if self.on_front_connected:
                self.on_front_connected()

        def _on_front_disconnected(reason):
            reason_map = {
                0x1001: "网络读失败",
                0x1002: "网络写失败",
                0x2001: "接收心跳超时",
                0x2002: "发送心跳失败",
                0x2003: "收到错误报文",
            }
            reason_str = reason_map.get(reason, f"未知({hex(reason)})")
            log.warn(f"OnFrontDisconnected - 连接断开, 原因: {reason_str}")
            if self.on_front_disconnected:
                self.on_front_disconnected(reason)

        def _on_heartbeat_warning(time_lapse):
            log.warn(f"OnHeartBeatWarning - 心跳超时警告: {time_lapse}秒")
            if self.on_heartbeat_warning:
                self.on_heartbeat_warning(time_lapse)

        # ========== 认证登录 ==========
        def _on_rsp_authenticate(broker_id, user_id, app_id,
                                  error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            app_id = self._decode(app_id)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspAuthenticate - 认证失败: [{error_id}] {error_msg}")
            else:
                log.ok("OnRspAuthenticate - 认证成功")

            if self.on_rsp_authenticate:
                self.on_rsp_authenticate(
                    broker_id, user_id, app_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_user_login(trading_day, login_time, broker_id, user_id,
                               front_id, session_id, max_order_ref,
                               error_id, error_msg, request_id, is_last):
            trading_day = self._decode(trading_day)
            login_time = self._decode(login_time)
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            max_order_ref = self._decode(max_order_ref)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspUserLogin - 登录失败: [{error_id}] {error_msg}")
            else:
                log.ok(f"OnRspUserLogin - 登录成功: 交易日={trading_day}, "
                      f"FrontID={front_id}, SessionID={session_id}")

            if self.on_rsp_user_login:
                self.on_rsp_user_login(
                    trading_day, login_time, broker_id, user_id,
                    front_id, session_id, max_order_ref,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_user_logout(broker_id, user_id,
                                error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspUserLogout - 登出失败: [{error_id}] {error_msg}")
            else:
                log.ok("OnRspUserLogout - 登出成功")

            if self.on_rsp_user_logout:
                self.on_rsp_user_logout(
                    broker_id, user_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_user_password_update(broker_id, user_id,
                                          error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspUserPasswordUpdate - 密码修改失败: [{error_id}] {error_msg}")
            else:
                log.ok("OnRspUserPasswordUpdate - 密码修改成功")

            if self.on_rsp_user_password_update:
                self.on_rsp_user_password_update(
                    broker_id, user_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_error(error_id, error_msg, request_id, is_last):
            error_msg = self._decode(error_msg)
            log.error(f"OnRspError - [{error_id}] {error_msg}")
            if self.on_rsp_error:
                self.on_rsp_error(error_id, error_msg, request_id, bool(is_last))

        # ========== 结算 ==========
        def _on_rsp_settlement_info_confirm(broker_id, investor_id,
                                             confirm_date, confirm_time,
                                             error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            confirm_date = self._decode(confirm_date)
            confirm_time = self._decode(confirm_time)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspSettlementInfoConfirm - 确认失败: [{error_id}] {error_msg}")
            else:
                log.ok(f"OnRspSettlementInfoConfirm - 结算确认成功: {confirm_date} {confirm_time}")

            if self.on_rsp_settlement_info_confirm:
                self.on_rsp_settlement_info_confirm(
                    broker_id, investor_id, confirm_date, confirm_time,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_settlement_info(broker_id, investor_id, trading_day, content,
                                         error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            trading_day = self._decode(trading_day)
            content = self._decode(content)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspQrySettlementInfo - 查询失败: [{error_id}] {error_msg}")

            if self.on_rsp_qry_settlement_info:
                self.on_rsp_qry_settlement_info(
                    broker_id, investor_id, trading_day, content,
                    error_id, error_msg, request_id, bool(is_last))

        # ========== 报单相关 ==========
        def _on_rsp_order_insert(broker_id, investor_id, instrument_id, order_ref,
                                  direction, offset_flag, price, volume,
                                  error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspOrderInsert - 报单失败: [{error_id}] {error_msg} "
                         f"合约={instrument_id}")

            if self.on_rsp_order_insert:
                self.on_rsp_order_insert(
                    broker_id, investor_id, instrument_id, order_ref,
                    direction, offset_flag, price, volume,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_order_action(broker_id, investor_id, instrument_id, order_ref,
                                  front_id, session_id, order_sys_id,
                                  error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            order_sys_id = self._decode(order_sys_id)
            error_msg = self._decode(error_msg)

            if error_id != 0:
                log.error(f"OnRspOrderAction - 撤单失败: [{error_id}] {error_msg}")

            if self.on_rsp_order_action:
                self.on_rsp_order_action(
                    broker_id, investor_id, instrument_id, order_ref,
                    front_id, session_id, order_sys_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rtn_order(broker_id, investor_id, instrument_id, order_ref,
                          user_id, direction, offset_flag, price, volume_total, volume_traded,
                          order_status, order_sys_id, front_id, session_id,
                          insert_date, insert_time, status_msg):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            user_id = self._decode(user_id)
            order_sys_id = self._decode(order_sys_id)
            insert_date = self._decode(insert_date)
            insert_time = self._decode(insert_time)
            status_msg = self._decode(status_msg)

            dir_str = "买" if direction == ord('0') else "卖"
            status_str = OrderStatus.to_string(order_status)
            log.info(f"OnRtnOrder - {instrument_id} {dir_str} "
                    f"价格={price} 数量={volume_total} 已成={volume_traded} "
                    f"状态={status_str}")

            if self.on_rtn_order:
                self.on_rtn_order(
                    broker_id, investor_id, instrument_id, order_ref,
                    user_id, direction, offset_flag, price, volume_total, volume_traded,
                    order_status, order_sys_id, front_id, session_id,
                    insert_date, insert_time, status_msg)

        def _on_rtn_trade(broker_id, investor_id, instrument_id, order_ref,
                          user_id, trade_id, direction, offset_flag,
                          price, volume, trade_date, trade_time, order_sys_id):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            user_id = self._decode(user_id)
            trade_id = self._decode(trade_id)
            trade_date = self._decode(trade_date)
            trade_time = self._decode(trade_time)
            order_sys_id = self._decode(order_sys_id)

            dir_str = "买" if direction == ord('0') else "卖"
            log.ok(f"OnRtnTrade - 成交! {instrument_id} {dir_str} "
                  f"价格={price} 数量={volume} 成交号={trade_id}")

            if self.on_rtn_trade:
                self.on_rtn_trade(
                    broker_id, investor_id, instrument_id, order_ref,
                    user_id, trade_id, direction, offset_flag,
                    price, volume, trade_date, trade_time, order_sys_id)

        def _on_err_rtn_order_insert(broker_id, investor_id, instrument_id, order_ref,
                                      direction, offset_flag, price, volume,
                                      error_id, error_msg):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            error_msg = self._decode(error_msg)

            log.error(f"OnErrRtnOrderInsert - 报单错误: [{error_id}] {error_msg} "
                     f"合约={instrument_id}")

            if self.on_err_rtn_order_insert:
                self.on_err_rtn_order_insert(
                    broker_id, investor_id, instrument_id, order_ref,
                    direction, offset_flag, price, volume,
                    error_id, error_msg)

        def _on_err_rtn_order_action(broker_id, investor_id, instrument_id, order_sys_id,
                                      error_id, error_msg):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_sys_id = self._decode(order_sys_id)
            error_msg = self._decode(error_msg)

            log.error(f"OnErrRtnOrderAction - 撤单错误: [{error_id}] {error_msg}")

            if self.on_err_rtn_order_action:
                self.on_err_rtn_order_action(
                    broker_id, investor_id, instrument_id, order_sys_id,
                    error_id, error_msg)

        # ========== 查询响应 ==========
        def _on_rsp_qry_order(broker_id, investor_id, instrument_id, order_ref,
                               direction, offset_flag, price, volume_total, volume_traded,
                               order_status, order_sys_id, insert_date, insert_time,
                               error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            order_ref = self._decode(order_ref)
            order_sys_id = self._decode(order_sys_id)
            insert_date = self._decode(insert_date)
            insert_time = self._decode(insert_time)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_order:
                self.on_rsp_qry_order(
                    broker_id, investor_id, instrument_id, order_ref,
                    direction, offset_flag, price, volume_total, volume_traded,
                    order_status, order_sys_id, insert_date, insert_time,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_trade(broker_id, investor_id, instrument_id, trade_id,
                               direction, offset_flag, price, volume,
                               trade_date, trade_time,
                               error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            trade_id = self._decode(trade_id)
            trade_date = self._decode(trade_date)
            trade_time = self._decode(trade_time)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_trade:
                self.on_rsp_qry_trade(
                    broker_id, investor_id, instrument_id, trade_id,
                    direction, offset_flag, price, volume,
                    trade_date, trade_time,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_investor_position(broker_id, investor_id, instrument_id, position_direction,
                                           position, yd_position, position_cost, open_cost,
                                           use_margin, frozen_margin,
                                           error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_investor_position:
                self.on_rsp_qry_investor_position(
                    broker_id, investor_id, instrument_id, position_direction,
                    position, yd_position, position_cost, open_cost,
                    use_margin, frozen_margin,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_trading_account(broker_id, account_id,
                                         balance, available, frozen_cash,
                                         curr_margin, close_profit, position_profit,
                                         commission, withdraw_quota,
                                         error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            account_id = self._decode(account_id)
            error_msg = self._decode(error_msg)

            if error_id == 0 and account_id:
                log.info(f"OnRspQryTradingAccount - 账户={account_id} "
                        f"余额={balance:.2f} 可用={available:.2f} 保证金={curr_margin:.2f}")

            if self.on_rsp_qry_trading_account:
                self.on_rsp_qry_trading_account(
                    broker_id, account_id, balance, available, frozen_cash,
                    curr_margin, close_profit, position_profit,
                    commission, withdraw_quota,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_instrument(instrument_id, exchange_id, instrument_name, product_id,
                                    volume_multiple, price_tick, long_margin_ratio, short_margin_ratio,
                                    is_trading,
                                    error_id, error_msg, request_id, is_last):
            instrument_id = self._decode(instrument_id)
            exchange_id = self._decode(exchange_id)
            instrument_name = self._decode(instrument_name)
            product_id = self._decode(product_id)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_instrument:
                self.on_rsp_qry_instrument(
                    instrument_id, exchange_id, instrument_name, product_id,
                    volume_multiple, price_tick, long_margin_ratio, short_margin_ratio,
                    is_trading,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_depth_market_data(instrument_id, exchange_id,
                                           last_price, pre_settlement_price,
                                           open_price, highest_price, lowest_price,
                                           volume, turnover, open_interest,
                                           bid_price1, bid_volume1, ask_price1, ask_volume1,
                                           update_time,
                                           error_id, error_msg, request_id, is_last):
            instrument_id = self._decode(instrument_id)
            exchange_id = self._decode(exchange_id)
            update_time = self._decode(update_time)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_depth_market_data:
                self.on_rsp_qry_depth_market_data(
                    instrument_id, exchange_id, last_price, pre_settlement_price,
                    open_price, highest_price, lowest_price,
                    volume, turnover, open_interest,
                    bid_price1, bid_volume1, ask_price1, ask_volume1,
                    update_time,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_instrument_margin_rate(broker_id, investor_id, instrument_id,
                                                long_margin_ratio_by_money, long_margin_ratio_by_volume,
                                                short_margin_ratio_by_money, short_margin_ratio_by_volume,
                                                error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_instrument_margin_rate:
                self.on_rsp_qry_instrument_margin_rate(
                    broker_id, investor_id, instrument_id,
                    long_margin_ratio_by_money, long_margin_ratio_by_volume,
                    short_margin_ratio_by_money, short_margin_ratio_by_volume,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_rsp_qry_instrument_commission_rate(broker_id, investor_id, instrument_id,
                                                    open_ratio_by_money, open_ratio_by_volume,
                                                    close_ratio_by_money, close_ratio_by_volume,
                                                    close_today_ratio_by_money, close_today_ratio_by_volume,
                                                    error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            investor_id = self._decode(investor_id)
            instrument_id = self._decode(instrument_id)
            error_msg = self._decode(error_msg)

            if self.on_rsp_qry_instrument_commission_rate:
                self.on_rsp_qry_instrument_commission_rate(
                    broker_id, investor_id, instrument_id,
                    open_ratio_by_money, open_ratio_by_volume,
                    close_ratio_by_money, close_ratio_by_volume,
                    close_today_ratio_by_money, close_today_ratio_by_volume,
                    error_id, error_msg, request_id, bool(is_last))

        # ========== 创建回调对象并保持引用 ==========
        callbacks = [
            OnFrontConnectedCallback(_on_front_connected),
            OnFrontDisconnectedCallback(_on_front_disconnected),
            OnHeartBeatWarningCallback(_on_heartbeat_warning),
            OnRspAuthenticateCallback(_on_rsp_authenticate),
            OnRspUserLoginCallback(_on_rsp_user_login),
            OnRspUserLogoutCallback(_on_rsp_user_logout),
            OnRspUserPasswordUpdateCallback(_on_rsp_user_password_update),
            OnRspErrorCallback(_on_rsp_error),
            OnRspSettlementInfoConfirmCallback(_on_rsp_settlement_info_confirm),
            OnRspQrySettlementInfoCallback(_on_rsp_qry_settlement_info),
            OnRspOrderInsertCallback(_on_rsp_order_insert),
            OnRspOrderActionCallback(_on_rsp_order_action),
            OnRtnOrderCallback(_on_rtn_order),
            OnRtnTradeCallback(_on_rtn_trade),
            OnErrRtnOrderInsertCallback(_on_err_rtn_order_insert),
            OnErrRtnOrderActionCallback(_on_err_rtn_order_action),
            OnRspQryOrderCallback(_on_rsp_qry_order),
            OnRspQryTradeCallback(_on_rsp_qry_trade),
            OnRspQryInvestorPositionCallback(_on_rsp_qry_investor_position),
            OnRspQryTradingAccountCallback(_on_rsp_qry_trading_account),
            OnRspQryInstrumentCallback(_on_rsp_qry_instrument),
            OnRspQryDepthMarketDataCallback(_on_rsp_qry_depth_market_data),
            OnRspQryInstrumentMarginRateCallback(_on_rsp_qry_instrument_margin_rate),
            OnRspQryInstrumentCommissionRateCallback(_on_rsp_qry_instrument_commission_rate),
        ]

        self._callback_refs = callbacks

        # 创建回调结构体
        self._callbacks = TraderCallbacks(
            on_front_connected=callbacks[0],
            on_front_disconnected=callbacks[1],
            on_heartbeat_warning=callbacks[2],
            on_rsp_authenticate=callbacks[3],
            on_rsp_user_login=callbacks[4],
            on_rsp_user_logout=callbacks[5],
            on_rsp_user_password_update=callbacks[6],
            on_rsp_error=callbacks[7],
            on_rsp_settlement_info_confirm=callbacks[8],
            on_rsp_qry_settlement_info=callbacks[9],
            on_rsp_order_insert=callbacks[10],
            on_rsp_order_action=callbacks[11],
            on_rtn_order=callbacks[12],
            on_rtn_trade=callbacks[13],
            on_err_rtn_order_insert=callbacks[14],
            on_err_rtn_order_action=callbacks[15],
            on_rsp_qry_order=callbacks[16],
            on_rsp_qry_trade=callbacks[17],
            on_rsp_qry_investor_position=callbacks[18],
            on_rsp_qry_trading_account=callbacks[19],
            on_rsp_qry_instrument=callbacks[20],
            on_rsp_qry_depth_market_data=callbacks[21],
            on_rsp_qry_instrument_margin_rate=callbacks[22],
            on_rsp_qry_instrument_commission_rate=callbacks[23],
        )

    # ============================================================
    # 基础方法
    # ============================================================

    def create_api(self, flow_path: str = "./flow/"):
        """
        创建 API 实例

        Args:
            flow_path: 流文件存储路径
        """
        os.makedirs(flow_path, exist_ok=True)
        log.info(f"Creating API instance, flow path: {flow_path}")

        self._api = self._dll.CreateTraderApi(flow_path.encode('gbk'))

        if not self._api:
            raise RuntimeError("Failed to create API instance")

        # 创建并注册回调
        self._create_callbacks()
        self._dll.RegisterCallbacks(self._api, byref(self._callbacks))

        # 获取版本
        version = self.get_api_version()
        log.ok(f"API created successfully, version: {version}")

    def release(self):
        """释放 API 实例"""
        if self._api:
            log.info("Releasing API...")
            self._dll.ReleaseTraderApi(self._api)
            self._api = None
            log.ok("API released")

    def get_api_version(self) -> str:
        """获取 API 版本"""
        version = self._dll.GetApiVersion()
        return version.decode('gbk') if version else ""

    def register_front(self, front_address: str):
        """
        注册前置地址

        Args:
            front_address: 前置地址，如 "tcp://127.0.0.1:17001"
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Registering front: {front_address}")
        self._dll.RegisterFront(self._api, front_address.encode('gbk'))

    def subscribe_private_topic(self, resume_type: int = ResumeType.QUICK):
        """订阅私有流"""
        if not self._api:
            raise RuntimeError("API not initialized")
        self._dll.SubscribePrivateTopic(self._api, resume_type)

    def subscribe_public_topic(self, resume_type: int = ResumeType.QUICK):
        """订阅公有流"""
        if not self._api:
            raise RuntimeError("API not initialized")
        self._dll.SubscribePublicTopic(self._api, resume_type)

    def init(self):
        """初始化连接"""
        if not self._api:
            raise RuntimeError("API not initialized")
        log.info("Initializing connection...")
        self._dll.Init(self._api)

    def join(self) -> int:
        """等待线程结束"""
        if not self._api:
            return -1
        return self._dll.Join(self._api)

    def get_trading_day(self) -> str:
        """获取交易日"""
        if not self._api:
            return ""
        day = self._dll.GetTradingDay(self._api)
        return day.decode('gbk') if day else ""

    # ============================================================
    # 认证登录
    # ============================================================

    def req_authenticate(self, broker_id: str, user_id: str,
                         app_id: str, auth_code: str, request_id: int = 1) -> int:
        """
        客户端认证请求

        Args:
            broker_id: 经纪公司代码
            user_id: 用户代码
            app_id: App代码
            auth_code: 认证码
            request_id: 请求ID

        Returns:
            0 表示成功，其他表示失败
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting authentication: broker={broker_id}, user={user_id}")

        return self._dll.ReqAuthenticate(
            self._api,
            broker_id.encode('gbk'),
            user_id.encode('gbk'),
            app_id.encode('gbk'),
            auth_code.encode('gbk'),
            request_id
        )

    def req_user_login(self, broker_id: str, user_id: str,
                       password: str, request_id: int = 2) -> int:
        """
        用户登录请求

        Args:
            broker_id: 经纪公司代码
            user_id: 用户代码
            password: 密码
            request_id: 请求ID

        Returns:
            0 表示成功，其他表示失败
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting login: broker={broker_id}, user={user_id}")

        return self._dll.ReqUserLogin(
            self._api,
            broker_id.encode('gbk'),
            user_id.encode('gbk'),
            password.encode('gbk'),
            request_id
        )

    def req_user_logout(self, broker_id: str, user_id: str,
                        request_id: int = 3) -> int:
        """用户登出请求"""
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting logout: broker={broker_id}, user={user_id}")

        return self._dll.ReqUserLogout(
            self._api,
            broker_id.encode('gbk'),
            user_id.encode('gbk'),
            request_id
        )

    def req_user_password_update(self, broker_id: str, user_id: str,
                                  old_password: str, new_password: str,
                                  request_id: int = 4) -> int:
        """
        用户密码更新请求

        Args:
            broker_id: 经纪公司代码
            user_id: 用户代码
            old_password: 原密码
            new_password: 新密码
            request_id: 请求ID

        Returns:
            0 表示成功，其他表示失败
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting password update: broker={broker_id}, user={user_id}")

        return self._dll.ReqUserPasswordUpdate(
            self._api,
            broker_id.encode('gbk'),
            user_id.encode('gbk'),
            old_password.encode('gbk'),
            new_password.encode('gbk'),
            request_id
        )

    # ============================================================
    # 结算
    # ============================================================

    def req_settlement_info_confirm(self, broker_id: str, investor_id: str,
                                    request_id: int = 5) -> int:
        """结算信息确认请求"""
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting settlement confirm: broker={broker_id}, investor={investor_id}")

        return self._dll.ReqSettlementInfoConfirm(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            request_id
        )

    def req_qry_settlement_info(self, broker_id: str, investor_id: str,
                                 trading_day: str = "", request_id: int = 6) -> int:
        """
        查询结算信息

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            trading_day: 交易日（空则查询当日）
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying settlement info: broker={broker_id}, investor={investor_id}")

        return self._dll.ReqQrySettlementInfo(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            trading_day.encode('gbk') if trading_day else b"",
            request_id
        )

    # ============================================================
    # 交易
    # ============================================================

    def req_order_insert(self, broker_id: str, investor_id: str,
                         instrument_id: str, order_ref: str,
                         direction: int, offset_flag: int,
                         price: float, volume: int,
                         order_price_type: int = OrderPriceType.LIMIT_PRICE,
                         time_condition: int = TimeCondition.GFD,
                         volume_condition: int = VolumeCondition.ANY,
                         request_id: int = 10) -> int:
        """
        报单请求

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码
            order_ref: 报单引用
            direction: 买卖方向 (Direction.BUY/Direction.SELL)
            offset_flag: 开平标志 (OffsetFlag.OPEN/CLOSE/CLOSE_TODAY)
            price: 价格
            volume: 数量
            order_price_type: 报单价格类型
            time_condition: 有效期类型
            volume_condition: 成交量类型
            request_id: 请求ID

        Returns:
            0 表示成功，其他表示失败
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        dir_str = "买" if direction == Direction.BUY else "卖"
        offset_str = {
            OffsetFlag.OPEN: "开",
            OffsetFlag.CLOSE: "平",
            OffsetFlag.CLOSE_TODAY: "平今",
            OffsetFlag.CLOSE_YESTERDAY: "平昨",
        }.get(offset_flag, "未知")

        log.info(f"Requesting order insert: {instrument_id} {dir_str}{offset_str} "
                f"价格={price} 数量={volume}")

        return self._dll.ReqOrderInsert(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk'),
            order_ref.encode('gbk'),
            direction,
            offset_flag,
            price,
            volume,
            order_price_type,
            time_condition,
            volume_condition,
            request_id
        )

    def req_order_action(self, broker_id: str, investor_id: str,
                         instrument_id: str, exchange_id: str = "",
                         order_ref: str = "", front_id: int = 0, session_id: int = 0,
                         order_sys_id: str = "",
                         request_id: int = 11) -> int:
        """
        撤单请求

        可以通过两种方式撤单:
        1. order_ref + front_id + session_id (本地报单引用)
        2. exchange_id + order_sys_id (交易所系统编号)

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码
            exchange_id: 交易所代码
            order_ref: 报单引用
            front_id: 前置编号
            session_id: 会话编号
            order_sys_id: 报单编号
            request_id: 请求ID

        Returns:
            0 表示成功，其他表示失败
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Requesting order action (cancel): {instrument_id}")

        return self._dll.ReqOrderAction(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk'),
            exchange_id.encode('gbk') if exchange_id else b"",
            order_ref.encode('gbk') if order_ref else b"",
            front_id,
            session_id,
            order_sys_id.encode('gbk') if order_sys_id else b"",
            request_id
        )

    # ============================================================
    # 查询
    # ============================================================

    def req_qry_order(self, broker_id: str, investor_id: str,
                      instrument_id: str = "", order_sys_id: str = "",
                      request_id: int = 20) -> int:
        """
        查询订单

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码（可选）
            order_sys_id: 报单编号（可选）
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying orders: instrument={instrument_id or 'ALL'}")

        return self._dll.ReqQryOrder(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk') if instrument_id else b"",
            order_sys_id.encode('gbk') if order_sys_id else b"",
            request_id
        )

    def req_qry_trade(self, broker_id: str, investor_id: str,
                      instrument_id: str = "", trade_id: str = "",
                      request_id: int = 21) -> int:
        """
        查询成交

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码（可选）
            trade_id: 成交编号（可选）
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying trades: instrument={instrument_id or 'ALL'}")

        return self._dll.ReqQryTrade(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk') if instrument_id else b"",
            trade_id.encode('gbk') if trade_id else b"",
            request_id
        )

    def req_qry_investor_position(self, broker_id: str, investor_id: str,
                                   instrument_id: str = "",
                                   request_id: int = 22) -> int:
        """
        查询持仓

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码（可选，空则查询所有）
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying position: instrument={instrument_id or 'ALL'}")

        return self._dll.ReqQryInvestorPosition(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk') if instrument_id else b"",
            request_id
        )

    def req_qry_trading_account(self, broker_id: str, investor_id: str,
                                 request_id: int = 23) -> int:
        """
        查询资金账户

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying trading account: investor={investor_id}")

        return self._dll.ReqQryTradingAccount(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            request_id
        )

    def req_qry_instrument(self, instrument_id: str = "",
                           exchange_id: str = "", product_id: str = "",
                           request_id: int = 24) -> int:
        """
        查询合约

        Args:
            instrument_id: 合约代码（可选）
            exchange_id: 交易所代码（可选）
            product_id: 产品代码（可选）
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying instrument: {instrument_id or 'ALL'}")

        return self._dll.ReqQryInstrument(
            self._api,
            instrument_id.encode('gbk') if instrument_id else b"",
            exchange_id.encode('gbk') if exchange_id else b"",
            product_id.encode('gbk') if product_id else b"",
            request_id
        )

    def req_qry_depth_market_data(self, instrument_id: str = "",
                                   request_id: int = 25) -> int:
        """
        查询行情

        Args:
            instrument_id: 合约代码
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying market data: {instrument_id or 'ALL'}")

        return self._dll.ReqQryDepthMarketData(
            self._api,
            instrument_id.encode('gbk') if instrument_id else b"",
            request_id
        )

    def req_qry_instrument_margin_rate(self, broker_id: str, investor_id: str,
                                        instrument_id: str = "",
                                        request_id: int = 26) -> int:
        """
        查询保证金率

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying margin rate: {instrument_id or 'ALL'}")

        return self._dll.ReqQryInstrumentMarginRate(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk') if instrument_id else b"",
            request_id
        )

    def req_qry_instrument_commission_rate(self, broker_id: str, investor_id: str,
                                            instrument_id: str = "",
                                            request_id: int = 27) -> int:
        """
        查询手续费率

        Args:
            broker_id: 经纪公司代码
            investor_id: 投资者代码
            instrument_id: 合约代码
            request_id: 请求ID
        """
        if not self._api:
            raise RuntimeError("API not initialized")

        log.info(f"Querying commission rate: {instrument_id or 'ALL'}")

        return self._dll.ReqQryInstrumentCommissionRate(
            self._api,
            broker_id.encode('gbk'),
            investor_id.encode('gbk'),
            instrument_id.encode('gbk') if instrument_id else b"",
            request_id
        )

    def __del__(self):
        """析构时释放资源"""
        self.release()


# ============================================================
# 便捷函数
# ============================================================
def get_api_version(dll_path: str = None) -> str:
    """获取 API 版本（无需创建实例）"""
    if dll_path is None:
        dll_path = os.path.dirname(os.path.abspath(__file__))

    wrapper_dll = os.path.join(dll_path, "ctp_wrapper.dll")
    dll = CDLL(wrapper_dll)
    dll.GetApiVersion.restype = c_char_p
    version = dll.GetApiVersion()
    return version.decode('gbk') if version else ""


if __name__ == "__main__":
    # 简单测试
    print("CTP API Python Wrapper v2.0.0")
    print("=" * 50)

    try:
        version = get_api_version()
        print(f"API Version: {version}")
    except Exception as e:
        print(f"Error: {e}")
        print("Please build ctp_wrapper.dll first!")
