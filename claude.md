# CTP程序化交易系统 - 项目上下文

## 项目概述

这是一个符合 **T/ZQX 0004-2025《期货程序化交易系统功能测试指引》** 标准的CTP程序化交易系统。

- **开发语言**: Python 3.8+
- **CTP版本**: v6.6.8 (官方 API，非 openctp)
- **状态**: 已完成全部功能测试 (36/36 通过)

---

## CTP API 说明

**重要：本项目使用官方 CTP v6.6.8 API，不使用 openctp！**

### API 来源

```
Sim/v6.6.8_T1_20220520_winApi/tradeapi/20220520_tradeapi64_se_windows/
├── thostmduserapi_se.dll   # 行情 API
├── thosttraderapi_se.dll   # 交易 API (3.2MB)
└── *.lib                   # 链接库
```

### API 封装架构

```
Python 代码
    ↓ (ctypes)
ctp_wrapper.dll (25KB, 自编 C++ 封装)
    ↓ (调用)
thosttraderapi_se.dll (官方 v6.6.8 API)
```

### 编译 ctp_wrapper.dll

需要 Visual Studio 2022：

```cmd
# 在 VS Developer Command Prompt 中运行
cd C:\Repo\CTP\ctp_wrapper
build.bat
```

输出文件：
- `ctp_wrapper/python/ctp_wrapper.dll`
- `ctp_wrapper/python/thosttraderapi_se.dll`

---

## 快速启动（官方 API 版）

### 打包

```cmd
# 运行打包脚本
build_official_api.bat
```

### 运行

```cmd
cd dist\CTP_Official_v6.6.8
start_server.bat
# 或
python -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000
```

### 打包内容

```
dist/CTP_Official_v6.6.8/
├── ctp_trading_system/
│   ├── ctp_api/
│   │   ├── ctp_api.py           # Python 封装
│   │   ├── ctp_wrapper.dll      # C++ 封装层 (25KB)
│   │   └── thosttraderapi_se.dll # 官方 v6.6.8 API (3.2MB)
│   ├── core/                    # 核心模块
│   ├── monitor/                 # 监测模块
│   ├── validator/               # 验证模块
│   ├── alert/                   # 预警模块
│   ├── emergency/               # 应急模块
│   ├── trade_logging/           # 日志模块
│   └── web/                     # Web UI
├── logs/
└── start_server.bat
```

---

## 自动化测试

### 运行全部测试（36项）

```cmd
# 1. 启动 Web 服务
cd dist\CTP_Official_v6.6.8
python -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000

# 2. 新开命令行窗口，运行后端 API 测试
cd C:\Repo\CTP
python -m pytest ctp_trading_system/tests/test_api_assessment.py -v
```

### 测试结果 (2026-01-24)

```
36 passed in 93.73s (100%)
API: 官方 CTP v6.6.8
测试方式: 后端 API 测试 (httpx)
```

| 类别 | 评估项 | 测试数 | 结果 |
|------|--------|--------|------|
| 接口适应性 | 第1项 | 3 | PASSED |
| 基础交易 | 第2-4项 | 3 | PASSED |
| 异常监测 | 第5-10项 | 6 | PASSED |
| 阈值管理 | 第11-13项 | 8 | PASSED |
| 错误防范 | 第14-19项 | 6 | PASSED |
| 应急处置 | 第20,23-24项 | 3 | PASSED |
| 日志记录 | 第25项 | 7 | PASSED |

---

## 项目结构

```
CTP/
├── build_official_api.bat         # 官方 API 打包脚本
├── dist/
│   └── CTP_Official_v6.6.8/       # 官方 API 打包版本
│
├── ctp_wrapper/                   # CTP C++ 封装层
│   ├── build.bat                  # 编译脚本 (MSVC)
│   ├── src/ctp_wrapper.cpp        # C++ 源码
│   ├── include/                   # CTP 头文件
│   └── python/                    # 编译输出
│       ├── ctp_wrapper.dll
│       └── thosttraderapi_se.dll
│
├── Sim/                           # 仿真测试目录
│   ├── v6.6.8_T1_20220520_winApi/ # 官方 v6.6.8 API
│   │   └── tradeapi/20220520_tradeapi64_se_windows/
│   ├── sim_login_test.py          # 登录测试脚本
│   └── 期货仿真测试.txt            # 仿真账号信息
│
├── ctp_trading_system/            # 主项目源代码
│   ├── main.py                    # 系统主入口
│   ├── ctp_api/                   # CTP Python 封装 (ctypes)
│   │   └── ctp_api.py             # 调用 ctp_wrapper.dll
│   ├── config/settings.py         # 配置管理
│   ├── core/ctp_gateway.py        # CTP 网关
│   ├── monitor/                   # 监测模块
│   ├── validator/                 # 验证模块
│   ├── alert/                     # 预警模块
│   ├── emergency/                 # 应急模块
│   ├── trade_logging/             # 日志模块
│   ├── web/                       # Web UI (FastAPI)
│   ├── tests/test_assessment.py   # 自动化测试 (36项)
│   └── docs/                      # 文档目录
│
└── CLAUDE.md                      # 本文件
```

---

## 仿真服务器配置

| 配置项 | 值 |
|--------|-----|
| 经纪商ID | 66666 |
| 账号 | 88003785 |
| 密码 | 024111 (身份证后六位) |
| AppID | client_mltrader_1.0.0 |
| 授权码 | L8QDUC6XHBQR7WK2 |
| 交易前置 | tcp://124.74.247.136:21407 |
| 行情前置 | tcp://124.74.247.136:21413 |

---

## 评估表覆盖 (T/ZQX 0004-2025)

| 序号 | 评价项目 | 级别 | 模块 | 状态 |
|------|----------|------|------|------|
| 1 | 接口适应性 | 严重 | core/ctp_gateway.py | ✅ |
| 2 | 开仓指令 | 严重 | core/ctp_gateway.py | ✅ |
| 3 | 平仓指令 | 严重 | core/ctp_gateway.py | ✅ |
| 4 | 撤单指令 | 严重 | core/ctp_gateway.py | ✅ |
| 5 | 连接状态监测 | 严重 | monitor/connection_monitor.py | ✅ |
| 6-8 | 重复报单监测 | 建议 | monitor/order_monitor.py | ✅ |
| 9-10 | 报撤单总数 | 严重 | monitor/order_monitor.py | ✅ |
| 11-13 | 阈值预警 | 混合 | monitor/threshold_manager.py | ✅ |
| 14-19 | 错误防范 | 严重 | validator/order_validator.py | ✅ |
| 20,23-24 | 应急处置 | 混合 | emergency/emergency_handler.py | ✅ |
| 25 | 日志记录 | 严重 | trade_logging/trade_logger.py | ✅ |

---

## 依赖安装

```bash
# 核心依赖（不需要 openctp-ctp）
pip install pyyaml loguru fastapi uvicorn jinja2 python-multipart websockets

# 测试依赖
pip install pytest pytest-asyncio playwright httpx
python -m playwright install chromium
```

---

## 测试证据收集工具

**重要：必须使用以下指定工具，不能使用其他替代工具！**

### 1. 截图工具 - Genesis

```
ctp_trading_system/docs/辅助截图工具/Genesis/Genesis.exe
```

- **必须使用** Genesis 进行截图
- 不能使用 Windows 自带截图或其他第三方工具
- 截图保存到 `output/` 目录

### 2. 电子证据工具 - Argus

```
ctp_trading_system/docs/程序化证据收集工具/程序化证据收集工具/Argus.exe
```

使用方法：
1. 启动 Argus.exe
2. 选择被测系统的启动程序（.exe/.dll/.py）
3. 点击"生成电子证据"
4. 输出文件：`ArgusReport_日期_时间.dat`

详见：`ctp_trading_system/docs/程序化证据收集工具使用指引.pdf`

### 启动工具命令

```cmd
# Genesis 截图工具（必须在其目录下启动）
cd C:\Repo\CTP\ctp_trading_system\docs\辅助截图工具\Genesis
Genesis.exe

# Argus 电子证据工具
cd C:\Repo\CTP\ctp_trading_system\docs\程序化证据收集工具\程序化证据收集工具
Argus.exe

# Web 服务
cd C:\Repo\CTP\dist\CTP_Official_v6.6.8
python -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000
```

### 自动化测试脚本

| 脚本 | 用途 |
|------|------|
| `run_test_8_9.py` | 测试点8/9: 发报单+撤单，验证监测面板计数显示 |

### 测试流程

```
1. 手动双击启动 Genesis 截图工具（在其自身目录下）
2. 启动 Web 服务
3. 运行自动化测试脚本
4. 使用 Genesis 截图（不要用其他工具）
5. 测试完成后，使用 Argus 生成电子证据
6. 提交：截图 + ArgusReport_xxx.dat + 测试报告
```

---

## 常见问题

### 1. 连接超时
- 检查网络是否为中国IP
- 检查防火墙设置
- 确认服务器地址和端口

### 2. 认证失败
- 检查 AppID 和授权码是否匹配
- 确认使用正确的 API 版本 (v6.6.8)

### 3. 登录失败
- 检查密码是否正确（身份证后六位）
- 检查账号是否有效

### 4. ctp_wrapper.dll 未找到
- 运行 `ctp_wrapper/build.bat` 编译
- 需要 Visual Studio 2022

---

## 已完成工作

- [x] 完成仿真环境连接测试
- [x] 验证基础交易功能（开仓/平仓/撤单）
- [x] 测试监测和预警功能
- [x] 完成全部 36 项自动化测试 (100% 通过)
- [x] 使用官方 CTP v6.6.8 API 打包（非 openctp）
- [x] 编译 ctp_wrapper.dll 封装层

## 下一步工作

1. 在实盘环境进行验收测试
2. 根据期货公司要求调整配置参数
3. 使用 Argus 工具生成电子证据
