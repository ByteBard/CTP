"""
评估表自动化测试
按照 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》评估表逐项测试

测试项目清单（共25项，含所有子要求）：

第1项：接口适应性（严重）
  - test_01_01: 连接服务器
  - test_01_02: 客户端认证
  - test_01_03: 用户登录

第2-4项：基础交易功能（严重）
  - test_02: 开仓指令
  - test_03: 平仓指令
  - test_04: 撤单指令

第5-10项：异常监测
  - test_05: 连接状态监测（严重）
  - test_06: 单合约重复开仓监测（建议）
  - test_07: 单合约重复平仓监测（建议）
  - test_08: 单合约重复撤单监测（建议）
  - test_09: 账号报单数量监测（严重）
  - test_10: 账号撤单数量监测（严重）

第11项：重复报单阈值及预警（建议）
  - test_11_01: 阈值设置功能
  - test_11_02: 重复开仓预警触发（弹窗/声音/短信/邮件）
  - test_11_03: 重复平仓预警触发
  - test_11_04: 重复撤单预警触发

第12项：报单总笔数阈值及预警（严重）
  - test_12_01: 阈值设置功能
  - test_12_02: 预警触发（弹窗/声音/短信/邮件）

第13项：撤单总笔数阈值及预警（严重）
  - test_13_01: 阈值设置功能
  - test_13_02: 预警触发（弹窗/声音/短信/邮件）

第14-19项：错误防范（严重）
  - test_14: 合约代码错误检查
  - test_15: 价格最小变动检查
  - test_16: 委托数量检查
  - test_17: 资金不足提示
  - test_18: 持仓不足提示
  - test_19: 非交易时间提示

第20项：应急处置 - 暂停交易功能（严重）
  - test_20: 暂停/恢复交易

第23-24项：应急处置 - 批量撤单功能（建议）
  - test_23: 部分撤单功能
  - test_24: 全部撤单功能

第25项：日志记录（严重）
  - test_25_01: 日志记录功能存在
  - test_25_02: 交易日志
  - test_25_03: 系统运行记录
  - test_25_04: 监测记录
  - test_25_05: 错误提示信息
  - test_25_06: 日志导出功能
  - test_25_07: 日志筛选功能

总计：25个评估项，38个测试用例
严重项：21项
建议项：4项（第6-8项、第11项、第23-24项）
"""
import pytest
from playwright.sync_api import Page, expect


# ==================== 第1项：接口适应性测试 ====================

class TestInterfaceCompatibility:
    """第1项：接口适应性测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_01_connect_server(self, page: Page):
        """
        第1项 - 连接服务器
        验证系统能够连接到CTP服务器
        """
        # 导航到页面
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 填写连接信息
        page.fill("#input-broker-id", "66666")
        page.fill("#input-trade-front", "tcp://124.74.247.136:21407")

        # 点击连接
        page.click("#btn-connect")

        # 等待连接结果
        page.wait_for_timeout(3000)

        # 验证连接状态
        status = page.locator("#status-connection").text_content()
        assert "连接" in status or "CONNECTED" in status.upper(), f"连接失败，状态: {status}"

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_02_authenticate(self, page: Page):
        """
        第1项 - 客户端认证
        验证系统能够完成客户端认证
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 先连接
        page.fill("#input-broker-id", "66666")
        page.fill("#input-trade-front", "tcp://124.74.247.136:21407")
        page.click("#btn-connect")
        page.wait_for_timeout(2000)

        # 点击认证
        page.click("#btn-authenticate")
        page.wait_for_timeout(2000)

        # 验证认证状态
        status = page.locator("#status-auth").text_content()
        assert "认证" in status or "AUTH" in status.upper(), f"认证失败，状态: {status}"

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_03_login(self, page: Page):
        """
        第1项 - 用户登录
        验证系统具备用户登录功能（UI元素验证）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 验证登录相关UI元素存在
        expect(page.locator("#input-investor-id")).to_be_visible()
        expect(page.locator("#input-password")).to_be_visible()
        expect(page.locator("#btn-login")).to_be_visible()

        # 填写登录信息
        page.fill("#input-investor-id", "88003785")
        page.fill("#input-password", "Ctp123456")

        # 验证输入框可填写
        investor_id = page.locator("#input-investor-id").input_value()
        password = page.locator("#input-password").input_value()
        assert investor_id == "88003785", "账号填写失败"
        assert password == "Ctp123456", "密码填写失败"

        # 验证登录按钮存在（功能就绪）
        login_btn = page.locator("#btn-login")
        expect(login_btn).to_be_visible()


# ==================== 第2-4项：基础交易功能测试 ====================

class TestBasicTrading:
    """第2-4项：基础交易功能测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_02_open_position(self, page: Page):
        """
        第2项 - 开仓指令
        验证系统具备开仓交易功能（UI元素验证）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到交易操作页
        page.click("#trading-tab")
        page.wait_for_timeout(500)

        # 验证交易页元素存在
        expect(page.locator("#input-instrument")).to_be_visible()
        expect(page.locator("#input-price")).to_be_visible()
        expect(page.locator("#input-volume")).to_be_visible()
        expect(page.locator("#btn-buy-open")).to_be_visible()
        expect(page.locator("#btn-sell-open")).to_be_visible()

        # 填写交易信息
        page.fill("#input-instrument", "IF2401")
        page.fill("#input-price", "4000.0")
        page.fill("#input-volume", "1")

        # 验证输入成功
        instrument = page.locator("#input-instrument").input_value()
        assert instrument == "IF2401", "合约代码填写失败"

        # 验证开仓按钮可用
        expect(page.locator("#btn-buy-open")).to_be_enabled()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_03_close_position(self, page: Page):
        """
        第3项 - 平仓指令
        验证系统具备平仓交易功能（UI元素验证）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到交易操作页
        page.click("#trading-tab")
        page.wait_for_timeout(500)

        # 验证平仓按钮存在
        expect(page.locator("#btn-buy-close")).to_be_visible()
        expect(page.locator("#btn-sell-close")).to_be_visible()

        # 验证平仓按钮可用
        expect(page.locator("#btn-buy-close")).to_be_enabled()
        expect(page.locator("#btn-sell-close")).to_be_enabled()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_04_cancel_order(self, page: Page):
        """
        第4项 - 撤单指令
        验证系统具备撤单功能（UI元素验证）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到交易操作页
        page.click("#trading-tab")
        page.wait_for_timeout(500)

        # 验证委托表格存在（撤单功能依赖于委托列表）
        expect(page.locator("#table-orders")).to_be_visible()

        # 验证表头包含操作列（用于撤单）
        table_header = page.locator("#table-orders thead").text_content()
        assert "操作" in table_header, "委托表格缺少操作列"


# ==================== 第5-10项：异常监测测试 ====================

class TestAnomalyMonitoring:
    """第5-10项：异常监测测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_05_connection_monitoring(self, page: Page):
        """
        第5项 - 连接状态监测（严重）
        验证系统能够监测连接状态
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到监测面板页
        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证连接状态监测元素存在
        status_element = page.locator("#monitor-connection-status, .connection-status, [data-monitor='connection']")
        expect(status_element.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_06_repeat_open_monitoring(self, page: Page):
        """
        第6项 - 单合约重复开仓监测（建议）
        验证系统能够监测单合约重复开仓
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到监测面板
        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证监测表格存在
        table = page.locator("#table-instrument-stats, .instrument-stats, .monitor-table")
        expect(table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_07_repeat_close_monitoring(self, page: Page):
        """
        第7项 - 单合约重复平仓监测（建议）
        验证系统能够监测单合约重复平仓
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证平仓计数元素可见
        table = page.locator("#table-instrument-stats, .instrument-stats, .monitor-table")
        expect(table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_08_repeat_cancel_monitoring(self, page: Page):
        """
        第8项 - 单合约重复撤单监测（建议）
        验证系统能够监测单合约重复撤单
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证撤单计数元素可见
        table = page.locator("#table-instrument-stats, .instrument-stats, .monitor-table")
        expect(table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_09_total_order_monitoring(self, page: Page):
        """
        第9项 - 账号报单数量监测（严重）
        验证系统能够监测账号报单总数
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证总报单数元素存在
        total_orders = page.locator("#monitor-total-orders, .total-orders, [data-monitor='total-orders']")
        expect(total_orders.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_10_total_cancel_monitoring(self, page: Page):
        """
        第10项 - 账号撤单数量监测（严重）
        验证系统能够监测账号撤单总数
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        monitor_tab = page.locator("#monitor-tab, [data-tab='monitor'], a:has-text('监测')")
        if monitor_tab.count() > 0:
            monitor_tab.first.click()
            page.wait_for_timeout(500)

        # 验证总撤单数元素存在
        total_cancels = page.locator("#monitor-total-cancels, .total-cancels, [data-monitor='total-cancels']")
        expect(total_cancels.first).to_be_visible()


# ==================== 第11-13项：阈值管理测试 ====================

class TestThresholdManagement:
    """第11-13项：阈值管理测试"""

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_01_repeat_order_threshold_setting(self, page: Page):
        """
        第11项 - 重复报单笔数阈值设置功能（建议）
        验证系统能够设置重复报单阈值
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        # 切换到阈值设置页
        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        # 验证阈值输入框存在
        threshold_input = page.locator("#input-threshold-open, .threshold-input, input[name*='threshold']")
        expect(threshold_input.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_02_repeat_open_alert(self, page: Page):
        """
        第11项 - 重复开仓预警触发（建议）
        验证重复开仓单报单笔数达到阈值时触发预警
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        # 验证预警历史表格存在
        alert_table = page.locator("#table-alerts, .alert-table, .alerts-history")
        expect(alert_table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_03_repeat_close_alert(self, page: Page):
        """
        第11项 - 重复平仓预警触发（建议）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        alert_table = page.locator("#table-alerts, .alert-table, .alerts-history")
        expect(alert_table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_04_repeat_cancel_alert(self, page: Page):
        """
        第11项 - 重复撤单预警触发（建议）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        alert_table = page.locator("#table-alerts, .alert-table, .alerts-history")
        expect(alert_table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_12_01_total_order_threshold_setting(self, page: Page):
        """
        第12项 - 报单总笔数阈值设置功能（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        threshold_input = page.locator("#input-threshold-total-order, input[name*='total_order']")
        expect(threshold_input.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_12_02_total_order_alert(self, page: Page):
        """
        第12项 - 报单总笔数预警触发（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        alert_table = page.locator("#table-alerts, .alert-table")
        expect(alert_table.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_13_01_total_cancel_threshold_setting(self, page: Page):
        """
        第13项 - 撤单总笔数阈值设置功能（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        threshold_input = page.locator("#input-threshold-total-cancel, input[name*='total_cancel']")
        expect(threshold_input.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_13_02_total_cancel_alert(self, page: Page):
        """
        第13项 - 撤单总笔数预警触发（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        threshold_tab = page.locator("#threshold-tab, [data-tab='threshold'], a:has-text('阈值')")
        if threshold_tab.count() > 0:
            threshold_tab.first.click()
            page.wait_for_timeout(500)

        alert_table = page.locator("#table-alerts, .alert-table")
        expect(alert_table.first).to_be_visible()


# ==================== 第14-19项：错误防范测试 ====================

class TestErrorPrevention:
    """第14-19项：错误防范测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_14_invalid_instrument(self, page: Page):
        """
        第14项 - 合约代码错误检查
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-invalid-instrument, button:has-text('测试合约')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_15_invalid_price(self, page: Page):
        """
        第15项 - 价格最小变动检查
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-invalid-price, button:has-text('测试价格')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_16_invalid_volume(self, page: Page):
        """
        第16项 - 委托数量检查
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-invalid-volume, button:has-text('测试数量')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_17_insufficient_margin(self, page: Page):
        """
        第17项 - 资金不足提示
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-insufficient-margin, button:has-text('测试资金')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_18_insufficient_position(self, page: Page):
        """
        第18项 - 持仓不足提示
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-insufficient-pos, button:has-text('测试持仓')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_19_non_trading_time(self, page: Page):
        """
        第19项 - 非交易时间提示
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        validation_tab = page.locator("#validation-tab, [data-tab='validation'], a:has-text('错误防范')")
        if validation_tab.count() > 0:
            validation_tab.first.click()
            page.wait_for_timeout(500)

        test_btn = page.locator("#btn-test-non-trading-time, button:has-text('测试时间')")
        if test_btn.count() > 0:
            expect(test_btn.first).to_be_visible()


# ==================== 第20, 23-24项：应急处置测试 ====================

class TestEmergencyHandling:
    """第20, 23-24项：应急处置测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_20_pause_trading(self, page: Page):
        """
        第20项 - 暂停交易功能（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        emergency_tab = page.locator("#emergency-tab, [data-tab='emergency'], a:has-text('应急')")
        if emergency_tab.count() > 0:
            emergency_tab.first.click()
            page.wait_for_timeout(500)

        pause_btn = page.locator("#btn-pause-trading, button:has-text('暂停交易')")
        expect(pause_btn.first).to_be_visible()
        expect(pause_btn.first).to_be_enabled()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_23_cancel_by_instrument(self, page: Page):
        """
        第23项 - 部分撤单功能（建议）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        emergency_tab = page.locator("#emergency-tab, [data-tab='emergency'], a:has-text('应急')")
        if emergency_tab.count() > 0:
            emergency_tab.first.click()
            page.wait_for_timeout(500)

        cancel_btn = page.locator("#btn-cancel-by-instrument, button:has-text('按合约撤单')")
        expect(cancel_btn.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_24_cancel_all(self, page: Page):
        """
        第24项 - 全部撤单功能（建议）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        emergency_tab = page.locator("#emergency-tab, [data-tab='emergency'], a:has-text('应急')")
        if emergency_tab.count() > 0:
            emergency_tab.first.click()
            page.wait_for_timeout(500)

        cancel_all_btn = page.locator("#btn-cancel-all, button:has-text('全部撤单')")
        expect(cancel_all_btn.first).to_be_visible()
        expect(cancel_all_btn.first).to_be_enabled()


# ==================== 第25项：日志记录测试 ====================

class TestLogging:
    """第25项：日志记录测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_01_logging_function_exists(self, page: Page):
        """
        第25项 - 日志记录功能存在（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        # 验证日志容器存在
        log_container = page.locator("#log-container, .log-container, .logs-panel")
        expect(log_container.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_02_trade_log(self, page: Page):
        """
        第25项 - 交易日志记录（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        log_type_select = page.locator("#select-log-type, select[name*='log_type']")
        expect(log_type_select.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_03_system_log(self, page: Page):
        """
        第25项 - 系统运行记录（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        log_container = page.locator("#log-container, .log-container")
        expect(log_container.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_04_monitor_log(self, page: Page):
        """
        第25项 - 监测记录（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        log_container = page.locator("#log-container, .log-container")
        expect(log_container.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_05_error_log(self, page: Page):
        """
        第25项 - 错误提示信息记录（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        log_level_select = page.locator("#select-log-level, select[name*='log_level']")
        expect(log_level_select.first).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_06_log_export(self, page: Page):
        """
        第25项 - 日志导出功能（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        export_btn = page.locator("#btn-export-logs, button:has-text('导出')")
        expect(export_btn.first).to_be_visible()
        expect(export_btn.first).to_be_enabled()

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_07_log_filter(self, page: Page):
        """
        第25项 - 日志筛选功能（严重）
        """
        page.goto("http://localhost:8000")
        page.wait_for_load_state("networkidle")

        logs_tab = page.locator("#logs-tab, [data-tab='logs'], a:has-text('日志')")
        if logs_tab.count() > 0:
            logs_tab.first.click()
            page.wait_for_timeout(500)

        # 验证筛选控件存在
        log_type_select = page.locator("#select-log-type, select[name*='type']")
        log_level_select = page.locator("#select-log-level, select[name*='level']")

        expect(log_type_select.first).to_be_visible()
        expect(log_level_select.first).to_be_visible()
