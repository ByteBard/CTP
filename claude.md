# CTP程序化交易系统 - 项目上下文

## 项目概述

这是一个符合 **T/ZQX 0004-2025《期货程序化交易系统功能测试指引》** 标准的CTP程序化交易系统。

- **开发语言**: Python 3.8+
- **CTP版本**: v6.6.8
- **状态**: 功能框架已完成，正在进行仿真测试

## 项目结构

```
C:\Repo\CTP\
├── Sim/                           # 仿真测试目录
│   ├── sim_login_test.py          # 独立登录测试脚本
│   ├── sim_test_log.txt           # 测试日志输出
│   ├── v6.6.8_T1_20220520_winApi/ # Windows CTP API
│   ├── v6.6.8_T1_20220520_api_tradeapi_linux64/  # Linux CTP API
│   └── 期货仿真测试.txt            # 仿真账号信息
│
├── ctp_trading_system/            # 主项目目录
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
│   ├── tests/test_assessment.py   # 自动化测试
│   └── logs/                      # 运行日志
│
└── claude.md                      # 本文件
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

## 下一步工作

1. 完成仿真环境连接测试
2. 验证基础交易功能（开仓/平仓/撤单）
3. 测试监测和预警功能
4. 完成全部25项评估测试
