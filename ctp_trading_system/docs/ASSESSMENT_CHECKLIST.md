# 程序化交易系统功能标准符合性测试 - 自评估清单

## 文档信息

| 项目 | 内容 |
|------|------|
| 适用标准 | T/ZQX 0004-2025《期货程序化交易系统功能测试指引》 |
| 系统名称 | CTP程序化交易系统 v1.0 |
| 操作系统 | Windows 10/11 64位 |
| CTP版本 | v6.6.8 (官方API) |
| 测试日期 | 2026-01-15 |
| 测试结果 | **全部通过 (36/36)** |

---

## 自动化测试结果摘要

| 测试类型 | 通过数 | 总数 | 通过率 |
|----------|--------|------|--------|
| UI自动化测试 | 36 | 36 | 100% |
| API整合测试 | 6 | 6 | 100% |
| **总计** | **42** | **42** | **100%** |

---

## 评估项目清单

### 一、接口适应性 (第1项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 1.1 | 是否具备与交易系统的认证功能 | 严重 | ✅ 通过 | 连接登录页 → 客户端认证 | `core/ctp_gateway.py` |
| 1.2 | 是否能正常登录期货公司交易信息系统 | 严重 | ✅ 通过 | 连接登录页 → 用户登录 | `core/ctp_gateway.py` |

**测试步骤:**
1. 打开 Web UI → 连接登录标签页
2. 填写经纪商ID、交易前置地址
3. 点击【连接服务器】
4. 点击【客户端认证】
5. 填写账号密码，点击【用户登录】

**自动化测试:**
- `test_01_01_connect_server` - PASSED
- `test_01_02_authenticate` - PASSED
- `test_01_03_login` - PASSED

---

### 二、基础交易功能 (第2-4项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 2 | 是否能正常下开仓指令 | 严重 | ✅ 通过 | 交易操作页 → 买入/卖出开仓 | `core/ctp_gateway.py` |
| 3 | 是否能正常下平仓指令 | 严重 | ✅ 通过 | 交易操作页 → 买入/卖出平仓 | `core/ctp_gateway.py` |
| 4 | 是否能正常下撤单指令 | 严重 | ✅ 通过 | 交易操作页 → 委托列表撤单 | `core/ctp_gateway.py` |

**自动化测试:**
- `test_02_open_position` - PASSED
- `test_03_close_position` - PASSED
- `test_04_cancel_order` - PASSED

---

### 三、异常监测 - 系统连接状态 (第5项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 5 | 是否能监测启动、正常运行、断开、重连的连接状态 | 严重 | ✅ 通过 | 监测面板页 → 连接状态 | `monitor/connection_monitor.py` |

**连接状态说明:**
- STARTING: 启动中
- CONNECTED: 已连接（正常运行）
- DISCONNECTED: 断开连接
- RECONNECTING: 重连中
- AUTHENTICATED: 已认证
- LOGGED_IN: 已登录
- ERROR: 错误

**自动化测试:**
- `test_05_connection_monitoring` - PASSED

---

### 四、异常监测 - 重复报单监测 (第6-8项) - 建议

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 6 | 是否能监测单合约重复开仓交易指令数量 | 建议 | ✅ 通过 | 监测面板页 → 报单监测表格 | `monitor/order_monitor.py` |
| 7 | 是否能监测单合约重复平仓交易指令数量 | 建议 | ✅ 通过 | 监测面板页 → 报单监测表格 | `monitor/order_monitor.py` |
| 8 | 是否能监测单合约重复撤单交易指令数量 | 建议 | ✅ 通过 | 监测面板页 → 报单监测表格 | `monitor/order_monitor.py` |

**自动化测试:**
- `test_06_repeat_open_monitoring` - PASSED
- `test_07_repeat_close_monitoring` - PASSED
- `test_08_repeat_cancel_monitoring` - PASSED

---

### 五、异常监测 - 报撤单笔数监测 (第9-10项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 9 | 是否能监测同一账号的报单交易指令数量 | 严重 | ✅ 通过 | 监测面板页 → 账号统计 | `monitor/order_monitor.py` |
| 10 | 是否能监测同一账号的撤单交易指令数量 | 严重 | ✅ 通过 | 监测面板页 → 账号统计 | `monitor/order_monitor.py` |

**自动化测试:**
- `test_09_total_order_monitoring` - PASSED
- `test_10_total_cancel_monitoring` - PASSED

---

### 六、阈值管理 - 重复报单阈值及预警 (第11项) - 建议

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 11.1 | 是否提供重复报单笔数的阈值设置功能 | 建议 | ✅ 通过 | 阈值设置页 → 重复报单阈值 | `monitor/threshold_manager.py` |
| 11.2 | 重复开仓达到阈值时是否能预警 | 建议 | ✅ 通过 | 弹窗/声音提示 | `alert/alert_service.py` |
| 11.3 | 重复平仓达到阈值时是否能预警 | 建议 | ✅ 通过 | 弹窗/声音提示 | `alert/alert_service.py` |
| 11.4 | 重复撤单达到阈值时是否能预警 | 建议 | ✅ 通过 | 弹窗/声音提示 | `alert/alert_service.py` |

**预警方式:**
- ✅ 弹窗提示
- ✅ 声音提示
- ⬜ 短信通知（需配置）
- ⬜ 邮件通知（需配置）

**自动化测试:**
- `test_11_01_repeat_order_threshold_setting` - PASSED
- `test_11_02_repeat_open_alert` - PASSED
- `test_11_03_repeat_close_alert` - PASSED
- `test_11_04_repeat_cancel_alert` - PASSED

---

### 七、阈值管理 - 报单总笔数阈值及预警 (第12项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 12.1 | 是否提供报单总笔数的阈值设置功能 | 严重 | ✅ 通过 | 阈值设置页 → 总量阈值 | `monitor/threshold_manager.py` |
| 12.2 | 报单总笔数达到阈值时是否能预警 | 严重 | ✅ 通过 | 弹窗/声音提示 | `alert/alert_service.py` |

**自动化测试:**
- `test_12_01_total_order_threshold_setting` - PASSED
- `test_12_02_total_order_alert` - PASSED

---

### 八、阈值管理 - 撤单总笔数阈值及预警 (第13项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 13.1 | 是否提供撤单总笔数的阈值设置功能 | 严重 | ✅ 通过 | 阈值设置页 → 总量阈值 | `monitor/threshold_manager.py` |
| 13.2 | 撤单总笔数达到阈值时是否能预警 | 严重 | ✅ 通过 | 弹窗/声音提示 | `alert/alert_service.py` |

**自动化测试:**
- `test_13_01_total_cancel_threshold_setting` - PASSED
- `test_13_02_total_cancel_alert` - PASSED

---

### 九、错误防范 - 交易指令检查 (第14-16项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 14 | 合约代码错误时是否能检查出错误 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |
| 15 | 价格最小变动价位错误时是否能检查出错误 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |
| 16 | 委托数量超出限制时是否能检查出错误 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |

**错误代码:**
- `INVALID_INSTRUMENT`: 合约代码不存在或已过期
- `INVALID_PRICE`: 价格不符合最小变动单位
- `INVALID_VOLUME`: 委托数量超出限制或为负数

**自动化测试:**
- `test_14_invalid_instrument` - PASSED
- `test_15_invalid_price` - PASSED
- `test_16_invalid_volume` - PASSED

---

### 十、错误防范 - 错误提示功能 (第17-19项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 17 | 资金不足时是否显示错误提示 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |
| 18 | 持仓不足时是否显示错误提示 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |
| 19 | 非交易时间是否显示错误提示 | 严重 | ✅ 通过 | 错误防范测试页 → 测试 | `validator/order_validator.py` |

**错误代码:**
- `INSUFFICIENT_MARGIN`: 可用资金不足
- `INSUFFICIENT_POSITION`: 持仓不足
- `NON_TRADING_TIME`: 当前不在交易时段

**自动化测试:**
- `test_17_insufficient_margin` - PASSED
- `test_18_insufficient_position` - PASSED
- `test_19_non_trading_time` - PASSED

---

### 十一、应急处置 - 暂停交易功能 (第20项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 20 | 是否能通过限制账号权限、停止策略、强制退出等方式暂停交易 | 严重 | ✅ 通过 | 应急处置页 → 暂停交易 | `emergency/emergency_handler.py` |

**暂停交易方式:**
- ✅ 限制账号权限（禁用交易）
- ✅ 停止策略执行
- ✅ 强制退出账号

**自动化测试:**
- `test_20_pause_trading` - PASSED

---

### 十二、应急处置 - 批量撤单功能 (第23-24项) - 建议

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 23 | 是否能提供部分撤单功能 | 建议 | ✅ 通过 | 应急处置页 → 按合约撤单 | `emergency/emergency_handler.py` |
| 24 | 是否能提供全部撤单功能 | 建议 | ✅ 通过 | 应急处置页 → 全部撤单 | `emergency/emergency_handler.py` |

**自动化测试:**
- `test_23_cancel_by_instrument` - PASSED
- `test_24_cancel_all` - PASSED

---

### 十三、日志记录功能 (第25项) - 严重

| 序号 | 评价内容 | 问题等级 | 自评结果 | 测试方法 | 实现模块 |
|------|----------|----------|----------|----------|----------|
| 25.1 | 是否能提供日志记录功能 | 严重 | ✅ 通过 | 日志查看页 | `trade_logging/trade_logger.py` |
| 25.2 | 日志是否包括交易日志、系统运行记录、监测记录、错误提示 | 严重 | ✅ 通过 | 日志查看页 → 各类型日志 | `trade_logging/trade_logger.py` |

**日志类型:**
- TRADE: 交易日志（报单、成交、撤单）
- SYSTEM: 系统日志（启动、连接、登录）
- MONITOR: 监测日志（阈值检查、统计更新）
- ERROR: 错误日志（各类错误和异常）

**自动化测试:**
- `test_25_01_logging_function_exists` - PASSED
- `test_25_02_trade_log` - PASSED
- `test_25_03_system_log` - PASSED
- `test_25_04_monitor_log` - PASSED
- `test_25_05_error_log` - PASSED
- `test_25_06_log_export` - PASSED
- `test_25_07_log_filter` - PASSED

---

## 评估结果统计

| 问题等级 | 总数 | 通过 | 未通过 |
|----------|------|------|--------|
| 严重 | 21 | 21 | 0 |
| 建议 | 9 | 9 | 0 |
| **合计** | **30** | **30** | **0** |

---

## 测试环境

| 项目 | 配置 |
|------|------|
| 操作系统 | Windows 11 64位 |
| Python版本 | 3.14.0 |
| CTP版本 | v6.6.8_T1_20220520 (官方API) |
| 测试服务器 | 仿真环境 tcp://124.74.247.136:21407 |
| 经纪商ID | 66666 |
| 测试账号 | 88003785 |

---

## 测试报告文件

| 报告类型 | 文件路径 |
|----------|----------|
| HTML报告 | `test_reports/final_report.html` |
| JSON报告 | `test_reports/final_report.json` |

---

## 自动化测试命令

```bash
# 运行全部UI测试
cd D:\CTP\ctp_trading_system
python -m web.app &  # 启动Web服务器
python -m pytest tests/test_assessment.py -v

# 运行API整合测试
python integration_test.py

# 生成HTML测试报告
python -m pytest tests/test_assessment.py --html=test_reports/report.html --self-contained-html
```

---

**签字确认:**

测试人员: ________________  日期: 2026-01-15

审核人员: ________________  日期: ________________
