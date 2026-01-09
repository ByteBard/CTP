# CTP程序化交易系统 Web UI + 自动化测试设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | CTP程序化交易系统 Web UI |
| 版本 | 1.0 |
| 创建日期 | 2026-01-09 |
| 状态 | 待实施 |

---

## 一、项目背景

根据 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》要求，需要对交易系统进行第三方评估测试。为便于测试人员操作和验证各项功能，需要开发Web UI界面，并配套Playwright自动化测试用例。

---

## 二、技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Playwright 测试                         │
│              (自动化验证30项评估表功能)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────────────┐
│                    Web 前端                                  │
│         HTML + CSS + JavaScript (Bootstrap)                 │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 连接登录  │ │ 交易操作  │ │ 监测面板  │ │ 应急处置  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API + WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                  FastAPI 后端                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CTP Trading System                      │   │
│  │  (已实现的 core/monitor/validator/emergency 模块)    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | HTML + Bootstrap 5 + JavaScript | 简洁、响应式 |
| 后端 | FastAPI | 高性能、自动API文档 |
| 实时通信 | WebSocket | 日志/预警实时推送 |
| 自动化测试 | Playwright + Pytest | 浏览器自动化 |

---

## 三、页面设计

### 3.1 整体布局

```
┌────────────────────────────────────────────────────────────────┐
│  CTP程序化交易系统 - 功能测试平台          [系统状态: ●已连接]   │
├────────────────────────────────────────────────────────────────┤
│  [连接登录] [交易操作] [监测面板] [阈值设置] [应急处置] [日志]   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─ 主操作区 ─────────────────────┐ ┌─ 状态/日志区 ──────────┐ │
│  │                                │ │                        │ │
│  │  (根据选中标签显示不同内容)      │ │  实时日志滚动显示       │ │
│  │                                │ │                        │ │
│  │                                │ │  预警消息显示           │ │
│  │                                │ │                        │ │
│  └────────────────────────────────┘ └────────────────────────┘ │
├────────────────────────────────────────────────────────────────┤
│  报单: 0  撤单: 0  │  阈值状态: 正常  │  交易状态: 允许交易     │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 连接登录页 (评估表第1项)

```
┌─ 连接登录 ──────────────────────────────────┐
│                                             │
│  经纪商ID:    [9999        ]                │
│  交易前置:    [tcp://180.168.146.187:10201] │
│  投资者账号:  [____________]                │
│  密码:        [____________]                │
│                                             │
│  [连接服务器]  [客户端认证]  [用户登录]       │
│                                             │
│  ┌─ 连接状态 ─────────────────────────────┐ │
│  │ ● 服务器连接: 未连接                    │ │
│  │ ● 客户端认证: 未认证                    │ │
│  │ ● 用户登录:   未登录                    │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 连接服务器: 建立TCP连接到CTP前置
- 客户端认证: AppID和AuthCode认证
- 用户登录: 投资者账号密码登录

### 3.3 交易操作页 (评估表第2-4项)

```
┌─ 交易操作 ──────────────────────────────────┐
│                                             │
│  合约代码: [IF2401    ]  [查询合约]          │
│  价格:     [4000.0    ]                     │
│  数量:     [1         ]                     │
│  方向:     ○买入 ○卖出                      │
│  开平:     ○开仓 ○平仓 ○平今                │
│                                             │
│  [买入开仓] [卖出开仓] [买入平仓] [卖出平仓]  │
│                                             │
│  ┌─ 当前委托 ─────────────────────────────┐ │
│  │ 委托号  合约    方向  价格   数量  状态  │ │
│  │ 001    IF2401  买    4000   1    未成交 │ │
│  │                        [撤单]           │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第2项: 开仓指令 (买入开仓/卖出开仓)
- 第3项: 平仓指令 (买入平仓/卖出平仓)
- 第4项: 撤单指令 (撤单按钮)

### 3.4 监测面板页 (评估表第5-10项)

```
┌─ 监测面板 ──────────────────────────────────┐
│                                             │
│  ┌─ 连接状态监测 (第5项) ────────────────┐  │
│  │ 状态: ● 已连接                        │  │
│  │ 心跳: 2026-01-09 10:30:15            │  │
│  │ 断线次数: 0                           │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌─ 报单监测 (第6-8项) ─────────────────┐   │
│  │ 合约      开仓次数  平仓次数  撤单次数 │   │
│  │ IF2401      3        1         2     │   │
│  │ IF2402      1        0         0     │   │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌─ 账号统计 (第9-10项) ────────────────┐   │
│  │ 今日报单总数: 15                      │   │
│  │ 今日撤单总数: 5                       │   │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第5项: 连接状态监测
- 第6项: 单合约重复开仓监测
- 第7项: 单合约重复平仓监测
- 第8项: 单合约重复撤单监测
- 第9项: 账号报单数量监测
- 第10项: 账号撤单数量监测

### 3.5 阈值设置页 (评估表第11-13项)

```
┌─ 阈值设置 ──────────────────────────────────┐
│                                             │
│  ┌─ 重复报单阈值 (第11项) ──────────────┐   │
│  │ 单合约开仓次数上限: [10  ] [保存]     │   │
│  │ 单合约平仓次数上限: [10  ] [保存]     │   │
│  │ 单合约撤单次数上限: [10  ] [保存]     │   │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌─ 总量阈值 (第12-13项) ───────────────┐   │
│  │ 报单总数上限:       [500 ] [保存]     │   │
│  │ 撤单总数上限:       [400 ] [保存]     │   │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌─ 预警历史 ───────────────────────────┐   │
│  │ 时间        类型      消息            │   │
│  │ 10:30:15   WARNING   撤单次数达到阈值  │   │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第11项: 重复报单阈值及预警
- 第12项: 报单总笔数阈值及预警
- 第13项: 撤单总笔数阈值及预警

### 3.6 错误防范测试页 (评估表第14-19项)

```
┌─ 错误防范测试 ──────────────────────────────┐
│                                             │
│  [测试合约代码错误]     状态: ✓ 通过        │
│  [测试价格最小变动]     状态: ✓ 通过        │
│  [测试委托数量错误]     状态: ✓ 通过        │
│  [测试资金不足]         状态: ✓ 通过        │
│  [测试持仓不足]         状态: ✓ 通过        │
│  [测试非交易时间]       状态: ✓ 通过        │
│                                             │
│  ┌─ 错误提示记录 ───────────────────────┐   │
│  │ 时间       错误类型      提示消息      │   │
│  │ 10:30:15  合约代码错误  合约不存在     │   │
│  │ 10:30:20  价格错误     不符合最小变动  │   │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第14项: 合约代码错误检查
- 第15项: 价格最小变动检查
- 第16项: 委托数量检查
- 第17项: 资金不足提示
- 第18项: 持仓不足提示
- 第19项: 非交易时间提示

### 3.7 应急处置页 (评估表第20, 23-24项)

```
┌─ 应急处置 ──────────────────────────────────┐
│                                             │
│  ┌─ 暂停交易 (第20项) ─────────────────┐    │
│  │                                     │    │
│  │  [暂停交易]    [恢复交易]            │    │
│  │                                     │    │
│  │  当前状态: ● 交易中 / ○ 已暂停       │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─ 批量撤单 (第23-24项) ──────────────┐    │
│  │                                     │    │
│  │  合约代码: [IF2401] [部分撤单]       │    │
│  │                                     │    │
│  │  [全部撤单]                         │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─ 紧急停止 ─────────────────────────┐     │
│  │                                     │    │
│  │  [一键紧急停止]  ← 暂停+撤单+断开     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第20项: 暂停交易功能
- 第23项: 部分撤单功能
- 第24项: 全部撤单功能

### 3.8 日志查看页 (评估表第25项)

```
┌─ 日志查看 ──────────────────────────────────┐
│                                             │
│  类型: [全部▼] 级别: [全部▼] [刷新] [导出]   │
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │ 2026-01-09 10:30:15 [TRADE] 买入开仓... ││
│  │ 2026-01-09 10:30:16 [SYSTEM] 报单已提交 ││
│  │ 2026-01-09 10:30:17 [MONITOR] 阈值检查  ││
│  │ 2026-01-09 10:30:18 [TRADE] 成交回报... ││
│  │ ...                                     ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**功能说明:**
- 第25项: 完整日志记录
- 支持按类型/级别筛选
- 支持日志导出

---

## 四、API接口设计

### 4.1 接口列表

| 方法 | 路径 | 说明 | 评估项 |
|------|------|------|--------|
| POST | /api/connect | 连接服务器 | 第1项 |
| POST | /api/authenticate | 客户端认证 | 第1项 |
| POST | /api/login | 用户登录 | 第1项 |
| POST | /api/logout | 登出 | - |
| POST | /api/order/open | 开仓 | 第2项 |
| POST | /api/order/close | 平仓 | 第3项 |
| POST | /api/order/cancel | 撤单 | 第4项 |
| GET | /api/orders | 获取委托列表 | - |
| GET | /api/monitor/connection | 连接状态 | 第5项 |
| GET | /api/monitor/orders | 报单统计 | 第6-10项 |
| GET | /api/monitor/thresholds | 阈值状态 | 第11-13项 |
| PUT | /api/monitor/thresholds | 更新阈值 | 第11-13项 |
| POST | /api/validate/order | 验证订单 | 第14-19项 |
| POST | /api/emergency/pause | 暂停交易 | 第20项 |
| POST | /api/emergency/resume | 恢复交易 | 第20项 |
| POST | /api/emergency/cancel-by-instrument | 部分撤单 | 第23项 |
| POST | /api/emergency/cancel-all | 全部撤单 | 第24项 |
| POST | /api/emergency/stop | 紧急停止 | 第20项 |
| GET | /api/logs | 获取日志 | 第25项 |
| WS | /ws/realtime | 实时推送 | - |

### 4.2 接口详细定义

#### 连接服务器
```
POST /api/connect
Request:
{
    "broker_id": "9999",
    "trade_front": "tcp://180.168.146.187:10201"
}
Response:
{
    "success": true,
    "message": "连接成功"
}
```

#### 开仓
```
POST /api/order/open
Request:
{
    "instrument_id": "IF2401",
    "direction": "buy",  // buy | sell
    "price": 4000.0,
    "volume": 1
}
Response:
{
    "success": true,
    "order_ref": "000001",
    "message": "报单已提交"
}
```

#### 验证订单 (用于错误防范测试)
```
POST /api/validate/order
Request:
{
    "instrument_id": "INVALID",
    "direction": "buy",
    "price": 4000.123,
    "volume": -1
}
Response:
{
    "valid": false,
    "errors": [
        {"code": "INVALID_INSTRUMENT", "message": "合约代码不存在"},
        {"code": "INVALID_PRICE", "message": "价格不符合最小变动单位"},
        {"code": "INVALID_VOLUME", "message": "委托数量必须为正整数"}
    ]
}
```

---

## 五、HTML元素ID规范

为便于Playwright自动化测试定位元素，所有可交互元素需要设置标准化ID。

### 5.1 连接登录

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#input-broker-id` | input | 经纪商ID输入框 |
| `#input-trade-front` | input | 交易前置输入框 |
| `#input-investor-id` | input | 投资者账号输入框 |
| `#input-password` | input | 密码输入框 |
| `#btn-connect` | button | 连接按钮 |
| `#btn-authenticate` | button | 认证按钮 |
| `#btn-login` | button | 登录按钮 |
| `#status-connection` | span | 连接状态显示 |
| `#status-auth` | span | 认证状态显示 |
| `#status-login` | span | 登录状态显示 |

### 5.2 交易操作

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#input-instrument` | input | 合约代码输入框 |
| `#input-price` | input | 价格输入框 |
| `#input-volume` | input | 数量输入框 |
| `#btn-buy-open` | button | 买入开仓按钮 |
| `#btn-sell-open` | button | 卖出开仓按钮 |
| `#btn-buy-close` | button | 买入平仓按钮 |
| `#btn-sell-close` | button | 卖出平仓按钮 |
| `#btn-cancel-order` | button | 撤单按钮 |
| `#table-orders` | table | 委托表格 |
| `#order-row-{ref}` | tr | 委托行 |

### 5.3 监测面板

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#monitor-connection-status` | span | 连接状态 |
| `#monitor-heartbeat` | span | 心跳时间 |
| `#monitor-disconnect-count` | span | 断线次数 |
| `#monitor-open-count-{inst}` | span | 合约开仓次数 |
| `#monitor-close-count-{inst}` | span | 合约平仓次数 |
| `#monitor-cancel-count-{inst}` | span | 合约撤单次数 |
| `#monitor-total-orders` | span | 总报单数 |
| `#monitor-total-cancels` | span | 总撤单数 |

### 5.4 阈值设置

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#input-threshold-open` | input | 开仓阈值输入 |
| `#input-threshold-close` | input | 平仓阈值输入 |
| `#input-threshold-cancel` | input | 撤单阈值输入 |
| `#input-threshold-total-order` | input | 总报单阈值 |
| `#input-threshold-total-cancel` | input | 总撤单阈值 |
| `#btn-save-thresholds` | button | 保存阈值按钮 |
| `#table-alerts` | table | 预警历史表格 |

### 5.5 错误防范测试

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#btn-test-invalid-instrument` | button | 测试无效合约 |
| `#btn-test-invalid-price` | button | 测试无效价格 |
| `#btn-test-invalid-volume` | button | 测试无效数量 |
| `#btn-test-insufficient-margin` | button | 测试资金不足 |
| `#btn-test-insufficient-pos` | button | 测试持仓不足 |
| `#btn-test-non-trading-time` | button | 测试非交易时间 |
| `#error-message` | div | 错误提示显示区 |
| `#test-result-{n}` | span | 测试结果状态 |

### 5.6 应急处置

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#btn-pause-trading` | button | 暂停交易按钮 |
| `#btn-resume-trading` | button | 恢复交易按钮 |
| `#input-cancel-instrument` | input | 撤单合约输入 |
| `#btn-cancel-by-instrument` | button | 部分撤单按钮 |
| `#btn-cancel-all` | button | 全部撤单按钮 |
| `#btn-emergency-stop` | button | 紧急停止按钮 |
| `#status-trading` | span | 交易状态显示 |

### 5.7 日志

| ID | 元素类型 | 说明 |
|----|----------|------|
| `#select-log-type` | select | 日志类型选择 |
| `#select-log-level` | select | 日志级别选择 |
| `#btn-refresh-logs` | button | 刷新日志按钮 |
| `#btn-export-logs` | button | 导出日志按钮 |
| `#log-container` | div | 日志容器 |

---

## 六、Playwright自动化测试

### 6.1 测试框架配置

```python
# tests/conftest.py
import pytest
from playwright.async_api import async_playwright

@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    page = await browser.new_page()
    await page.goto("http://localhost:8000")
    yield page
    await page.close()
```

### 6.2 测试用例设计

#### 第1项：接口适应性测试

```python
class TestInterfaceCompatibility:
    """第1项：接口适应性测试"""

    async def test_01_connect_server(self, page):
        """测试连接服务器"""
        await page.fill("#input-broker-id", "9999")
        await page.fill("#input-trade-front", "tcp://180.168.146.187:10201")
        await page.click("#btn-connect")
        await expect(page.locator("#status-connection")).to_have_text("已连接")

    async def test_01_authenticate(self, page):
        """测试客户端认证"""
        await page.click("#btn-authenticate")
        await expect(page.locator("#status-auth")).to_have_text("已认证")

    async def test_01_login(self, page):
        """测试用户登录"""
        await page.fill("#input-investor-id", "test_user")
        await page.fill("#input-password", "test_pass")
        await page.click("#btn-login")
        await expect(page.locator("#status-login")).to_have_text("已登录")
```

#### 第2-4项：基础交易功能测试

```python
class TestBasicTrading:
    """第2-4项：基础交易功能测试"""

    async def test_02_open_position(self, page):
        """第2项：开仓指令"""
        await page.fill("#input-instrument", "IF2401")
        await page.fill("#input-price", "4000.0")
        await page.fill("#input-volume", "1")
        await page.click("#btn-buy-open")
        await expect(page.locator("#table-orders")).to_contain_text("IF2401")

    async def test_03_close_position(self, page):
        """第3项：平仓指令"""
        await page.click("#btn-sell-close")
        await expect(page.locator("#table-orders")).to_contain_text("平仓")

    async def test_04_cancel_order(self, page):
        """第4项：撤单指令"""
        await page.click("#btn-cancel-order")
        await expect(page.locator("#table-orders")).to_contain_text("已撤")
```

#### 第5-10项：异常监测测试

```python
class TestAnomalyMonitoring:
    """第5-10项：异常监测测试"""

    async def test_05_connection_monitoring(self, page):
        """第5项：连接状态监测"""
        await page.click("text=监测面板")
        await expect(page.locator("#monitor-connection-status")).to_be_visible()
        await expect(page.locator("#monitor-heartbeat")).to_be_visible()

    async def test_06_repeat_open_monitoring(self, page):
        """第6项：单合约重复开仓监测"""
        for _ in range(3):
            await page.click("#btn-buy-open")
            await page.wait_for_timeout(500)
        count = await page.locator("#monitor-open-count-IF2401").text_content()
        assert int(count) >= 3

    async def test_07_repeat_close_monitoring(self, page):
        """第7项：单合约重复平仓监测"""
        await expect(page.locator("#monitor-close-count-IF2401")).to_be_visible()

    async def test_08_repeat_cancel_monitoring(self, page):
        """第8项：单合约重复撤单监测"""
        await expect(page.locator("#monitor-cancel-count-IF2401")).to_be_visible()

    async def test_09_total_order_monitoring(self, page):
        """第9项：账号报单数量监测"""
        await expect(page.locator("#monitor-total-orders")).to_be_visible()

    async def test_10_total_cancel_monitoring(self, page):
        """第10项：账号撤单数量监测"""
        await expect(page.locator("#monitor-total-cancels")).to_be_visible()
```

#### 第11-13项：阈值管理测试

```python
class TestThresholdManagement:
    """第11-13项：阈值管理测试"""

    async def test_11_repeat_order_threshold(self, page):
        """第11项：重复报单阈值及预警"""
        await page.click("text=阈值设置")
        await page.fill("#input-threshold-open", "5")
        await page.click("#btn-save-thresholds")
        # 触发超过阈值
        for _ in range(6):
            await page.click("#btn-buy-open")
        await expect(page.locator("#table-alerts")).to_contain_text("开仓")

    async def test_12_total_order_threshold(self, page):
        """第12项：报单总笔数阈值及预警"""
        await page.fill("#input-threshold-total-order", "10")
        await page.click("#btn-save-thresholds")
        await expect(page.locator("#table-alerts")).to_be_visible()

    async def test_13_total_cancel_threshold(self, page):
        """第13项：撤单总笔数阈值及预警"""
        await page.fill("#input-threshold-total-cancel", "10")
        await page.click("#btn-save-thresholds")
```

#### 第14-19项：错误防范测试

```python
class TestErrorPrevention:
    """第14-19项：错误防范测试"""

    async def test_14_invalid_instrument(self, page):
        """第14项：合约代码错误检查"""
        await page.click("text=错误防范测试")
        await page.click("#btn-test-invalid-instrument")
        await expect(page.locator("#error-message")).to_contain_text("合约")

    async def test_15_invalid_price(self, page):
        """第15项：价格最小变动检查"""
        await page.click("#btn-test-invalid-price")
        await expect(page.locator("#error-message")).to_contain_text("价格")

    async def test_16_invalid_volume(self, page):
        """第16项：委托数量检查"""
        await page.click("#btn-test-invalid-volume")
        await expect(page.locator("#error-message")).to_contain_text("数量")

    async def test_17_insufficient_margin(self, page):
        """第17项：资金不足提示"""
        await page.click("#btn-test-insufficient-margin")
        await expect(page.locator("#error-message")).to_contain_text("资金")

    async def test_18_insufficient_position(self, page):
        """第18项：持仓不足提示"""
        await page.click("#btn-test-insufficient-pos")
        await expect(page.locator("#error-message")).to_contain_text("持仓")

    async def test_19_non_trading_time(self, page):
        """第19项：非交易时间提示"""
        await page.click("#btn-test-non-trading-time")
        await expect(page.locator("#error-message")).to_contain_text("交易时间")
```

#### 第20, 23-24项：应急处置测试

```python
class TestEmergencyHandling:
    """第20, 23-24项：应急处置测试"""

    async def test_20_pause_trading(self, page):
        """第20项：暂停交易功能"""
        await page.click("text=应急处置")
        await page.click("#btn-pause-trading")
        await expect(page.locator("#status-trading")).to_contain_text("已暂停")

        # 验证暂停后无法交易
        await page.click("#btn-buy-open")
        await expect(page.locator("#error-message")).to_contain_text("暂停")

        # 恢复交易
        await page.click("#btn-resume-trading")
        await expect(page.locator("#status-trading")).to_contain_text("交易中")

    async def test_23_cancel_by_instrument(self, page):
        """第23项：部分撤单功能"""
        await page.fill("#input-cancel-instrument", "IF2401")
        await page.click("#btn-cancel-by-instrument")
        # 验证该合约订单已撤

    async def test_24_cancel_all(self, page):
        """第24项：全部撤单功能"""
        await page.click("#btn-cancel-all")
        await expect(page.locator("#table-orders tbody")).to_be_empty()
```

#### 第25项：日志记录测试

```python
class TestLogging:
    """第25项：日志记录测试"""

    async def test_25_logging(self, page):
        """第25项：完整日志记录"""
        await page.click("text=日志查看")

        # 验证各类日志
        await page.select_option("#select-log-type", "TRADE")
        await expect(page.locator("#log-container")).to_contain_text("TRADE")

        await page.select_option("#select-log-type", "SYSTEM")
        await expect(page.locator("#log-container")).to_contain_text("SYSTEM")

        await page.select_option("#select-log-type", "MONITOR")
        await expect(page.locator("#log-container")).to_contain_text("MONITOR")

        # 测试日志导出
        async with page.expect_download() as download_info:
            await page.click("#btn-export-logs")
        download = await download_info.value
        assert download.suggested_filename.endswith(".log")
```

### 6.3 测试报告格式

```
评估表测试报告
=====================================
测试时间: 2026-01-09 15:30:00
测试环境: Windows 11 / Python 3.8 / Playwright 1.40

评估项目                              结果    用时
-------------------------------------+------+------
第1项 - 接口适应性
  ├─ 连接服务器                        ✓     1.2s
  ├─ 客户端认证                        ✓     0.8s
  └─ 用户登录                          ✓     0.9s
第2项 - 开仓指令                       ✓     0.5s
第3项 - 平仓指令                       ✓     0.5s
第4项 - 撤单指令                       ✓     0.4s
第5项 - 连接状态监测                   ✓     0.3s
第6项 - 单合约重复开仓监测             ✓     2.1s
第7项 - 单合约重复平仓监测             ✓     0.3s
第8项 - 单合约重复撤单监测             ✓     0.3s
第9项 - 账号报单数量监测               ✓     0.2s
第10项 - 账号撤单数量监测              ✓     0.2s
第11项 - 重复报单阈值及预警            ✓     3.5s
第12项 - 报单总笔数阈值及预警          ✓     0.4s
第13项 - 撤单总笔数阈值及预警          ✓     0.4s
第14项 - 合约代码错误检查              ✓     0.3s
第15项 - 价格最小变动检查              ✓     0.3s
第16项 - 委托数量检查                  ✓     0.3s
第17项 - 资金不足提示                  ✓     0.3s
第18项 - 持仓不足提示                  ✓     0.3s
第19项 - 非交易时间提示                ✓     0.3s
第20项 - 暂停交易功能                  ✓     1.5s
第23项 - 部分撤单功能                  ✓     0.8s
第24项 - 全部撤单功能                  ✓     0.6s
第25项 - 完整日志记录                  ✓     1.2s
=====================================
总计: 25/25 通过 (100%)
严重项: 21/21 通过
建议项: 4/4 通过
```

---

## 七、项目文件结构

```
ctp_trading_system/
├── ... (现有代码)
│
├── docs/
│   └── WEB_UI_DESIGN.md          # 本设计文档
│
├── web/                          # Web UI 模块
│   ├── __init__.py
│   ├── app.py                    # FastAPI 应用主入口
│   ├── api/                      # API 路由
│   │   ├── __init__.py
│   │   ├── connection.py         # 连接相关API
│   │   ├── trading.py            # 交易相关API
│   │   ├── monitor.py            # 监测相关API
│   │   ├── emergency.py          # 应急相关API
│   │   └── logs.py               # 日志相关API
│   ├── static/                   # 静态资源
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── main.js
│   └── templates/                # HTML模板
│       └── index.html            # 单页面应用
│
└── tests/                        # 测试目录
    ├── __init__.py
    ├── conftest.py               # Pytest fixtures
    ├── test_assessment.py        # 评估表自动化测试
    └── pytest.ini                # Pytest配置
```

---

## 八、依赖更新

需要在 `requirements.txt` 中添加:

```
# Web UI
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
jinja2>=3.1.2
websockets>=12.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
playwright>=1.40.0
```

---

## 九、实施计划

### 阶段一：Web后端 (API)
1. 创建FastAPI应用框架
2. 实现连接相关API
3. 实现交易相关API
4. 实现监测相关API
5. 实现应急相关API
6. 实现日志相关API
7. 实现WebSocket实时推送

### 阶段二：Web前端 (UI)
1. 创建HTML页面结构
2. 实现连接登录页
3. 实现交易操作页
4. 实现监测面板页
5. 实现阈值设置页
6. 实现错误防范测试页
7. 实现应急处置页
8. 实现日志查看页
9. 实现实时状态更新

### 阶段三：自动化测试
1. 配置Playwright测试环境
2. 实现第1项测试用例
3. 实现第2-4项测试用例
4. 实现第5-10项测试用例
5. 实现第11-13项测试用例
6. 实现第14-19项测试用例
7. 实现第20,23-24项测试用例
8. 实现第25项测试用例
9. 生成测试报告

---

## 十、审批记录

| 日期 | 审批人 | 意见 | 状态 |
|------|--------|------|------|
| 2026-01-09 | - | - | 待审核 |

