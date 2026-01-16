# CTP程序化交易系统 - 项目上下文

## 项目概述

这是一个符合 **T/ZQX 0004-2025《期货程序化交易系统功能测试指引》** 标准的CTP程序化交易系统。

- **开发语言**: Python 3.8+
- **CTP版本**: v6.6.8
- **状态**: 已完成全部功能测试 (36/36 通过)

---

## 快速启动（便携版）

**无需安装 Python，双击即可运行！**

### 在新机器上运行

```cmd
# 1. 克隆或拉取代码
git clone https://github.com/ByteBard/CTP.git
# 或
git pull

# 2. 双击运行（首次自动解压）
run_portable.bat
```

### 运行流程说明

1. `run_portable.bat` 检测 `dist/CTP_Trading_System.zip` 是否存在
2. 如果 `dist/CTP_Trading_System/` 目录不存在，自动解压 zip 文件
3. 启动 Web 服务，监听 http://127.0.0.1:8000
4. 在浏览器中打开该地址即可使用

### 便携版内容

| 文件/目录 | 说明 |
|-----------|------|
| `run_portable.bat` | 启动脚本（自动解压+运行） |
| `build_portable.bat` | 打包脚本（用于重新打包） |
| `dist/CTP_Trading_System.zip` | 便携版压缩包 (27.4MB) |
| `dist/CTP_Trading_System/` | 解压后的运行目录（自动生成，不提交到git） |

### 便携版包含

- 内嵌 Python 3.11.9 运行环境
- 所有依赖包 (openctp-ctp, fastapi, uvicorn, loguru 等)
- 完整的交易系统代码
- Web UI 界面

---

## 自动化测试

### 运行全部测试（36项）

```cmd
# 1. 启动Web服务（使用便携版Python）
cd dist\CTP_Trading_System
python\python.exe -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000

# 2. 新开命令行窗口，运行测试
cd dist\CTP_Trading_System
python\python.exe -m pip install pytest pytest-playwright pytest-html
python\python.exe -m playwright install chromium
python\python.exe -m pytest ctp_trading_system/tests/test_assessment.py -v
```

### 测试结果 (2026-01-16)

```
36 passed in 152.71s (100%)
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
├── run_portable.bat               # 便携版启动脚本（首次自动解压）
├── build_portable.bat             # 便携版打包脚本
├── dist/
│   └── CTP_Trading_System.zip     # 便携版压缩包 (27.4MB)
│
├── Sim/                           # 仿真测试目录
│   ├── sim_login_test.py          # 独立登录测试脚本
│   ├── sim_test_log.txt           # 测试日志输出
│   └── 期货仿真测试.txt            # 仿真账号信息
│
├── ctp_trading_system/            # 主项目源代码
│   ├── main.py                    # 系统主入口
│   ├── config/settings.py         # 配置管理
│   ├── core/ctp_gateway.py        # CTP网关
│   ├── monitor/                   # 监测模块
│   │   ├── connection_monitor.py  # 连接状态监测
│   │   ├── order_monitor.py       # 报单/撤单监测
│   │   └── threshold_manager.py   # 阈值管理
│   ├── validator/order_validator.py  # 交易验证
│   ├── alert/alert_service.py     # 预警服务
│   ├── emergency/emergency_handler.py  # 应急处置
│   ├── trade_logging/trade_logger.py   # 日志系统
│   ├── web/                       # Web UI (FastAPI)
│   ├── tests/test_assessment.py   # 自动化测试 (36项)
│   ├── docs/                      # 文档目录
│   └── logs/                      # 运行日志
│
└── CLAUDE.md                      # 本文件
```

## 当前任务

### 仿真环境连接测试

由于用户在澳洲，无法直接连接中国的CTP仿真服务器，采用以下工作流程：

1. **切换中国网络** -> 运行测试脚本
2. **切换澳洲网络** -> 与Claude对话分析日志
3. **迭代修复** -> 重复以上步骤

### 测试脚本位置

```
C:\Repo\CTP\Sim\sim_login_test.py
```

运行方式：
```cmd
cd C:\Repo\CTP\Sim
python sim_login_test.py
```

日志输出：
```
C:\Repo\CTP\Sim\sim_test_log.txt
```

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

## 依赖安装

```bash
pip install openctp-ctp pyyaml loguru fastapi uvicorn
```

## 常见问题

### 1. 连接超时
- 检查网络是否为中国IP
- 检查防火墙设置
- 确认服务器地址和端口

### 2. 认证失败
- 检查AppID和授权码是否匹配
- 确认使用正确的API版本

### 3. 登录失败
- 检查密码是否正确（身份证后六位）
- 检查账号是否有效

## 已完成工作

- [x] 完成仿真环境连接测试
- [x] 验证基础交易功能（开仓/平仓/撤单）
- [x] 测试监测和预警功能
- [x] 完成全部36项自动化测试 (100%通过)
- [x] 创建便携版打包 (无需安装Python)

## 下一步工作

1. 在实盘环境进行验收测试
2. 根据期货公司要求调整配置参数
