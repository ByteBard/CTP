# -*- coding: utf-8 -*-
"""
CTP 修改密码脚本
================
首次登录仿真账户需要修改密码

使用方法:
    python change_password.py

注意:
    - 新密码至少6位
    - 修改成功后请记住新密码
"""

import os
import sys
import threading
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ctp_api import CTPTraderApi, ResumeType


# ============================================================
# 配置信息
# ============================================================
CONFIG = {
    "broker_id": "66666",
    "investor_id": "88003785",
    "old_password": "024111",           # 原密码（身份证后六位）
    "new_password": "Ctp123456",        # 新密码（至少6位）
    "app_id": "client_mltrader_1.0.0",
    "auth_code": "L8QDUC6XHBQR7WK2",
    "trade_front": "tcp://124.74.247.136:21407",
}


# ============================================================
# 日志工具
# ============================================================
class Logger:
    def __init__(self, log_file=None):
        self.start_time = datetime.now()
        self.log_file = log_file or os.path.join(SCRIPT_DIR, "change_password_log.txt")
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("CTP v6.6.8 修改密码日志\n")
            f.write(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

    def _log(self, level, msg):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        line = f"[{timestamp}] [{level:5}] (+{elapsed:6.2f}s) {msg}"
        print(line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    def info(self, msg): self._log("INFO", msg)
    def ok(self, msg): self._log("OK", msg)
    def error(self, msg): self._log("ERROR", msg)
    def warn(self, msg): self._log("WARN", msg)


log = Logger()


# ============================================================
# 修改密码类
# ============================================================
class ChangePassword:
    def __init__(self):
        self.api = None
        self.connected = False
        self.authenticated = False
        self.login_attempted = False
        self.password_updated = False
        self.error_msg = ""

        self.connect_event = threading.Event()
        self.auth_event = threading.Event()
        self.login_event = threading.Event()
        self.password_event = threading.Event()

    def on_connected(self):
        self.connected = True
        self.connect_event.set()

    def on_disconnected(self, reason):
        self.connected = False

    def on_authenticate(self, broker_id, user_id, app_id,
                        error_id, error_msg, request_id, is_last):
        if error_id == 0:
            self.authenticated = True
        else:
            self.error_msg = f"[{error_id}] {error_msg}"
        self.auth_event.set()

    def on_login(self, trading_day, login_time, broker_id, user_id,
                 front_id, session_id, max_order_ref,
                 error_id, error_msg, request_id, is_last):
        self.login_attempted = True
        if error_id != 0:
            log.warn(f"登录返回: [{error_id}] {error_msg}")
        self.login_event.set()

    def on_password_update(self, broker_id, user_id,
                           error_id, error_msg, request_id, is_last):
        if error_id == 0:
            self.password_updated = True
        else:
            self.error_msg = f"[{error_id}] {error_msg}"
        self.password_event.set()

    def run(self):
        print("\n" + "=" * 60)
        print("CTP v6.6.8 仿真账户修改密码")
        print("=" * 60 + "\n")

        log.info(f"原密码: {CONFIG['old_password']}")
        log.info(f"新密码: {CONFIG['new_password']}")

        try:
            # 创建 API
            log.info("创建 API 实例...")
            self.api = CTPTraderApi()

            self.api.on_front_connected = self.on_connected
            self.api.on_front_disconnected = self.on_disconnected
            self.api.on_rsp_authenticate = self.on_authenticate
            self.api.on_rsp_user_login = self.on_login
            self.api.on_rsp_user_password_update = self.on_password_update

            self.api.create_api("./flow_pwd/")

            # 连接
            log.info(f"连接服务器: {CONFIG['trade_front']}")
            self.api.register_front(CONFIG['trade_front'])
            self.api.subscribe_private_topic(ResumeType.QUICK)
            self.api.subscribe_public_topic(ResumeType.QUICK)
            self.api.init()

            log.info("等待连接...")
            if not self.connect_event.wait(timeout=10):
                log.error("连接超时!")
                return False

            # 认证
            log.info("发送认证请求...")
            self.api.req_authenticate(
                CONFIG['broker_id'],
                CONFIG['investor_id'],
                CONFIG['app_id'],
                CONFIG['auth_code'],
                request_id=1
            )

            if not self.auth_event.wait(timeout=10):
                log.error("认证超时!")
                return False

            if not self.authenticated:
                log.error(f"认证失败: {self.error_msg}")
                return False

            # 先尝试登录（会返回错误140，需要改密码）
            log.info("尝试登录（预期会失败）...")
            self.api.req_user_login(
                CONFIG['broker_id'],
                CONFIG['investor_id'],
                CONFIG['old_password'],
                request_id=2
            )

            if not self.login_event.wait(timeout=10):
                log.warn("登录超时，继续尝试修改密码...")

            # 修改密码
            import time
            time.sleep(0.5)  # 等待一下

            log.info("发送修改密码请求...")
            self.api.req_user_password_update(
                CONFIG['broker_id'],
                CONFIG['investor_id'],
                CONFIG['old_password'],
                CONFIG['new_password'],
                request_id=3
            )

            if not self.password_event.wait(timeout=10):
                log.error("修改密码超时!")
                return False

            if not self.password_updated:
                log.error(f"修改密码失败: {self.error_msg}")
                return False

            log.ok("=" * 40)
            log.ok("密码修改成功!")
            log.ok(f"新密码: {CONFIG['new_password']}")
            log.ok("=" * 40)

            return True

        except Exception as e:
            import traceback
            log.error(f"异常: {e}")
            traceback.print_exc()
            return False

        finally:
            if self.api:
                log.info("释放 API...")
                self.api.release()


def main():
    changer = ChangePassword()
    success = changer.run()

    print("\n" + "=" * 60)
    if success:
        print("[PASS] 密码修改成功!")
        print(f"新密码: {CONFIG['new_password']}")
        print("请使用新密码重新运行 login_test.py")
    else:
        print("[FAIL] 密码修改失败!")
    print("=" * 60)
    print(f"\n日志已保存到: {log.log_file}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
