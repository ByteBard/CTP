"""
仿真服务器登录测试脚本 (独立版)
================================
用途: 在中国网络下运行，测试CTP仿真服务器连接
使用: python sim_login_test.py
日志: 输出到 sim_test_log.txt

注意: 请先修改下方的 PASSWORD 为您的密码（身份证后六位）
"""

import os
import sys
import time
import threading
from datetime import datetime

# ============================================================
# 配置区 - 请根据实际情况修改
# ============================================================
CONFIG = {
    "broker_id": "66666",
    "investor_id": "88003785",
    "password": "024111",              # <-- 修改为您的密码（身份证后六位）
    "app_id": "client_mltrader_1.0.0",
    "auth_code": "L8QDUC6XHBQR7WK2",
    "trade_front": "tcp://124.74.247.136:21407",
    "md_front": "tcp://124.74.247.136:21413",
}

# 日志文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "sim_test_log.txt")
FLOW_PATH = os.path.join(SCRIPT_DIR, "flow_test/")


class Logger:
    """简单的日志记录器，同时输出到控制台和文件"""

    def __init__(self, log_file):
        self.log_file = log_file
        self.start_time = datetime.now()
        # 清空或创建日志文件
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"CTP仿真服务器登录测试日志\n")
            f.write(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n\n")

    def log(self, level, msg, details=None):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elapsed = (datetime.now() - self.start_time).total_seconds()

        line = f"[{timestamp}] [{level:5}] (+{elapsed:6.2f}s) {msg}"
        if details:
            line += f"\n         详情: {details}"

        print(line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def info(self, msg, details=None):
        self.log("INFO", msg, details)

    def ok(self, msg, details=None):
        self.log("OK", msg, details)

    def error(self, msg, details=None):
        self.log("ERROR", msg, details)

    def warn(self, msg, details=None):
        self.log("WARN", msg, details)

    def section(self, title):
        """分节标题"""
        line = f"\n{'='*50}\n{title}\n{'='*50}"
        print(line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def summary(self, success, results):
        """输出测试总结"""
        self.section("测试总结")
        for key, value in results.items():
            self.info(f"{key}: {value}")

        if success:
            self.ok("=== 测试通过 ===")
        else:
            self.error("=== 测试失败 ===")

        self.info(f"日志已保存到: {self.log_file}")


# 初始化日志
log = Logger(LOG_FILE)


# 导入CTP库
try:
    from openctp_ctp import tdapi
    log.ok("加载CTP库成功", "使用 openctp-ctp")
except ImportError:
    try:
        from ctp import tdapi
        log.ok("加载CTP库成功", "使用 ctp")
    except ImportError:
        log.error("未安装CTP库", "请运行: pip install openctp-ctp")
        sys.exit(1)


class TraderSpi(tdapi.CThostFtdcTraderSpi):
    """交易回调处理"""

    def __init__(self):
        super().__init__()
        # 状态标志
        self.connected = False
        self.authenticated = False
        self.logged_in = False

        # 登录信息
        self.trading_day = ""
        self.front_id = 0
        self.session_id = 0
        self.max_order_ref = ""

        # 错误信息
        self.last_error_id = 0
        self.last_error_msg = ""

        # 同步事件
        self.connect_event = threading.Event()
        self.auth_event = threading.Event()
        self.login_event = threading.Event()
        self.disconnect_event = threading.Event()

    def OnFrontConnected(self):
        """连接成功回调"""
        log.ok("OnFrontConnected - 服务器连接成功")
        self.connected = True
        self.connect_event.set()

    def OnFrontDisconnected(self, nReason):
        """连接断开回调"""
        reason_map = {
            0x1001: "网络读失败",
            0x1002: "网络写失败",
            0x2001: "接收心跳超时",
            0x2002: "发送心跳失败",
            0x2003: "收到错误报文",
        }
        reason = reason_map.get(nReason, f"未知({hex(nReason)})")
        log.warn(f"OnFrontDisconnected - 连接断开", f"原因: {reason}")
        self.connected = False
        self.disconnect_event.set()

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        """认证响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.last_error_id = pRspInfo.ErrorID
            self.last_error_msg = pRspInfo.ErrorMsg
            log.error(f"OnRspAuthenticate - 认证失败",
                     f"ErrorID={pRspInfo.ErrorID}, Msg={pRspInfo.ErrorMsg}")
            self.authenticated = False
        else:
            log.ok("OnRspAuthenticate - 认证成功")
            self.authenticated = True
        self.auth_event.set()

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        """登录响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            self.last_error_id = pRspInfo.ErrorID
            self.last_error_msg = pRspInfo.ErrorMsg
            log.error(f"OnRspUserLogin - 登录失败",
                     f"ErrorID={pRspInfo.ErrorID}, Msg={pRspInfo.ErrorMsg}")
            self.logged_in = False
        else:
            self.logged_in = True
            if pRspUserLogin:
                self.trading_day = pRspUserLogin.TradingDay
                self.front_id = pRspUserLogin.FrontID
                self.session_id = pRspUserLogin.SessionID
                self.max_order_ref = pRspUserLogin.MaxOrderRef
                log.ok("OnRspUserLogin - 登录成功",
                      f"交易日={self.trading_day}, FrontID={self.front_id}, "
                      f"SessionID={self.session_id}")
        self.login_event.set()

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        """错误响应"""
        if pRspInfo:
            log.error(f"OnRspError",
                     f"ErrorID={pRspInfo.ErrorID}, Msg={pRspInfo.ErrorMsg}")


def run_test():
    """运行登录测试"""
    results = {
        "连接状态": "未测试",
        "认证状态": "未测试",
        "登录状态": "未测试",
        "交易日": "-",
        "FrontID": "-",
        "SessionID": "-",
        "错误信息": "无",
    }

    api = None
    success = False

    try:
        log.section("配置信息")
        log.info(f"经纪商ID: {CONFIG['broker_id']}")
        log.info(f"账号: {CONFIG['investor_id']}")
        log.info(f"AppID: {CONFIG['app_id']}")
        log.info(f"交易前置: {CONFIG['trade_front']}")
        log.info(f"行情前置: {CONFIG['md_front']}")

        # 创建流文件目录
        os.makedirs(FLOW_PATH, exist_ok=True)

        log.section("步骤1: 创建API实例")
        api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi(FLOW_PATH)
        log.info(f"API版本: {api.GetApiVersion()}")

        spi = TraderSpi()
        api.RegisterSpi(spi)

        log.section("步骤2: 连接服务器")
        api.RegisterFront(CONFIG['trade_front'])
        api.SubscribePrivateTopic(2)  # THOST_TERT_QUICK
        api.SubscribePublicTopic(2)

        log.info("初始化连接...")
        api.Init()

        log.info("等待连接响应 (超时10秒)...")
        if not spi.connect_event.wait(timeout=10):
            results["连接状态"] = "超时"
            results["错误信息"] = "连接服务器超时"
            log.error("连接超时")
            return False, results

        if not spi.connected:
            results["连接状态"] = "失败"
            results["错误信息"] = "连接失败"
            return False, results

        results["连接状态"] = "成功"

        log.section("步骤3: 客户端认证")
        req = tdapi.CThostFtdcReqAuthenticateField()
        req.BrokerID = CONFIG['broker_id']
        req.UserID = CONFIG['investor_id']
        req.AppID = CONFIG['app_id']
        req.AuthCode = CONFIG['auth_code']

        spi.auth_event.clear()
        ret = api.ReqAuthenticate(req, 1)

        if ret != 0:
            results["认证状态"] = f"请求失败(ret={ret})"
            results["错误信息"] = f"认证请求发送失败, 返回码: {ret}"
            log.error(f"认证请求发送失败", f"返回码: {ret}")
            return False, results

        log.info("等待认证响应 (超时10秒)...")
        if not spi.auth_event.wait(timeout=10):
            results["认证状态"] = "超时"
            results["错误信息"] = "认证响应超时"
            log.error("认证超时")
            return False, results

        if not spi.authenticated:
            results["认证状态"] = "失败"
            results["错误信息"] = f"[{spi.last_error_id}] {spi.last_error_msg}"
            return False, results

        results["认证状态"] = "成功"

        log.section("步骤4: 用户登录")
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = CONFIG['broker_id']
        req.UserID = CONFIG['investor_id']
        req.Password = CONFIG['password']

        spi.login_event.clear()
        ret = api.ReqUserLogin(req, 2)

        if ret != 0:
            results["登录状态"] = f"请求失败(ret={ret})"
            results["错误信息"] = f"登录请求发送失败, 返回码: {ret}"
            log.error(f"登录请求发送失败", f"返回码: {ret}")
            return False, results

        log.info("等待登录响应 (超时10秒)...")
        if not spi.login_event.wait(timeout=10):
            results["登录状态"] = "超时"
            results["错误信息"] = "登录响应超时"
            log.error("登录超时")
            return False, results

        if not spi.logged_in:
            results["登录状态"] = "失败"
            results["错误信息"] = f"[{spi.last_error_id}] {spi.last_error_msg}"
            return False, results

        results["登录状态"] = "成功"
        results["交易日"] = spi.trading_day
        results["FrontID"] = str(spi.front_id)
        results["SessionID"] = str(spi.session_id)
        results["错误信息"] = "无"

        success = True
        return True, results

    except Exception as e:
        import traceback
        results["错误信息"] = f"{type(e).__name__}: {e}"
        log.error(f"异常", f"{type(e).__name__}: {e}")
        log.error("堆栈", traceback.format_exc())
        return False, results

    finally:
        if api:
            log.info("释放API资源...")
            try:
                api.Release()
                log.info("API资源已释放")
            except:
                pass


def main():
    """主函数"""
    print(f"\n{'='*70}")
    print("CTP仿真服务器登录测试")
    print(f"日志文件: {LOG_FILE}")
    print(f"{'='*70}\n")

    success, results = run_test()
    log.summary(success, results)

    print(f"\n{'='*70}")
    print(f"测试{'通过' if success else '失败'}")
    print(f"详细日志: {LOG_FILE}")
    print(f"{'='*70}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
