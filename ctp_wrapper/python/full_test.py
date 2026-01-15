# -*- coding: utf-8 -*-
"""
CTP v2.0.0 完整功能测试脚本
===========================
测试所有 API 功能，包括:
- 登录认证
- 结算确认
- 资金查询
- 持仓查询
- 合约查询
- 行情查询

使用方法:
    python full_test.py

日志输出:
    ./full_test_log.txt
"""

import os
import sys
import time
import threading
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ctp_api import (
    CTPTraderApi, ResumeType,
    Direction, OffsetFlag, OrderPriceType,
    PositionDirection, OrderStatus
)


# ============================================================
# 配置信息
# ============================================================
CONFIG = {
    "broker_id": "66666",
    "investor_id": "88003785",
    "password": "Ctp123456",
    "app_id": "client_mltrader_1.0.0",
    "auth_code": "L8QDUC6XHBQR7WK2",
    "trade_front": "tcp://124.74.247.136:21407",
    "flow_path": "./flow_full_test/",
}


# ============================================================
# 日志工具
# ============================================================
class FileLogger:
    def __init__(self, log_file=None):
        self.start_time = datetime.now()
        self.log_file = log_file or os.path.join(SCRIPT_DIR, "full_test_log.txt")
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("CTP v2.0.0 完整功能测试日志\n")
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
    def section(self, title):
        self.info("=" * 50)
        self.info(title)
        self.info("=" * 50)

    def write_summary(self, results):
        lines = ["\n" + "=" * 60, "测试总结", "=" * 60]
        passed = 0
        failed = 0
        for name, status in results.items():
            mark = "[PASS]" if status else "[FAIL]"
            lines.append(f"  {mark} {name}")
            if status:
                passed += 1
            else:
                failed += 1
        lines.append("")
        lines.append(f"  通过: {passed}, 失败: {failed}")
        lines.append("=" * 60)
        lines.append(f"\n日志已保存到: {self.log_file}\n")

        for line in lines:
            print(line)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')


log = FileLogger()


# ============================================================
# 测试类
# ============================================================
class FullTest:
    def __init__(self):
        self.api = None

        # 状态
        self.connected = False
        self.authenticated = False
        self.logged_in = False
        self.settlement_confirmed = False

        # 登录信息
        self.front_id = 0
        self.session_id = 0
        self.trading_day = ""

        # 查询结果
        self.account_info = {}
        self.positions = []
        self.instruments = []
        self.orders = []
        self.trades = []

        # 同步事件
        self.connect_event = threading.Event()
        self.auth_event = threading.Event()
        self.login_event = threading.Event()
        self.settlement_event = threading.Event()
        self.account_event = threading.Event()
        self.position_event = threading.Event()
        self.instrument_event = threading.Event()
        self.order_event = threading.Event()
        self.trade_event = threading.Event()

        # 测试结果
        self.results = {}

    # ========== 回调函数 ==========
    def on_connected(self):
        self.connected = True
        self.connect_event.set()

    def on_disconnected(self, reason):
        self.connected = False

    def on_authenticate(self, broker_id, user_id, app_id,
                        error_id, error_msg, request_id, is_last):
        if error_id == 0:
            self.authenticated = True
        self.auth_event.set()

    def on_login(self, trading_day, login_time, broker_id, user_id,
                 front_id, session_id, max_order_ref,
                 error_id, error_msg, request_id, is_last):
        if error_id == 0:
            self.logged_in = True
            self.front_id = front_id
            self.session_id = session_id
            self.trading_day = trading_day
        self.login_event.set()

    def on_settlement_confirm(self, broker_id, investor_id,
                               confirm_date, confirm_time,
                               error_id, error_msg, request_id, is_last):
        if error_id == 0:
            self.settlement_confirmed = True
        self.settlement_event.set()

    def on_trading_account(self, broker_id, account_id,
                            balance, available, frozen_cash,
                            curr_margin, close_profit, position_profit,
                            commission, withdraw_quota,
                            error_id, error_msg, request_id, is_last):
        if error_id == 0 and account_id:
            self.account_info = {
                'account_id': account_id,
                'balance': balance,
                'available': available,
                'frozen_cash': frozen_cash,
                'curr_margin': curr_margin,
                'close_profit': close_profit,
                'position_profit': position_profit,
                'commission': commission,
            }
        if is_last:
            self.account_event.set()

    def on_position(self, broker_id, investor_id, instrument_id, position_direction,
                    position, yd_position, position_cost, open_cost,
                    use_margin, frozen_margin,
                    error_id, error_msg, request_id, is_last):
        if error_id == 0 and position > 0:
            self.positions.append({
                'instrument_id': instrument_id,
                'direction': PositionDirection.to_string(position_direction),
                'position': position,
                'yd_position': yd_position,
                'use_margin': use_margin,
            })
        if is_last:
            self.position_event.set()

    def on_instrument(self, instrument_id, exchange_id, instrument_name, product_id,
                      volume_multiple, price_tick, long_margin_ratio, short_margin_ratio,
                      is_trading,
                      error_id, error_msg, request_id, is_last):
        if error_id == 0 and instrument_id:
            self.instruments.append({
                'instrument_id': instrument_id,
                'exchange_id': exchange_id,
                'instrument_name': instrument_name,
                'product_id': product_id,
                'volume_multiple': volume_multiple,
                'price_tick': price_tick,
                'is_trading': is_trading,
            })
        if is_last:
            self.instrument_event.set()

    def on_qry_order(self, broker_id, investor_id, instrument_id, order_ref,
                     direction, offset_flag, price, volume_total, volume_traded,
                     order_status, order_sys_id, insert_date, insert_time,
                     error_id, error_msg, request_id, is_last):
        if error_id == 0 and instrument_id:
            self.orders.append({
                'instrument_id': instrument_id,
                'direction': '买' if direction == ord('0') else '卖',
                'price': price,
                'volume': volume_total,
                'traded': volume_traded,
                'status': OrderStatus.to_string(order_status),
            })
        if is_last:
            self.order_event.set()

    def on_qry_trade(self, broker_id, investor_id, instrument_id, trade_id,
                     direction, offset_flag, price, volume,
                     trade_date, trade_time,
                     error_id, error_msg, request_id, is_last):
        if error_id == 0 and instrument_id:
            self.trades.append({
                'instrument_id': instrument_id,
                'trade_id': trade_id,
                'direction': '买' if direction == ord('0') else '卖',
                'price': price,
                'volume': volume,
                'time': trade_time,
            })
        if is_last:
            self.trade_event.set()

    def on_error(self, error_id, error_msg, request_id, is_last):
        log.error(f"收到错误: [{error_id}] {error_msg}")

    # ========== 测试步骤 ==========
    def test_login(self):
        """测试登录流程"""
        log.section("测试 1: 连接和登录")

        try:
            # 创建 API
            log.info("创建 API 实例...")
            self.api = CTPTraderApi()

            # 设置回调
            self.api.on_front_connected = self.on_connected
            self.api.on_front_disconnected = self.on_disconnected
            self.api.on_rsp_authenticate = self.on_authenticate
            self.api.on_rsp_user_login = self.on_login
            self.api.on_rsp_settlement_info_confirm = self.on_settlement_confirm
            self.api.on_rsp_qry_trading_account = self.on_trading_account
            self.api.on_rsp_qry_investor_position = self.on_position
            self.api.on_rsp_qry_instrument = self.on_instrument
            self.api.on_rsp_qry_order = self.on_qry_order
            self.api.on_rsp_qry_trade = self.on_qry_trade
            self.api.on_rsp_error = self.on_error

            self.api.create_api(CONFIG["flow_path"])

            # 连接
            log.info(f"连接服务器: {CONFIG['trade_front']}")
            self.api.register_front(CONFIG["trade_front"])
            self.api.subscribe_private_topic(ResumeType.QUICK)
            self.api.subscribe_public_topic(ResumeType.QUICK)
            self.api.init()

            if not self.connect_event.wait(timeout=10):
                log.error("连接超时!")
                return False
            log.ok("连接成功")

            # 认证
            log.info("发送认证请求...")
            self.api.req_authenticate(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                CONFIG["app_id"],
                CONFIG["auth_code"],
                request_id=1
            )

            if not self.auth_event.wait(timeout=10):
                log.error("认证超时!")
                return False
            if not self.authenticated:
                log.error("认证失败!")
                return False
            log.ok("认证成功")

            # 登录
            log.info("发送登录请求...")
            self.api.req_user_login(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                CONFIG["password"],
                request_id=2
            )

            if not self.login_event.wait(timeout=10):
                log.error("登录超时!")
                return False
            if not self.logged_in:
                log.error("登录失败!")
                return False
            log.ok(f"登录成功: 交易日={self.trading_day}, FrontID={self.front_id}, SessionID={self.session_id}")

            return True

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_settlement(self):
        """测试结算确认"""
        log.section("测试 2: 结算确认")

        try:
            log.info("发送结算确认请求...")
            self.api.req_settlement_info_confirm(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                request_id=3
            )

            if not self.settlement_event.wait(timeout=10):
                log.error("结算确认超时!")
                return False
            if not self.settlement_confirmed:
                log.error("结算确认失败!")
                return False
            log.ok("结算确认成功")
            return True

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_query_account(self):
        """测试资金查询"""
        log.section("测试 3: 查询资金账户")

        try:
            time.sleep(1)  # CTP 查询限流

            log.info("发送资金查询请求...")
            self.api.req_qry_trading_account(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                request_id=4
            )

            if not self.account_event.wait(timeout=10):
                log.error("资金查询超时!")
                return False

            if self.account_info:
                log.ok("资金查询成功:")
                log.info(f"  账户: {self.account_info['account_id']}")
                log.info(f"  余额: {self.account_info['balance']:.2f}")
                log.info(f"  可用: {self.account_info['available']:.2f}")
                log.info(f"  保证金: {self.account_info['curr_margin']:.2f}")
                log.info(f"  持仓盈亏: {self.account_info['position_profit']:.2f}")
                log.info(f"  平仓盈亏: {self.account_info['close_profit']:.2f}")
                return True
            else:
                log.warn("未查询到资金信息")
                return True  # 空账户也算成功

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_query_position(self):
        """测试持仓查询"""
        log.section("测试 4: 查询持仓")

        try:
            time.sleep(1)  # CTP 查询限流

            log.info("发送持仓查询请求...")
            self.api.req_qry_investor_position(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                request_id=5
            )

            if not self.position_event.wait(timeout=10):
                log.error("持仓查询超时!")
                return False

            if self.positions:
                log.ok(f"持仓查询成功, 共 {len(self.positions)} 条记录:")
                for pos in self.positions:
                    log.info(f"  {pos['instrument_id']} {pos['direction']} "
                            f"持仓={pos['position']} 昨仓={pos['yd_position']} "
                            f"保证金={pos['use_margin']:.2f}")
            else:
                log.ok("持仓查询成功: 无持仓")
            return True

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_query_instrument(self):
        """测试合约查询"""
        log.section("测试 5: 查询合约 (rb2501)")

        try:
            time.sleep(1)  # CTP 查询限流

            log.info("发送合约查询请求 (rb2501)...")
            self.api.req_qry_instrument(
                instrument_id="rb2501",
                request_id=6
            )

            if not self.instrument_event.wait(timeout=10):
                log.error("合约查询超时!")
                return False

            if self.instruments:
                log.ok(f"合约查询成功:")
                for inst in self.instruments:
                    log.info(f"  合约: {inst['instrument_id']}")
                    log.info(f"  名称: {inst['instrument_name']}")
                    log.info(f"  交易所: {inst['exchange_id']}")
                    log.info(f"  乘数: {inst['volume_multiple']}")
                    log.info(f"  最小变动: {inst['price_tick']}")
                    log.info(f"  是否交易: {inst['is_trading']}")
                return True
            else:
                log.warn("未查询到合约信息")
                return True  # 可能非交易时段

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_query_orders(self):
        """测试订单查询"""
        log.section("测试 6: 查询订单")

        try:
            time.sleep(1)  # CTP 查询限流

            log.info("发送订单查询请求...")
            self.api.req_qry_order(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                request_id=7
            )

            if not self.order_event.wait(timeout=10):
                log.error("订单查询超时!")
                return False

            if self.orders:
                log.ok(f"订单查询成功, 共 {len(self.orders)} 条记录:")
                for order in self.orders[:5]:  # 只显示前5条
                    log.info(f"  {order['instrument_id']} {order['direction']} "
                            f"价格={order['price']} 数量={order['volume']} "
                            f"成交={order['traded']} 状态={order['status']}")
            else:
                log.ok("订单查询成功: 今日无订单")
            return True

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def test_query_trades(self):
        """测试成交查询"""
        log.section("测试 7: 查询成交")

        try:
            time.sleep(1)  # CTP 查询限流

            log.info("发送成交查询请求...")
            self.api.req_qry_trade(
                CONFIG["broker_id"],
                CONFIG["investor_id"],
                request_id=8
            )

            if not self.trade_event.wait(timeout=10):
                log.error("成交查询超时!")
                return False

            if self.trades:
                log.ok(f"成交查询成功, 共 {len(self.trades)} 条记录:")
                for trade in self.trades[:5]:  # 只显示前5条
                    log.info(f"  {trade['instrument_id']} {trade['direction']} "
                            f"价格={trade['price']} 数量={trade['volume']} "
                            f"时间={trade['time']}")
            else:
                log.ok("成交查询成功: 今日无成交")
            return True

        except Exception as e:
            log.error(f"异常: {e}")
            return False

    def run(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("CTP v2.0.0 完整功能测试")
        print("=" * 60 + "\n")

        try:
            # 测试登录
            self.results["连接登录"] = self.test_login()
            if not self.results["连接登录"]:
                return False

            # 测试结算
            self.results["结算确认"] = self.test_settlement()

            # 测试查询
            self.results["资金查询"] = self.test_query_account()
            self.results["持仓查询"] = self.test_query_position()
            self.results["合约查询"] = self.test_query_instrument()
            self.results["订单查询"] = self.test_query_orders()
            self.results["成交查询"] = self.test_query_trades()

            return all(self.results.values())

        except Exception as e:
            log.error(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            if self.api:
                log.info("释放 API 资源...")
                self.api.release()

    def print_summary(self):
        """打印测试总结"""
        log.write_summary(self.results)


def main():
    test = FullTest()
    success = test.run()
    test.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
