"""
仿真环境连接测试脚本
测试连接、认证、登录功能
"""
import os
import sys
import time
import threading

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 仿真服务器配置
SIM_CONFIG = {
    "broker_id": "66666",
    "investor_id": "88003785",
    "password": "024111",
    "app_id": "client_mltrader_1.0.0",
    "auth_code": "L8QDUC6XHBQR7WK2",
    "trade_front": "tcp://124.74.247.136:21407",
    "md_front": "tcp://124.74.247.136:21413",
}

# 尝试导入CTP API
try:
    from openctp_ctp import tdapi
    print("[OK] 已加载 openctp-ctp 库")
except ImportError:
    try:
        from ctp import tdapi
        print("[OK] 已加载 ctp 库")
    except ImportError:
        print("[ERROR] 未安装CTP库，请运行: pip install openctp-ctp")
        sys.exit(1)


class TestTraderSpi(tdapi.CThostFtdcTraderSpi):
    """交易回调处理类"""

    def __init__(self):
        super().__init__()
        self.connected = False
        self.authenticated = False
        self.logged_in = False
        self.front_id = 0
        self.session_id = 0
        self.trading_day = ""

        # 同步事件
        self.connect_event = threading.Event()
        self.auth_event = threading.Event()
        self.login_event = threading.Event()

        # 错误信息
        self.last_error = ""

    def OnFrontConnected(self):
        """连接成功"""
        print("[回调] OnFrontConnected - 服务器连接成功")
        self.connected = True
        self.connect_event.set()

    def OnFrontDisconnected(self, nReason: int):
        """连接断开"""
        reason_map = {
            0x1001: "网络读失败",
            0x1002: "网络写失败",
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文",
        }
        reason = reason_map.get(nReason, f"未知原因({hex(nReason)})")
        print(f"[回调] OnFrontDisconnected - 连接断开: {reason}")
        self.connected = False

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        """客户端认证响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.last_error = f"认证失败[{pRspInfo.ErrorID}]: {pRspInfo.ErrorMsg}"
            print(f"[回调] OnRspAuthenticate - {self.last_error}")
            self.authenticated = False
        else:
            print("[回调] OnRspAuthenticate - 认证成功")
            self.authenticated = True
        self.auth_event.set()

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登录响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.last_error = f"登录失败[{pRspInfo.ErrorID}]: {pRspInfo.ErrorMsg}"
            print(f"[回调] OnRspUserLogin - {self.last_error}")
            self.logged_in = False
        else:
            self.logged_in = True
            if pRspUserLogin:
                self.trading_day = pRspUserLogin.TradingDay
                self.front_id = pRspUserLogin.FrontID
                self.session_id = pRspUserLogin.SessionID
                print(f"[回调] OnRspUserLogin - 登录成功")
                print(f"       交易日: {self.trading_day}")
                print(f"       FrontID: {self.front_id}")
                print(f"       SessionID: {self.session_id}")
        self.login_event.set()

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        """错误响应"""
        if pRspInfo:
            print(f"[回调] OnRspError - 错误[{pRspInfo.ErrorID}]: {pRspInfo.ErrorMsg}")


def test_connection():
    """测试仿真服务器连接"""
    print("=" * 60)
    print("CTP仿真环境连接测试")
    print("=" * 60)
    print(f"经纪商ID: {SIM_CONFIG['broker_id']}")
    print(f"账号: {SIM_CONFIG['investor_id']}")
    print(f"交易前置: {SIM_CONFIG['trade_front']}")
    print("=" * 60)

    # 创建流文件目录
    flow_path = "./flow_sim/"
    os.makedirs(flow_path, exist_ok=True)

    # 创建API实例
    print("\n[步骤1] 创建API实例...")
    api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi(flow_path)
    print(f"         API版本: {api.GetApiVersion()}")

    # 创建SPI实例
    spi = TestTraderSpi()

    # 注册SPI
    api.RegisterSpi(spi)

    # 注册前置地址
    print(f"\n[步骤2] 注册前置地址: {SIM_CONFIG['trade_front']}")
    api.RegisterFront(SIM_CONFIG['trade_front'])

    # 订阅私有流和公有流
    api.SubscribePrivateTopic(2)  # THOST_TERT_QUICK
    api.SubscribePublicTopic(2)

    # 初始化连接
    print("\n[步骤3] 初始化连接...")
    api.Init()

    # 等待连接
    print("         等待服务器连接...")
    if not spi.connect_event.wait(timeout=10):
        print("[失败] 连接超时")
        api.Release()
        return False

    if not spi.connected:
        print("[失败] 连接失败")
        api.Release()
        return False

    print("[成功] 服务器连接成功")

    # 客户端认证
    print("\n[步骤4] 客户端认证...")
    req = tdapi.CThostFtdcReqAuthenticateField()
    req.BrokerID = SIM_CONFIG['broker_id']
    req.UserID = SIM_CONFIG['investor_id']
    req.AppID = SIM_CONFIG['app_id']
    req.AuthCode = SIM_CONFIG['auth_code']

    spi.auth_event.clear()
    ret = api.ReqAuthenticate(req, 1)

    if ret != 0:
        print(f"[失败] 认证请求发送失败, 返回码: {ret}")
        api.Release()
        return False

    print("         等待认证响应...")
    if not spi.auth_event.wait(timeout=10):
        print("[失败] 认证超时")
        api.Release()
        return False

    if not spi.authenticated:
        print(f"[失败] {spi.last_error}")
        api.Release()
        return False

    print("[成功] 客户端认证成功")

    # 用户登录
    print("\n[步骤5] 用户登录...")
    req = tdapi.CThostFtdcReqUserLoginField()
    req.BrokerID = SIM_CONFIG['broker_id']
    req.UserID = SIM_CONFIG['investor_id']
    req.Password = SIM_CONFIG['password']

    spi.login_event.clear()
    ret = api.ReqUserLogin(req, 2)

    if ret != 0:
        print(f"[失败] 登录请求发送失败, 返回码: {ret}")
        api.Release()
        return False

    print("         等待登录响应...")
    if not spi.login_event.wait(timeout=10):
        print("[失败] 登录超时")
        api.Release()
        return False

    if not spi.logged_in:
        print(f"[失败] {spi.last_error}")
        api.Release()
        return False

    print("[成功] 用户登录成功")

    # 测试完成
    print("\n" + "=" * 60)
    print("测试结果: 全部通过")
    print("=" * 60)
    print(f"交易日: {spi.trading_day}")
    print(f"FrontID: {spi.front_id}")
    print(f"SessionID: {spi.session_id}")
    print("=" * 60)

    # 断开连接
    print("\n正在断开连接...")
    api.Release()
    print("连接已断开")

    return True


if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[异常] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
