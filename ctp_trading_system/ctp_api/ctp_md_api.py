"""
CTP 行情 API Python 封装 (ctypes)
通过 ctp_md_wrapper.dll 调用 CTP v6.6.8 官方行情 API
"""

import os
import sys
import logging
from ctypes import (
    cdll, c_int, c_double, c_char, c_char_p, c_void_p,
    Structure, CFUNCTYPE, POINTER, byref, cast
)
from typing import Optional, Callable, List

log = logging.getLogger(__name__)

# ============================================================
# 回调函数类型定义
# ============================================================
MdOnFrontConnectedCallback = CFUNCTYPE(None)
MdOnFrontDisconnectedCallback = CFUNCTYPE(None, c_int)
MdOnHeartBeatWarningCallback = CFUNCTYPE(None, c_int)

MdOnRspUserLoginCallback = CFUNCTYPE(
    None, c_char_p, c_char_p, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

MdOnRspUserLogoutCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_int, c_char_p, c_int, c_int)

MdOnRspErrorCallback = CFUNCTYPE(
    None, c_int, c_char_p, c_int, c_int)

MdOnRspSubMarketDataCallback = CFUNCTYPE(
    None, c_char_p,
    c_int, c_char_p, c_int, c_int)

MdOnRspUnSubMarketDataCallback = CFUNCTYPE(
    None, c_char_p,
    c_int, c_char_p, c_int, c_int)

MdOnRtnDepthMarketDataCallback = CFUNCTYPE(
    None, c_char_p, c_char_p,
    c_double, c_double, c_double, c_double,
    c_double, c_double, c_double,
    c_int, c_double, c_double,
    c_double, c_double,
    c_double, c_double,
    c_double, c_int, c_double, c_int,
    c_double, c_int, c_double, c_int,
    c_double, c_int, c_double, c_int,
    c_double, c_int, c_double, c_int,
    c_double, c_int, c_double, c_int,
    c_double,
    c_char_p, c_int,
    c_char_p, c_char_p)


# ============================================================
# 回调结构体
# ============================================================
class MdCallbacks(Structure):
    _fields_ = [
        ("on_front_connected", MdOnFrontConnectedCallback),
        ("on_front_disconnected", MdOnFrontDisconnectedCallback),
        ("on_heartbeat_warning", MdOnHeartBeatWarningCallback),
        ("on_rsp_user_login", MdOnRspUserLoginCallback),
        ("on_rsp_user_logout", MdOnRspUserLogoutCallback),
        ("on_rsp_error", MdOnRspErrorCallback),
        ("on_rsp_sub_market_data", MdOnRspSubMarketDataCallback),
        ("on_rsp_unsub_market_data", MdOnRspUnSubMarketDataCallback),
        ("on_rtn_depth_market_data", MdOnRtnDepthMarketDataCallback),
    ]


class CTPMdApi:
    """CTP 行情 API 封装"""

    def __init__(self):
        self._dll = None
        self._api = None
        self._callbacks_struct = None
        self._callback_refs = []

        # 用户回调
        self.on_front_connected: Optional[Callable] = None
        self.on_front_disconnected: Optional[Callable] = None
        self.on_heartbeat_warning: Optional[Callable] = None
        self.on_rsp_user_login: Optional[Callable] = None
        self.on_rsp_user_logout: Optional[Callable] = None
        self.on_rsp_error: Optional[Callable] = None
        self.on_rsp_sub_market_data: Optional[Callable] = None
        self.on_rsp_unsub_market_data: Optional[Callable] = None
        self.on_rtn_depth_market_data: Optional[Callable] = None

        self._load_dll()
        if self._dll:
            self._setup_functions()

    def _load_dll(self):
        """加载 DLL"""
        search_paths = []

        # 当前目录
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(curr_dir)

        # ctp_wrapper/python 目录
        wrapper_dir = os.path.join(os.path.dirname(os.path.dirname(curr_dir)), 'ctp_wrapper', 'python')
        search_paths.append(wrapper_dir)

        for path in search_paths:
            dll_path = os.path.join(path, 'ctp_md_wrapper.dll')
            if os.path.exists(dll_path):
                try:
                    os.add_dll_directory(path)
                except:
                    pass
                try:
                    self._dll = cdll.LoadLibrary(dll_path)
                    log.info(f"Loaded ctp_md_wrapper.dll from {path}")
                    return
                except Exception as e:
                    log.warning(f"Failed to load from {path}: {e}")

        log.warning("ctp_md_wrapper.dll not found")

    def _setup_functions(self):
        """设置DLL函数签名"""
        self._dll.CreateMdApi.argtypes = [c_char_p]
        self._dll.CreateMdApi.restype = c_void_p

        self._dll.ReleaseMdApi.argtypes = [c_void_p]
        self._dll.ReleaseMdApi.restype = None

        self._dll.MdRegisterCallbacks.argtypes = [c_void_p, POINTER(MdCallbacks)]
        self._dll.MdRegisterCallbacks.restype = None

        self._dll.MdRegisterFront.argtypes = [c_void_p, c_char_p]
        self._dll.MdRegisterFront.restype = None

        self._dll.MdInit.argtypes = [c_void_p]
        self._dll.MdInit.restype = None

        self._dll.MdReqUserLogin.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p, c_int]
        self._dll.MdReqUserLogin.restype = c_int

        self._dll.MdReqUserLogout.argtypes = [c_void_p, c_char_p, c_char_p, c_int]
        self._dll.MdReqUserLogout.restype = c_int

        self._dll.MdSubscribeMarketData.argtypes = [c_void_p, POINTER(c_char_p), c_int]
        self._dll.MdSubscribeMarketData.restype = c_int

        self._dll.MdUnSubscribeMarketData.argtypes = [c_void_p, POINTER(c_char_p), c_int]
        self._dll.MdUnSubscribeMarketData.restype = c_int

    def _decode(self, val) -> str:
        if val is None:
            return ""
        if isinstance(val, bytes):
            try:
                return val.decode('gbk')
            except:
                return val.decode('utf-8', errors='replace')
        return str(val)

    def create_api(self, flow_path: str = ""):
        """创建行情API实例"""
        if not self._dll:
            raise RuntimeError("DLL not loaded")
        self._api = self._dll.CreateMdApi(flow_path.encode('gbk'))
        if not self._api:
            raise RuntimeError("Failed to create MdApi")
        self._create_callbacks()

    def _create_callbacks(self):
        """创建并注册回调"""
        def _on_connected():
            if self.on_front_connected:
                self.on_front_connected()

        def _on_disconnected(reason):
            if self.on_front_disconnected:
                self.on_front_disconnected(reason)

        def _on_heartbeat(time_lapse):
            if self.on_heartbeat_warning:
                self.on_heartbeat_warning(time_lapse)

        def _on_login(trading_day, login_time, broker_id, user_id,
                      error_id, error_msg, request_id, is_last):
            trading_day = self._decode(trading_day)
            login_time = self._decode(login_time)
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            error_msg = self._decode(error_msg)
            if self.on_rsp_user_login:
                self.on_rsp_user_login(
                    trading_day, login_time, broker_id, user_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_logout(broker_id, user_id, error_id, error_msg, request_id, is_last):
            broker_id = self._decode(broker_id)
            user_id = self._decode(user_id)
            error_msg = self._decode(error_msg)
            if self.on_rsp_user_logout:
                self.on_rsp_user_logout(
                    broker_id, user_id,
                    error_id, error_msg, request_id, bool(is_last))

        def _on_error(error_id, error_msg, request_id, is_last):
            error_msg = self._decode(error_msg)
            if self.on_rsp_error:
                self.on_rsp_error(error_id, error_msg, request_id, bool(is_last))

        def _on_sub(instrument_id, error_id, error_msg, request_id, is_last):
            instrument_id = self._decode(instrument_id)
            error_msg = self._decode(error_msg)
            if self.on_rsp_sub_market_data:
                self.on_rsp_sub_market_data(
                    instrument_id, error_id, error_msg, request_id, bool(is_last))

        def _on_unsub(instrument_id, error_id, error_msg, request_id, is_last):
            instrument_id = self._decode(instrument_id)
            error_msg = self._decode(error_msg)
            if self.on_rsp_unsub_market_data:
                self.on_rsp_unsub_market_data(
                    instrument_id, error_id, error_msg, request_id, bool(is_last))

        def _on_market_data(instrument_id, exchange_id,
                            last_price, pre_settlement_price,
                            pre_close_price, pre_open_interest,
                            open_price, highest_price, lowest_price,
                            volume, turnover, open_interest,
                            close_price, settlement_price,
                            upper_limit_price, lower_limit_price,
                            bid_price1, bid_volume1, ask_price1, ask_volume1,
                            bid_price2, bid_volume2, ask_price2, ask_volume2,
                            bid_price3, bid_volume3, ask_price3, ask_volume3,
                            bid_price4, bid_volume4, ask_price4, ask_volume4,
                            bid_price5, bid_volume5, ask_price5, ask_volume5,
                            average_price,
                            update_time, update_millisec,
                            trading_day, action_day):
            instrument_id = self._decode(instrument_id)
            exchange_id = self._decode(exchange_id)
            update_time = self._decode(update_time)
            trading_day = self._decode(trading_day)
            action_day = self._decode(action_day)
            if self.on_rtn_depth_market_data:
                self.on_rtn_depth_market_data(
                    instrument_id, exchange_id,
                    last_price, pre_settlement_price,
                    pre_close_price, pre_open_interest,
                    open_price, highest_price, lowest_price,
                    volume, turnover, open_interest,
                    close_price, settlement_price,
                    upper_limit_price, lower_limit_price,
                    bid_price1, bid_volume1, ask_price1, ask_volume1,
                    bid_price2, bid_volume2, ask_price2, ask_volume2,
                    bid_price3, bid_volume3, ask_price3, ask_volume3,
                    bid_price4, bid_volume4, ask_price4, ask_volume4,
                    bid_price5, bid_volume5, ask_price5, ask_volume5,
                    average_price,
                    update_time, update_millisec,
                    trading_day, action_day)

        callbacks = [
            MdOnFrontConnectedCallback(_on_connected),
            MdOnFrontDisconnectedCallback(_on_disconnected),
            MdOnHeartBeatWarningCallback(_on_heartbeat),
            MdOnRspUserLoginCallback(_on_login),
            MdOnRspUserLogoutCallback(_on_logout),
            MdOnRspErrorCallback(_on_error),
            MdOnRspSubMarketDataCallback(_on_sub),
            MdOnRspUnSubMarketDataCallback(_on_unsub),
            MdOnRtnDepthMarketDataCallback(_on_market_data),
        ]

        self._callback_refs = callbacks

        self._callbacks_struct = MdCallbacks(
            on_front_connected=callbacks[0],
            on_front_disconnected=callbacks[1],
            on_heartbeat_warning=callbacks[2],
            on_rsp_user_login=callbacks[3],
            on_rsp_user_logout=callbacks[4],
            on_rsp_error=callbacks[5],
            on_rsp_sub_market_data=callbacks[6],
            on_rsp_unsub_market_data=callbacks[7],
            on_rtn_depth_market_data=callbacks[8],
        )

        self._dll.MdRegisterCallbacks(self._api, byref(self._callbacks_struct))

    def register_front(self, front_address: str):
        """注册前置地址"""
        if not self._api:
            raise RuntimeError("API not initialized")
        self._dll.MdRegisterFront(self._api, front_address.encode('gbk'))

    def init(self):
        """初始化连接"""
        if not self._api:
            raise RuntimeError("API not initialized")
        self._dll.MdInit(self._api)

    def req_user_login(self, broker_id: str, user_id: str,
                       password: str, request_id: int = 1) -> int:
        """登录"""
        if not self._api:
            raise RuntimeError("API not initialized")
        return self._dll.MdReqUserLogin(
            self._api,
            broker_id.encode('gbk'),
            user_id.encode('gbk'),
            password.encode('gbk'),
            request_id
        )

    def subscribe_market_data(self, instrument_ids: List[str]) -> int:
        """订阅行情"""
        if not self._api:
            raise RuntimeError("API not initialized")
        count = len(instrument_ids)
        ids = (c_char_p * count)(*[s.encode('gbk') for s in instrument_ids])
        return self._dll.MdSubscribeMarketData(self._api, ids, count)

    def unsubscribe_market_data(self, instrument_ids: List[str]) -> int:
        """退订行情"""
        if not self._api:
            raise RuntimeError("API not initialized")
        count = len(instrument_ids)
        ids = (c_char_p * count)(*[s.encode('gbk') for s in instrument_ids])
        return self._dll.MdUnSubscribeMarketData(self._api, ids, count)

    def release(self):
        """释放资源"""
        if self._api and self._dll:
            self._dll.ReleaseMdApi(self._api)
            self._api = None

    def __del__(self):
        self.release()
