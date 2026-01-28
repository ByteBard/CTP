"""
CTP行情网关
使用 CTP v6.6.8 官方行情 API (通过 ctp_md_wrapper)
"""
import os
import sys
import time
import threading
from typing import Optional, Dict, Callable, Any, List

# 添加 ctp_api 路径
ctp_api_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ctp_api')
if ctp_api_path not in sys.path:
    sys.path.insert(0, ctp_api_path)

try:
    from ctp_md_api import CTPMdApi
    MD_API_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入 CTP MdApi: {e}")
    MD_API_AVAILABLE = False

try:
    from ..trade_logging.trade_logger import get_logger, TradeLogger
except ImportError:
    from trade_logging.trade_logger import get_logger, TradeLogger


class MdGateway:
    """CTP 行情网关"""

    def __init__(self, md_front: str, broker_id: str = "",
                 user_id: str = "", password: str = ""):
        self.md_front = md_front
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.logger: TradeLogger = get_logger()

        self._api: Optional[CTPMdApi] = None
        self._connected = False
        self._logged_in = False

        self._connect_event = threading.Event()
        self._login_event = threading.Event()

        # 行情缓存: instrument_id -> market data dict
        self._market_data: Dict[str, Dict] = {}

        # 已订阅合约
        self._subscribed: set = set()

        # 行情回调
        self._on_market_data_callbacks: List[Callable] = []

        self._lock = threading.Lock()

    def connect(self, timeout: int = 10) -> bool:
        """连接行情前置"""
        if not MD_API_AVAILABLE:
            self.logger.log_error("MdApi not available")
            return False

        self.logger.log_system("连接行情前置", {"md_front": self.md_front})

        flow_path = os.path.join("flow", "md_")
        os.makedirs("flow", exist_ok=True)

        self._api = CTPMdApi()
        self._api.create_api(flow_path)
        self._setup_callbacks()
        self._api.register_front(self.md_front)

        self._connect_event.clear()
        self._api.init()

        if not self._connect_event.wait(timeout):
            self.logger.log_error("行情连接超时")
            return False

        return self._connected

    def login(self, timeout: int = 10) -> bool:
        """登录行情"""
        if not self._connected:
            return False

        self._login_event.clear()
        ret = self._api.req_user_login(
            broker_id=self.broker_id,
            user_id=self.user_id,
            password=self.password,
            request_id=1
        )
        if ret != 0:
            return False

        if not self._login_event.wait(timeout):
            return False

        return self._logged_in

    def subscribe(self, instrument_ids: List[str]) -> bool:
        """订阅行情"""
        if not self._logged_in:
            return False
        ret = self._api.subscribe_market_data(instrument_ids)
        if ret == 0:
            self._subscribed.update(instrument_ids)
        return ret == 0

    def unsubscribe(self, instrument_ids: List[str]) -> bool:
        """退订行情"""
        if not self._logged_in:
            return False
        ret = self._api.unsubscribe_market_data(instrument_ids)
        if ret == 0:
            self._subscribed -= set(instrument_ids)
        return ret == 0

    def get_market_data(self, instrument_id: str = "") -> Dict:
        """获取行情缓存"""
        if instrument_id:
            return self._market_data.get(instrument_id, {})
        return self._market_data

    def get_subscribed(self) -> List[str]:
        """获取已订阅合约列表"""
        return list(self._subscribed)

    def register_market_data_callback(self, callback: Callable):
        """注册行情回调"""
        self._on_market_data_callbacks.append(callback)

    def _setup_callbacks(self):
        """设置回调"""
        def on_connected():
            self.logger.log_system("行情前置已连接")
            self._connected = True
            self._connect_event.set()

        def on_disconnected(reason):
            self.logger.log_system(f"行情前置断开: {reason}")
            self._connected = False
            self._logged_in = False

        def on_login(trading_day, login_time, broker_id, user_id,
                     error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_error(f"行情登录失败: {error_msg}")
                self._logged_in = False
            else:
                self.logger.log_system(f"行情登录成功, 交易日: {trading_day}")
                self._logged_in = True
            self._login_event.set()

        def on_sub(instrument_id, error_id, error_msg, request_id, is_last):
            if error_id != 0:
                self.logger.log_error(f"订阅行情失败: {instrument_id} - {error_msg}")
            else:
                self.logger.log_system(f"订阅行情成功: {instrument_id}")

        def on_unsub(instrument_id, error_id, error_msg, request_id, is_last):
            self.logger.log_system(f"退订行情: {instrument_id}")

        def on_market_data(instrument_id, exchange_id,
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
            data = {
                "instrument_id": instrument_id,
                "exchange_id": exchange_id,
                "last_price": last_price,
                "pre_settlement_price": pre_settlement_price,
                "pre_close_price": pre_close_price,
                "open_price": open_price,
                "highest_price": highest_price,
                "lowest_price": lowest_price,
                "volume": volume,
                "turnover": turnover,
                "open_interest": open_interest,
                "close_price": close_price,
                "settlement_price": settlement_price,
                "upper_limit_price": upper_limit_price,
                "lower_limit_price": lower_limit_price,
                "bid_price1": bid_price1,
                "bid_volume1": bid_volume1,
                "ask_price1": ask_price1,
                "ask_volume1": ask_volume1,
                "bid_price2": bid_price2,
                "bid_volume2": bid_volume2,
                "ask_price2": ask_price2,
                "ask_volume2": ask_volume2,
                "bid_price3": bid_price3,
                "bid_volume3": bid_volume3,
                "ask_price3": ask_price3,
                "ask_volume3": ask_volume3,
                "bid_price4": bid_price4,
                "bid_volume4": bid_volume4,
                "ask_price4": ask_price4,
                "ask_volume4": ask_volume4,
                "bid_price5": bid_price5,
                "bid_volume5": bid_volume5,
                "ask_price5": ask_price5,
                "ask_volume5": ask_volume5,
                "average_price": average_price,
                "update_time": update_time,
                "update_millisec": update_millisec,
                "trading_day": trading_day,
                "action_day": action_day,
            }

            with self._lock:
                self._market_data[instrument_id] = data

            for callback in self._on_market_data_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.log_exception(e, "market_data callback")

        self._api.on_front_connected = on_connected
        self._api.on_front_disconnected = on_disconnected
        self._api.on_rsp_user_login = on_login
        self._api.on_rsp_sub_market_data = on_sub
        self._api.on_rsp_unsub_market_data = on_unsub
        self._api.on_rtn_depth_market_data = on_market_data

    def is_connected(self) -> bool:
        return self._connected

    def is_logged_in(self) -> bool:
        return self._logged_in

    def close(self):
        """关闭连接"""
        if self._api:
            self._api.release()
            self._api = None
        self._connected = False
        self._logged_in = False
