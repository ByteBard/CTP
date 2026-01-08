#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CTP最小交易Demo - Python版本
功能：连接、登录、查询合约
依赖：需要安装CTP Python封装库
"""

import time
from typing import Optional

# 尝试导入CTP库（需要先安装）
# pip install openctp-ctp
# 或 pip install ctp
try:
    from openctp_ctp import tdapi
    print("[INFO] 使用 openctp-ctp 库")
except ImportError:
    try:
        from ctp import tdapi
        print("[INFO] 使用 ctp 库")
    except ImportError:
        print("[ERROR] 未安装CTP Python库，请安装：")
        print("  pip install openctp-ctp")
        print("  或")
        print("  pip install ctp")
        exit(1)

# ============ 配置信息 ============
BROKER_ID = "9999"           # 模拟经纪商代码，请替换为实际值
INVESTOR_ID = "000001"       # 投资者账号，请替换为实际值
PASSWORD = "123456"          # 密码，请替换为实际值
TRADE_FRONT = "tcp://180.168.146.187:10101"  # CTP交易前置地址

class CtpTraderSpi(tdapi.CThostFtdcTraderSpi):
    """交易SPI回调类"""

    def __init__(self, api):
        super().__init__()
        self.api = api
        self.request_id = 0
        self.is_login = False

    def OnFrontConnected(self):
        """连接成功回调"""
        print("[INFO] 已连接到交易前置")

        # 发送登录请求
        login_req = tdapi.CThostFtdcReqUserLoginField()
        login_req.BrokerID = BROKER_ID
        login_req.UserID = INVESTOR_ID
        login_req.Password = PASSWORD

        self.request_id += 1
        ret = self.api.ReqUserLogin(login_req, self.request_id)
        print(f"[INFO] 发送登录请求, 返回值={ret}")

    def OnFrontDisconnected(self, nReason: int):
        """连接断开回调"""
        print(f"[ERROR] 连接断开, 原因={nReason}")
        self.is_login = False

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID: int, bIsLast: bool):
        """登录响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[ERROR] 登录失败: {pRspInfo.ErrorMsg}")
            return

        print("[INFO] 登录成功!")
        print(f"  交易日: {pRspUserLogin.TradingDay}")
        print(f"  前置编号: {pRspUserLogin.FrontID}")
        print(f"  会话编号: {pRspUserLogin.SessionID}")
        print(f"  最大报单引用: {pRspUserLogin.MaxOrderRef}")

        self.is_login = True

        # 查询合约
        time.sleep(1)  # 等待1秒后查询，避免流控
        qry_req = tdapi.CThostFtdcQryInstrumentField()
        # 不指定合约代码，查询所有合约（实际使用时建议指定）
        # qry_req.InstrumentID = "rb2505"

        self.request_id += 1
        ret = self.api.ReqQryInstrument(qry_req, self.request_id)
        print(f"[INFO] 发送查询合约请求, 返回值={ret}")

    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID: int, bIsLast: bool):
        """查询合约响应"""
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"[ERROR] 查询合约失败: {pRspInfo.ErrorMsg}")
            return

        if pInstrument:
            print(f"  合约: {pInstrument.InstrumentID}, "
                  f"名称: {pInstrument.InstrumentName}, "
                  f"交易所: {pInstrument.ExchangeID}, "
                  f"乘数: {pInstrument.VolumeMultiple}")

        if bIsLast:
            print("[INFO] 合约查询完成")

    def OnRspError(self, pRspInfo, nRequestID: int, bIsLast: bool):
        """错误回调"""
        if pRspInfo:
            print(f"[ERROR] 错误回调: {pRspInfo.ErrorMsg}")


class CtpTrader:
    """CTP交易类"""

    def __init__(self):
        self.api: Optional[tdapi.CThostFtdcTraderApi] = None
        self.spi: Optional[CtpTraderSpi] = None

    def connect(self):
        """连接交易前置"""
        # 1. 创建API实例（指定流文件保存目录）
        self.api = tdapi.CThostFtdcTraderApi.CreateFtdcTraderApi("./flow/")

        # 2. 创建SPI实例并注册
        self.spi = CtpTraderSpi(self.api)
        self.api.RegisterSpi(self.spi)

        # 3. 注册交易前置地址
        self.api.RegisterFront(TRADE_FRONT)

        # 4. 订阅私有流和公有流
        # THOST_TERT_RESTART = 0  # 从本交易日开始重传
        # THOST_TERT_RESUME = 1   # 从上次收到的续传
        # THOST_TERT_QUICK = 2    # 只传送登录后的流内容
        self.api.SubscribePrivateTopic(tdapi.THOST_TERT_QUICK)
        self.api.SubscribePublicTopic(tdapi.THOST_TERT_QUICK)

        # 5. 初始化API
        self.api.Init()
        print("[INFO] 正在连接交易前置...")

    def wait(self):
        """等待，保持程序运行"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")

    def release(self):
        """释放资源"""
        if self.api:
            self.api.Release()
            print("[INFO] 已释放API资源")


def main():
    """主函数"""
    print("=" * 50)
    print("  CTP最小交易Demo - Python版本")
    print("=" * 50)

    # 创建交易对象
    trader = CtpTrader()

    try:
        # 连接
        trader.connect()

        # 等待运行（按Ctrl+C退出）
        trader.wait()

    except Exception as e:
        print(f"[ERROR] 发生异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 释放资源
        trader.release()


if __name__ == "__main__":
    main()

"""
使用说明：

1. 安装依赖：
   # 方式1：使用openctp（推荐，开源且更新）
   pip install openctp-ctp

   # 方式2：使用官方封装
   pip install ctp

   # 方式3：使用vnpy的封装
   pip install vnpy_ctp

2. 运行：
   python python_minimal_demo.py

3. 目录结构：
   D:\CTP\
   ├── python_minimal_demo.py
   ├── flow/                    # 流文件目录（自动创建）
   └── thosttraderapi.dll       # Windows下需要（Linux下为.so文件）

4. 注意事项：
   - 请替换BROKER_ID、INVESTOR_ID、PASSWORD为实际值
   - 交易前置地址TRADE_FRONT需要从期货公司获取
   - 首次运行会创建flow目录保存流文件
   - 查询操作受流控限制（每秒1次），注意添加time.sleep()

5. 进阶功能（取消注释相关代码即可）：
   - 查询资金账户：ReqQryTradingAccount
   - 查询持仓：ReqQryInvestorPosition
   - 报单：ReqOrderInsert
   - 撤单：ReqOrderAction

6. 推荐资源：
   - OpenCTP: https://github.com/openctp/openctp
   - VNPY: https://github.com/vnpy/vnpy
   - 官方文档: http://www.sfit.com.cn/
"""
