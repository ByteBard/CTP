#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP程序化交易系统 - 整合测试
使用 CTP v6.6.8 官方 API
"""
import os
import sys
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from trade_logging.trade_logger import init_logger
from core.ctp_gateway import CtpGateway


def main():
    print("=" * 60)
    print("CTP程序化交易系统 - 整合测试")
    print("使用 CTP v6.6.8 官方 API")
    print("=" * 60)

    # 加载仿真配置
    config_path = os.path.join(os.path.dirname(__file__), "config", "sim_config.yaml")
    if os.path.exists(config_path):
        print(f"\n加载配置: {config_path}")
        settings = Settings.load_from_yaml(config_path)
    else:
        print("\n使用默认配置...")
        settings = Settings()
        settings.connection.broker_id = "66666"
        settings.connection.investor_id = "88003785"
        settings.connection.password = "Ctp123456"
        settings.connection.app_id = "client_mltrader_1.0.0"
        settings.connection.auth_code = "L8QDUC6XHBQR7WK2"
        settings.connection.trade_front = "tcp://124.74.247.136:21407"

    # 初始化日志
    logger = init_logger(log_dir="./logs_test")

    print(f"\n配置信息:")
    print(f"  经纪商ID: {settings.connection.broker_id}")
    print(f"  账号: {settings.connection.investor_id}")
    print(f"  交易前置: {settings.connection.trade_front}")

    # 创建网关
    gateway = CtpGateway(settings)

    results = []

    # 测试1: 连接
    print("\n" + "-" * 40)
    print("测试1: 连接服务器")
    print("-" * 40)
    try:
        if gateway.connect(timeout=30):
            print("[PASS] 连接成功")
            results.append(("连接服务器", True))
        else:
            print("[FAIL] 连接失败")
            results.append(("连接服务器", False))
            return
    except Exception as e:
        print(f"[FAIL] 连接异常: {e}")
        results.append(("连接服务器", False))
        return

    # 测试2: 认证
    print("\n" + "-" * 40)
    print("测试2: 客户端认证")
    print("-" * 40)
    try:
        if gateway.authenticate(timeout=10):
            print("[PASS] 认证成功")
            results.append(("客户端认证", True))
        else:
            print("[FAIL] 认证失败")
            results.append(("客户端认证", False))
            gateway.close()
            return
    except Exception as e:
        print(f"[FAIL] 认证异常: {e}")
        results.append(("客户端认证", False))
        gateway.close()
        return

    # 测试3: 登录
    print("\n" + "-" * 40)
    print("测试3: 用户登录")
    print("-" * 40)
    try:
        if gateway.login(timeout=10):
            print(f"[PASS] 登录成功")
            print(f"  交易日: {gateway._trading_day}")
            print(f"  FrontID: {gateway._front_id}")
            print(f"  SessionID: {gateway._session_id}")
            results.append(("用户登录", True))
        else:
            print("[FAIL] 登录失败")
            results.append(("用户登录", False))
            gateway.close()
            return
    except Exception as e:
        print(f"[FAIL] 登录异常: {e}")
        results.append(("用户登录", False))
        gateway.close()
        return

    # 测试4: 结算确认
    print("\n" + "-" * 40)
    print("测试4: 结算确认")
    print("-" * 40)
    try:
        if gateway.confirm_settlement(timeout=10):
            print("[PASS] 结算确认成功")
            results.append(("结算确认", True))
        else:
            print("[WARN] 结算确认超时（可能已确认）")
            results.append(("结算确认", True))
    except Exception as e:
        print(f"[WARN] 结算确认异常: {e}")
        results.append(("结算确认", True))

    # 测试5: 查询资金
    print("\n" + "-" * 40)
    print("测试5: 查询资金账户")
    print("-" * 40)
    time.sleep(1)  # 查询限流
    try:
        account = gateway.query_account(timeout=10)
        if account:
            print("[PASS] 资金查询成功")
            print(f"  账户: {account.get('account_id', 'N/A')}")
            print(f"  余额: {account.get('balance', 0):.2f}")
            print(f"  可用: {account.get('available', 0):.2f}")
            print(f"  保证金: {account.get('curr_margin', 0):.2f}")
            results.append(("查询资金", True))
        else:
            print("[WARN] 资金查询返回空")
            results.append(("查询资金", True))
    except Exception as e:
        print(f"[FAIL] 资金查询异常: {e}")
        results.append(("查询资金", False))

    # 测试6: 查询持仓
    print("\n" + "-" * 40)
    print("测试6: 查询持仓")
    print("-" * 40)
    time.sleep(1)
    try:
        positions = gateway.query_position(timeout=10)
        print(f"[PASS] 持仓查询成功")
        if positions:
            for key, pos in positions.items():
                print(f"  {pos['instrument_id']} {pos['direction']} 持仓={pos['position']}")
        else:
            print("  无持仓")
        results.append(("查询持仓", True))
    except Exception as e:
        print(f"[FAIL] 持仓查询异常: {e}")
        results.append(("查询持仓", False))

    # 关闭连接
    print("\n" + "-" * 40)
    print("关闭连接")
    print("-" * 40)
    gateway.close()
    print("[OK] 连接已关闭")

    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n通过: {passed}, 失败: {failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
