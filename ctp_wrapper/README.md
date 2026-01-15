# CTP API Python 封装 (v2.0.0)

基于 CTP v6.6.8 的完整 Python 封装，通过 C Wrapper + ctypes 实现。

## 特性

- **完整功能**: 覆盖 CTP TraderApi 所有常用功能
- **纯 C 封装**: 使用 C 接口封装 C++ API，避免 ABI 兼容问题
- **类型安全**: 完整的 Python 类型提示
- **自动日志**: 内置日志系统，自动记录 API 调用和回调
- **常量定义**: 完整的枚举常量（方向、开平、报单类型等）

## 目录结构

```
ctp_wrapper/
├── README.md                    # 本文档
├── src/
│   ├── ctp_wrapper.h           # C 接口头文件
│   └── ctp_wrapper.cpp         # C++ 实现
├── include/                     # CTP 原始头文件
│   ├── ThostFtdcTraderApi.h
│   ├── ThostFtdcUserApiStruct.h
│   └── ThostFtdcUserApiDataType.h
├── lib/                         # CTP 库文件
│   └── thosttraderapi_se.lib
├── python/
│   ├── ctp_api.py              # Python 封装
│   ├── login_test.py           # 登录测试
│   ├── change_password.py      # 修改密码
│   ├── full_test.py            # 完整功能测试
│   ├── ctp_wrapper.dll         # 编译后的 DLL
│   └── thosttraderapi_se.dll   # CTP 原始 DLL
└── compile_msvc.bat            # MSVC 编译脚本
```

## 功能列表

### 1. 连接管理
| 函数 | 说明 |
|------|------|
| `create_api(flow_path)` | 创建 API 实例 |
| `release()` | 释放 API 实例 |
| `register_front(address)` | 注册前置地址 |
| `subscribe_private_topic(type)` | 订阅私有流 |
| `subscribe_public_topic(type)` | 订阅公共流 |
| `init()` | 初始化连接 |
| `join()` | 等待线程结束 |
| `get_trading_day()` | 获取交易日 |
| `get_api_version()` | 获取 API 版本 |

### 2. 认证登录
| 函数 | 说明 |
|------|------|
| `req_authenticate(...)` | 客户端认证 |
| `req_user_login(...)` | 用户登录 |
| `req_user_logout(...)` | 用户登出 |
| `req_user_password_update(...)` | 修改密码 |

### 3. 结算管理
| 函数 | 说明 |
|------|------|
| `req_settlement_info_confirm(...)` | 结算信息确认 |
| `req_qry_settlement_info(...)` | 查询结算信息 |

### 4. 交易功能
| 函数 | 说明 |
|------|------|
| `req_order_insert(...)` | 报单（开仓/平仓） |
| `req_order_action(...)` | 撤单 |

### 5. 查询功能
| 函数 | 说明 |
|------|------|
| `req_qry_order(...)` | 查询订单 |
| `req_qry_trade(...)` | 查询成交 |
| `req_qry_investor_position(...)` | 查询持仓 |
| `req_qry_trading_account(...)` | 查询资金账户 |
| `req_qry_instrument(...)` | 查询合约 |
| `req_qry_depth_market_data(...)` | 查询行情 |
| `req_qry_instrument_margin_rate(...)` | 查询保证金率 |
| `req_qry_instrument_commission_rate(...)` | 查询手续费率 |

### 6. 回调事件
| 回调 | 说明 |
|------|------|
| `on_front_connected` | 连接成功 |
| `on_front_disconnected` | 连接断开 |
| `on_heartbeat_warning` | 心跳超时警告 |
| `on_rsp_authenticate` | 认证响应 |
| `on_rsp_user_login` | 登录响应 |
| `on_rsp_user_logout` | 登出响应 |
| `on_rsp_user_password_update` | 改密响应 |
| `on_rsp_error` | 错误响应 |
| `on_rsp_settlement_info_confirm` | 结算确认响应 |
| `on_rsp_qry_settlement_info` | 结算查询响应 |
| `on_rsp_order_insert` | 报单响应 |
| `on_rsp_order_action` | 撤单响应 |
| `on_rtn_order` | 报单回报 |
| `on_rtn_trade` | 成交回报 |
| `on_err_rtn_order_insert` | 报单错误回报 |
| `on_err_rtn_order_action` | 撤单错误回报 |
| `on_rsp_qry_order` | 订单查询响应 |
| `on_rsp_qry_trade` | 成交查询响应 |
| `on_rsp_qry_investor_position` | 持仓查询响应 |
| `on_rsp_qry_trading_account` | 资金查询响应 |
| `on_rsp_qry_instrument` | 合约查询响应 |
| `on_rsp_qry_depth_market_data` | 行情查询响应 |
| `on_rsp_qry_instrument_margin_rate` | 保证金率查询响应 |
| `on_rsp_qry_instrument_commission_rate` | 手续费率查询响应 |

## 常量定义

### 买卖方向 (Direction)
```python
Direction.BUY   # 买入
Direction.SELL  # 卖出
```

### 开平标志 (OffsetFlag)
```python
OffsetFlag.OPEN             # 开仓
OffsetFlag.CLOSE            # 平仓
OffsetFlag.CLOSE_TODAY      # 平今
OffsetFlag.CLOSE_YESTERDAY  # 平昨
OffsetFlag.FORCE_CLOSE      # 强平
```

### 报单价格类型 (OrderPriceType)
```python
OrderPriceType.LIMIT_PRICE  # 限价
OrderPriceType.ANY_PRICE    # 任意价（市价）
OrderPriceType.BEST_PRICE   # 最优价
```

### 有效期类型 (TimeCondition)
```python
TimeCondition.IOC  # 立即完成，否则撤销
TimeCondition.GFD  # 当日有效
TimeCondition.GTC  # 撤销前有效
```

### 成交量类型 (VolumeCondition)
```python
VolumeCondition.ANY  # 任意数量
VolumeCondition.ALL  # 全部数量（FOK）
VolumeCondition.MIN  # 最小数量
```

### 报单状态 (OrderStatus)
```python
OrderStatus.ALL_TRADED              # 全部成交
OrderStatus.PART_TRADED_QUEUEING    # 部分成交(排队中)
OrderStatus.NO_TRADE_QUEUEING       # 未成交(排队中)
OrderStatus.CANCELED                # 已撤单
```

### 持仓方向 (PositionDirection)
```python
PositionDirection.LONG   # 多头
PositionDirection.SHORT  # 空头
PositionDirection.NET    # 净持仓
```

### 订阅模式 (ResumeType)
```python
ResumeType.RESTART  # 从本交易日开始重传
ResumeType.RESUME   # 从上次收到的续传
ResumeType.QUICK    # 只传送登录后的流内容
```

## 使用示例

### 基础登录
```python
from ctp_api import CTPTraderApi, ResumeType
import threading

# 创建 API 实例
api = CTPTraderApi()

# 同步事件
connect_event = threading.Event()
login_event = threading.Event()

# 设置回调
def on_connected():
    connect_event.set()

def on_login(trading_day, login_time, broker_id, user_id,
             front_id, session_id, max_order_ref,
             error_id, error_msg, request_id, is_last):
    if error_id == 0:
        print(f"登录成功! 交易日={trading_day}")
    login_event.set()

api.on_front_connected = on_connected
api.on_rsp_user_login = on_login

# 初始化连接
api.create_api("./flow/")
api.register_front("tcp://180.168.146.187:10201")
api.subscribe_private_topic(ResumeType.QUICK)
api.subscribe_public_topic(ResumeType.QUICK)
api.init()

# 等待连接
connect_event.wait(timeout=10)

# 认证
api.req_authenticate("9999", "123456", "simnow_client_test", "0000000000000000")
# ... 等待认证响应

# 登录
api.req_user_login("9999", "123456", "password")
login_event.wait(timeout=10)

# 释放
api.release()
```

### 报单交易
```python
from ctp_api import Direction, OffsetFlag, OrderPriceType

# 买入开仓
api.req_order_insert(
    broker_id="9999",
    investor_id="123456",
    instrument_id="rb2501",
    order_ref="1",
    direction=Direction.BUY,
    offset_flag=OffsetFlag.OPEN,
    price=3500.0,
    volume=1,
    order_price_type=OrderPriceType.LIMIT_PRICE
)

# 卖出平仓
api.req_order_insert(
    broker_id="9999",
    investor_id="123456",
    instrument_id="rb2501",
    order_ref="2",
    direction=Direction.SELL,
    offset_flag=OffsetFlag.CLOSE,
    price=3510.0,
    volume=1
)
```

### 撤单
```python
# 方式1: 使用 order_ref + front_id + session_id
api.req_order_action(
    broker_id="9999",
    investor_id="123456",
    instrument_id="rb2501",
    order_ref="1",
    front_id=front_id,
    session_id=session_id
)

# 方式2: 使用 exchange_id + order_sys_id
api.req_order_action(
    broker_id="9999",
    investor_id="123456",
    instrument_id="rb2501",
    exchange_id="SHFE",
    order_sys_id="123456789"
)
```

### 查询资金
```python
# 设置回调
def on_trading_account(broker_id, account_id, balance, available, frozen_cash,
                       curr_margin, close_profit, position_profit,
                       commission, withdraw_quota,
                       error_id, error_msg, request_id, is_last):
    print(f"账户: {account_id}")
    print(f"  余额: {balance:.2f}")
    print(f"  可用: {available:.2f}")
    print(f"  保证金: {curr_margin:.2f}")
    print(f"  持仓盈亏: {position_profit:.2f}")

api.on_rsp_qry_trading_account = on_trading_account

# 发起查询
api.req_qry_trading_account("9999", "123456")
```

### 查询持仓
```python
from ctp_api import PositionDirection

positions = []

def on_position(broker_id, investor_id, instrument_id, position_direction,
                position, yd_position, position_cost, open_cost,
                use_margin, frozen_margin,
                error_id, error_msg, request_id, is_last):
    if position > 0:
        dir_str = PositionDirection.to_string(position_direction)
        positions.append({
            'instrument': instrument_id,
            'direction': dir_str,
            'position': position,
            'yd_position': yd_position,
            'margin': use_margin
        })

    if is_last:
        for p in positions:
            print(f"{p['instrument']} {p['direction']} 持仓={p['position']}")

api.on_rsp_qry_investor_position = on_position
api.req_qry_investor_position("9999", "123456")
```

## 编译说明

### 环境要求
- Windows 10/11
- Visual Studio Build Tools 2022 (MSVC)
- Python 3.8+

### 编译步骤
```cmd
cd ctp_wrapper
compile_msvc.bat
```

编译成功后，`ctp_wrapper.dll` 将生成在 `python/` 目录下。

### 编译脚本内容
```batch
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

cl /EHsc /LD /DCTP_WRAPPER_EXPORTS ^
   /I"src" /I"include" ^
   /Fe"python\ctp_wrapper.dll" ^
   src\ctp_wrapper.cpp ^
   /link /LIBPATH:"lib" thosttraderapi_se.lib
```

## 注意事项

1. **GBK 编码**: CTP 使用 GBK 编码，Python 封装自动处理编码转换
2. **回调引用**: 回调函数使用 `CFUNCTYPE` 并保持引用，防止垃圾回收
3. **查询限流**: CTP 查询接口有 1 秒限制，建议每次查询间隔 1 秒以上
4. **线程安全**: 回调在 CTP 内部线程执行，注意线程安全
5. **仿真/实盘**: 仿真环境和实盘环境的前置地址不同

## 错误码参考

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 3 | 用户不存在 |
| 4 | 密码错误 |
| 5 | 资金账户不存在 |
| 11 | 报单不存在 |
| 12 | 报单已全部成交 |
| 13 | 报单已撤销 |
| 14 | 报单数量错误 |
| 30 | 无此权限 |
| 31 | 合约不存在 |
| 36 | 投机套保标志错误 |
| 44 | 没有报单交易权限 |
| 51 | 资金不足 |
| 52 | 持仓不足 |
| 140 | 首次登录必须修改密码 |

## 仿真服务器配置

| 配置项 | 值 |
|--------|-----|
| 经纪商ID | 66666 |
| 交易前置 | tcp://124.74.247.136:21407 |
| 行情前置 | tcp://124.74.247.136:21413 |

## 版本历史

### v2.0.0 (2026-01-15)
- 完整功能版本
- 新增: 报单/撤单功能
- 新增: 持仓/资金/订单/成交查询
- 新增: 合约/行情/保证金率/手续费率查询
- 新增: 报单回报/成交回报处理
- 新增: 完整的常量定义

### v1.0.0 (2026-01-14)
- 初始版本
- 支持: 连接/认证/登录/登出
- 支持: 结算确认
- 支持: 修改密码

## 许可证

MIT License
