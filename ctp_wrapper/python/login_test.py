"""
CTP 登录测试脚本
使用自封装的 ctp_api 进行登录测试

使用方法:
    python login_test.py

日志输出:
    ./test_log.txt
"""

import os
import sys
import time
import threading
from datetime import datetime

# 添加当前目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ctp_api import CTPTraderApi, ResumeType


# ============================================================
# 日志工具 (支持文件持久化)
# ============================================================
class FileLogger:
    """支持文件输出的日志记录器"""

    def __init__(self, log_file: str = None):
        self.start_time = datetime.now()
        self.log_file = log_file or os.path.join(SCRIPT_DIR, "test_log.txt")
        self._init_log_file()

    def _init_log_file(self):
        """初始化日志文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("CTP v6.6.8 封装登录测试日志\n")
            f.write(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

    def _log(self, level: str, msg: str):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        line = f"[{timestamp}] [{level:5}] (+{elapsed:6.2f}s) {msg}"

        # 输出到控制台
        print(line)

        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def info(self, msg: str):
        self._log("INFO", msg)

    def ok(self, msg: str):
        self._log("OK", msg)

    def error(self, msg: str):
        self._log("ERROR", msg)

    def warn(self, msg: str):
        self._log("WARN", msg)

    def write_summary(self, results: dict, success: bool):
        """写入测试总结"""
        lines = [
            "\n" + "=" * 60,
            "测试总结",
            "=" * 60,
        ]
        for key, value in results.items():
            lines.append(f"  {key}: {value}")
        lines.append("")
        lines.append("  [PASS] 测试通过" if success else "  [FAIL] 测试失败")
        lines.append("=" * 60)
        lines.append(f"\n日志已保存到: {self.log_file}\n")

        for line in lines:
            print(line)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')


# 创建全局日志实例
log = FileLogger()


# ============================================================
# 配置信息
# ============================================================
CONFIG = {
    "broker_id": "66666",
    "investor_id": "88003785",
    "password": "Ctp123456",        # 新密码（已修改）
    "app_id": "client_mltrader_1.0.0",
    "auth_code": "L8QDUC6XHBQR7WK2",
    "trade_front": "tcp://124.74.247.136:21407",
    "md_front": "tcp://124.74.247.136:21413",
    "flow_path": "./flow_test/",
}


# ============================================================
# 测试类
# ============================================================
class LoginTest:
    """登录测试"""

    def __init__(self):
        self.api = None
        self.connected = False
        self.authenticated = False
        self.logged_in = False
        self.login_info = {}

        # 同步事件
        self.connect_event = threading.Event()
        self.auth_event = threading.Event()
        self.login_event = threading.Event()

        # 结果
        self.results = {
            "连接状态": "未测试",
            "认证状态": "未测试",
            "登录状态": "未测试",
            "交易日": "-",
            "FrontID": "-",
            "SessionID": "-",
            "错误信息": "无",
        }

    def on_front_connected(self):
        """连接成功回调"""
        self.connected = True
        self.connect_event.set()

    def on_front_disconnected(self, reason):
        """连接断开回调"""
        self.connected = False

    def on_rsp_authenticate(self, broker_id, user_id, app_id,
                            error_id, error_msg, request_id, is_last):
        """认证响应回调"""
        if error_id == 0:
            self.authenticated = True
        else:
            self.results["错误信息"] = f"[{error_id}] {error_msg}"
        self.auth_event.set()

    def on_rsp_user_login(self, trading_day, login_time, broker_id, user_id,
                          front_id, session_id, max_order_ref,
                          error_id, error_msg, request_id, is_last):
        """登录响应回调"""
        if error_id == 0:
            self.logged_in = True
            self.login_info = {
                "trading_day": trading_day,
                "login_time": login_time,
                "front_id": front_id,
                "session_id": session_id,
                "max_order_ref": max_order_ref,
            }
        else:
            self.results["错误信息"] = f"[{error_id}] {error_msg}"
        self.login_event.set()

    def on_rsp_error(self, error_id, error_msg, request_id, is_last):
        """错误响应回调"""
        self.results["错误信息"] = f"[{error_id}] {error_msg}"

    def run(self):
        """运行测试"""
        try:
            # 步骤 1: 创建 API
            log.info("=" * 40)
            log.info("步骤 1: 创建 API 实例")
            log.info("=" * 40)

            self.api = CTPTraderApi()

            # 设置回调
            self.api.on_front_connected = self.on_front_connected
            self.api.on_front_disconnected = self.on_front_disconnected
            self.api.on_rsp_authenticate = self.on_rsp_authenticate
            self.api.on_rsp_user_login = self.on_rsp_user_login
            self.api.on_rsp_error = self.on_rsp_error

            self.api.create_api(CONFIG["flow_path"])

            # 步骤 2: 连接服务器
            log.info("=" * 40)
            log.info("步骤 2: 连接服务器")
            log.info("=" * 40)

            self.api.register_front(CONFIG["trade_front"])
            self.api.subscribe_private_topic(ResumeType.QUICK)
            self.api.subscribe_public_topic(ResumeType.QUICK)

            log.info("初始化连接...")
            self.api.init()

            log.info("等待连接响应 (超时10秒)...")
            if not self.connect_event.wait(timeout=10):
                self.results["连接状态"] = "超时"
                self.results["错误信息"] = "连接服务器超时"
                return False

            if not self.connected:
                self.results["连接状态"] = "失败"
                return False

            self.results["连接状态"] = "成功"

            # 步骤 3: 客户端认证
            log.info("=" * 40)
            log.info("步骤 3: 客户端认证")
            log.info("=" * 40)

            self.auth_event.clear()
            ret = self.api.req_authenticate(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                CONFIG["app_id"],
                CONFIG["auth_code"],
                request_id=1
            )

            if ret != 0:
                self.results["认证状态"] = f"请求失败(ret={ret})"
                return False

            log.info("等待认证响应 (超时10秒)...")
            if not self.auth_event.wait(timeout=10):
                self.results["认证状态"] = "超时"
                self.results["错误信息"] = "认证响应超时"
                return False

            if not self.authenticated:
                self.results["认证状态"] = "失败"
                return False

            self.results["认证状态"] = "成功"

            # 步骤 4: 用户登录
            log.info("=" * 40)
            log.info("步骤 4: 用户登录")
            log.info("=" * 40)

            self.login_event.clear()
            ret = self.api.req_user_login(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                CONFIG["password"],
                request_id=2
            )

            if ret != 0:
                self.results["登录状态"] = f"请求失败(ret={ret})"
                return False

            log.info("等待登录响应 (超时10秒)...")
            if not self.login_event.wait(timeout=10):
                self.results["登录状态"] = "超时"
                self.results["错误信息"] = "登录响应超时"
                return False

            if not self.logged_in:
                self.results["登录状态"] = "失败"
                return False

            self.results["登录状态"] = "成功"
            self.results["交易日"] = self.login_info.get("trading_day", "-")
            self.results["FrontID"] = str(self.login_info.get("front_id", "-"))
            self.results["SessionID"] = str(self.login_info.get("session_id", "-"))
            self.results["错误信息"] = "无"

            return True

        except Exception as e:
            import traceback
            self.results["错误信息"] = f"{type(e).__name__}: {e}"
            log.error(f"异常: {e}")
            traceback.print_exc()
            return False

        finally:
            if self.api:
                log.info("释放 API 资源...")
                self.api.release()

    def print_summary(self, success):
        """打印测试总结"""
        log.write_summary(self.results, success)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("CTP v6.6.8 仿真服务器登录测试 (自封装版)")
    print("=" * 60 + "\n")

    test = LoginTest()
    success = test.run()
    test.print_summary(success)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
