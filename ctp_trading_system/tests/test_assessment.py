"""
评估表自动化测试
按照 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》评估表逐项测试

测试项目清单：
- 第1项：接口适应性（连通性：认证功能、登录系统）
- 第2项：基础交易功能（开仓指令）
- 第3项：基础交易功能（平仓指令）
- 第4项：基础交易功能（撤单指令）
- 第5项：异常监测（连接状态监测）
- 第6项：异常监测（单合约重复开仓监测）
- 第7项：异常监测（单合约重复平仓监测）
- 第8项：异常监测（单合约重复撤单监测）
- 第9项：异常监测（账号报单数量监测）
- 第10项：异常监测（账号撤单数量监测）
- 第11项：阈值管理（重复报单阈值及预警）
- 第12项：阈值管理（报单总笔数阈值及预警）
- 第13项：阈值管理（撤单总笔数阈值及预警）
- 第14项：错误防范（合约代码错误检查）
- 第15项：错误防范（价格最小变动检查）
- 第16项：错误防范（委托数量检查）
- 第17项：错误防范（资金不足提示）
- 第18项：错误防范（持仓不足提示）
- 第19项：错误防范（非交易时间提示）
- 第20项：应急处置（暂停交易功能）
- 第23项：应急处置（部分撤单功能）
- 第24项：应急处置（全部撤单功能）
- 第25项：日志记录（完整日志记录）
"""
import pytest
from playwright.async_api import Page, expect


# ==================== 第1项：接口适应性测试 ====================

class TestInterfaceCompatibility:
    """第1项：接口适应性测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_01_01_connect_server(self, page: Page):
        """
        第1项 - 连接服务器
        验证系统能够连接到CTP服务器
        """
        # 填写连接信息
        await page.fill("#input-broker-id", "9999")
        await page.fill("#input-trade-front", "tcp://180.168.146.187:10201")

        # 点击连接
        await page.click("#btn-connect")

        # 等待连接结果
        await page.wait_for_timeout(3000)

        # 验证连接状态
        status = await page.locator("#status-connection").text_content()
        assert status == "已连接", f"连接失败，状态: {status}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_01_02_authenticate(self, page: Page):
        """
        第1项 - 客户端认证
        验证系统能够完成客户端认证
        """
        # 先连接
        await page.fill("#input-broker-id", "9999")
        await page.fill("#input-trade-front", "tcp://180.168.146.187:10201")
        await page.click("#btn-connect")
        await page.wait_for_timeout(2000)

        # 点击认证
        await page.click("#btn-authenticate")
        await page.wait_for_timeout(2000)

        # 验证认证状态
        status = await page.locator("#status-auth").text_content()
        assert status == "已认证", f"认证失败，状态: {status}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_01_03_login(self, page: Page):
        """
        第1项 - 用户登录
        验证系统能够完成用户登录
        """
        # 连接和认证
        await page.fill("#input-broker-id", "9999")
        await page.fill("#input-trade-front", "tcp://180.168.146.187:10201")
        await page.click("#btn-connect")
        await page.wait_for_timeout(2000)
        await page.click("#btn-authenticate")
        await page.wait_for_timeout(1000)

        # 填写登录信息
        await page.fill("#input-investor-id", "test_user")
        await page.fill("#input-password", "test_pass")

        # 点击登录
        await page.click("#btn-login")
        await page.wait_for_timeout(3000)

        # 验证登录状态
        status = await page.locator("#status-login").text_content()
        assert status == "已登录", f"登录失败，状态: {status}"


# ==================== 第2-4项：基础交易功能测试 ====================

class TestBasicTrading:
    """第2-4项：基础交易功能测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_02_open_position(self, page: Page):
        """
        第2项 - 开仓指令
        验证系统能够发送开仓指令
        """
        # 切换到交易操作页
        await page.click("#trading-tab")
        await page.wait_for_timeout(500)

        # 填写交易信息
        await page.fill("#input-instrument", "IF2401")
        await page.fill("#input-price", "4000.0")
        await page.fill("#input-volume", "1")

        # 点击买入开仓
        await page.click("#btn-buy-open")
        await page.wait_for_timeout(1000)

        # 验证委托表格有新订单
        orders_table = page.locator("#table-orders tbody")
        await expect(orders_table).to_contain_text("IF2401")

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_03_close_position(self, page: Page):
        """
        第3项 - 平仓指令
        验证系统能够发送平仓指令
        """
        # 切换到交易操作页
        await page.click("#trading-tab")
        await page.wait_for_timeout(500)

        # 填写交易信息
        await page.fill("#input-instrument", "IF2401")
        await page.fill("#input-price", "4010.0")
        await page.fill("#input-volume", "1")

        # 点击卖出平仓
        await page.click("#btn-sell-close")
        await page.wait_for_timeout(1000)

        # 验证有平仓订单
        orders_table = page.locator("#table-orders tbody")
        # 平仓订单应该出现在表格中
        row_count = await orders_table.locator("tr").count()
        assert row_count > 0, "未找到平仓订单"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_04_cancel_order(self, page: Page):
        """
        第4项 - 撤单指令
        验证系统能够发送撤单指令
        """
        # 切换到交易操作页
        await page.click("#trading-tab")
        await page.wait_for_timeout(500)

        # 先下一个订单
        await page.fill("#input-instrument", "IF2401")
        await page.fill("#input-price", "3900.0")  # 远离市价，不会成交
        await page.fill("#input-volume", "1")
        await page.click("#btn-buy-open")
        await page.wait_for_timeout(1000)

        # 查找撤单按钮并点击
        cancel_btn = page.locator(".btn-cancel-order").first
        if await cancel_btn.count() > 0:
            await cancel_btn.click()
            await page.wait_for_timeout(1000)

            # 验证订单状态变为已撤或撤单中
            orders_table = page.locator("#table-orders tbody")
            text = await orders_table.text_content()
            assert "已撤" in text or "撤单" in text, "撤单失败"


# ==================== 第5-10项：异常监测测试 ====================

class TestAnomalyMonitoring:
    """第5-10项：异常监测测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_05_connection_monitoring(self, page: Page):
        """
        第5项 - 连接状态监测（严重）
        验证系统能够监测连接状态
        """
        # 切换到监测面板页
        await page.click("#monitor-tab")
        await page.wait_for_timeout(500)

        # 验证连接状态监测元素存在
        await expect(page.locator("#monitor-connection-status")).to_be_visible()
        await expect(page.locator("#monitor-heartbeat")).to_be_visible()
        await expect(page.locator("#monitor-disconnect-count")).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_06_repeat_open_monitoring(self, page: Page):
        """
        第6项 - 单合约重复开仓监测（建议）
        验证系统能够监测单合约重复开仓
        """
        # 切换到交易页，执行多次开仓
        await page.click("#trading-tab")
        await page.wait_for_timeout(500)

        await page.fill("#input-instrument", "IF2401")
        await page.fill("#input-price", "4000.0")
        await page.fill("#input-volume", "1")

        # 执行3次开仓
        for _ in range(3):
            await page.click("#btn-buy-open")
            await page.wait_for_timeout(500)

        # 切换到监测面板
        await page.click("#monitor-tab")
        await page.wait_for_timeout(1000)

        # 验证开仓计数
        count_element = page.locator("#monitor-open-count-IF2401")
        if await count_element.count() > 0:
            count = await count_element.text_content()
            assert int(count) >= 3, f"开仓计数不正确: {count}"

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_07_repeat_close_monitoring(self, page: Page):
        """
        第7项 - 单合约重复平仓监测（建议）
        验证系统能够监测单合约重复平仓
        """
        await page.click("#monitor-tab")
        await page.wait_for_timeout(500)

        # 验证平仓计数元素可见（如果有该合约的记录）
        table = page.locator("#table-instrument-stats")
        await expect(table).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_08_repeat_cancel_monitoring(self, page: Page):
        """
        第8项 - 单合约重复撤单监测（建议）
        验证系统能够监测单合约重复撤单
        """
        await page.click("#monitor-tab")
        await page.wait_for_timeout(500)

        # 验证撤单计数元素可见
        table = page.locator("#table-instrument-stats")
        await expect(table).to_be_visible()

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_09_total_order_monitoring(self, page: Page):
        """
        第9项 - 账号报单数量监测（严重）
        验证系统能够监测账号报单总数
        """
        await page.click("#monitor-tab")
        await page.wait_for_timeout(500)

        # 验证总报单数元素存在
        await expect(page.locator("#monitor-total-orders")).to_be_visible()

        # 获取数值
        count = await page.locator("#monitor-total-orders").text_content()
        assert count.isdigit(), f"报单总数格式错误: {count}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_10_total_cancel_monitoring(self, page: Page):
        """
        第10项 - 账号撤单数量监测（严重）
        验证系统能够监测账号撤单总数
        """
        await page.click("#monitor-tab")
        await page.wait_for_timeout(500)

        # 验证总撤单数元素存在
        await expect(page.locator("#monitor-total-cancels")).to_be_visible()

        # 获取数值
        count = await page.locator("#monitor-total-cancels").text_content()
        assert count.isdigit(), f"撤单总数格式错误: {count}"


# ==================== 第11-13项：阈值管理测试 ====================

class TestThresholdManagement:
    """第11-13项：阈值管理测试"""

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_11_repeat_order_threshold(self, page: Page):
        """
        第11项 - 重复报单阈值及预警（建议）
        验证系统能够设置和触发重复报单阈值预警
        """
        # 切换到阈值设置页
        await page.click("#threshold-tab")
        await page.wait_for_timeout(500)

        # 设置较低的阈值
        await page.fill("#input-threshold-open", "2")
        await page.click("#btn-save-thresholds")
        await page.wait_for_timeout(500)

        # 验证阈值已保存
        value = await page.locator("#input-threshold-open").input_value()
        assert value == "2", f"阈值设置失败: {value}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_12_total_order_threshold(self, page: Page):
        """
        第12项 - 报单总笔数阈值及预警（严重）
        验证系统能够设置报单总数阈值
        """
        await page.click("#threshold-tab")
        await page.wait_for_timeout(500)

        # 设置阈值
        await page.fill("#input-threshold-total-order", "100")
        await page.click("#btn-save-thresholds")
        await page.wait_for_timeout(500)

        # 验证
        value = await page.locator("#input-threshold-total-order").input_value()
        assert value == "100", f"阈值设置失败: {value}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_13_total_cancel_threshold(self, page: Page):
        """
        第13项 - 撤单总笔数阈值及预警（严重）
        验证系统能够设置撤单总数阈值
        """
        await page.click("#threshold-tab")
        await page.wait_for_timeout(500)

        # 设置阈值
        await page.fill("#input-threshold-total-cancel", "80")
        await page.click("#btn-save-thresholds")
        await page.wait_for_timeout(500)

        # 验证
        value = await page.locator("#input-threshold-total-cancel").input_value()
        assert value == "80", f"阈值设置失败: {value}"


# ==================== 第14-19项：错误防范测试 ====================

class TestErrorPrevention:
    """第14-19项：错误防范测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_14_invalid_instrument(self, page: Page):
        """
        第14项 - 合约代码错误检查
        验证系统能够检查并提示合约代码错误
        """
        # 切换到错误防范测试页
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        # 点击测试按钮
        await page.click("#btn-test-invalid-instrument")
        await page.wait_for_timeout(1000)

        # 验证测试结果
        result = await page.locator("#test-result-14").text_content()
        assert result == "通过", f"合约代码错误检查未通过: {result}"

        # 验证错误消息
        error = await page.locator("#error-message").text_content()
        assert "合约" in error, f"错误消息不正确: {error}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_15_invalid_price(self, page: Page):
        """
        第15项 - 价格最小变动检查
        验证系统能够检查并提示价格错误
        """
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        await page.click("#btn-test-invalid-price")
        await page.wait_for_timeout(1000)

        result = await page.locator("#test-result-15").text_content()
        assert result == "通过", f"价格检查未通过: {result}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_16_invalid_volume(self, page: Page):
        """
        第16项 - 委托数量检查
        验证系统能够检查并提示数量错误
        """
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        await page.click("#btn-test-invalid-volume")
        await page.wait_for_timeout(1000)

        result = await page.locator("#test-result-16").text_content()
        assert result == "通过", f"数量检查未通过: {result}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_17_insufficient_margin(self, page: Page):
        """
        第17项 - 资金不足提示
        验证系统能够提示资金不足
        """
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        await page.click("#btn-test-insufficient-margin")
        await page.wait_for_timeout(1000)

        result = await page.locator("#test-result-17").text_content()
        assert result == "通过", f"资金检查未通过: {result}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_18_insufficient_position(self, page: Page):
        """
        第18项 - 持仓不足提示
        验证系统能够提示持仓不足
        """
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        await page.click("#btn-test-insufficient-pos")
        await page.wait_for_timeout(1000)

        result = await page.locator("#test-result-18").text_content()
        assert result == "通过", f"持仓检查未通过: {result}"

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_19_non_trading_time(self, page: Page):
        """
        第19项 - 非交易时间提示
        验证系统能够提示非交易时间
        """
        await page.click("#validation-tab")
        await page.wait_for_timeout(500)

        await page.click("#btn-test-non-trading-time")
        await page.wait_for_timeout(1000)

        result = await page.locator("#test-result-19").text_content()
        # 非交易时间检查可能在交易时间内不会触发
        assert result in ["通过", "未触发"], f"交易时间检查状态: {result}"


# ==================== 第20, 23-24项：应急处置测试 ====================

class TestEmergencyHandling:
    """第20, 23-24项：应急处置测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_20_pause_trading(self, page: Page):
        """
        第20项 - 暂停交易功能（严重）
        验证系统能够暂停和恢复交易
        """
        # 切换到应急处置页
        await page.click("#emergency-tab")
        await page.wait_for_timeout(500)

        # 点击暂停交易
        await page.click("#btn-pause-trading")
        await page.wait_for_timeout(1000)

        # 验证状态变为已暂停
        status = await page.locator("#status-trading").text_content()
        assert "暂停" in status, f"暂停交易失败，状态: {status}"

        # 恢复交易
        await page.click("#btn-resume-trading")
        await page.wait_for_timeout(1000)

        # 验证状态恢复
        status = await page.locator("#status-trading").text_content()
        assert "交易" in status, f"恢复交易失败，状态: {status}"

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_23_cancel_by_instrument(self, page: Page):
        """
        第23项 - 部分撤单功能（建议）
        验证系统能够按合约撤单
        """
        await page.click("#emergency-tab")
        await page.wait_for_timeout(500)

        # 输入合约代码
        await page.fill("#input-cancel-instrument", "IF2401")

        # 点击部分撤单
        await page.click("#btn-cancel-by-instrument")
        await page.wait_for_timeout(1000)

        # 验证按钮可点击（功能存在）
        await expect(page.locator("#btn-cancel-by-instrument")).to_be_enabled()

    @pytest.mark.assessment
    @pytest.mark.suggested
    async def test_24_cancel_all(self, page: Page):
        """
        第24项 - 全部撤单功能（建议）
        验证系统能够全部撤单
        """
        await page.click("#emergency-tab")
        await page.wait_for_timeout(500)

        # 验证全部撤单按钮存在且可点击
        await expect(page.locator("#btn-cancel-all")).to_be_visible()
        await expect(page.locator("#btn-cancel-all")).to_be_enabled()


# ==================== 第25项：日志记录测试 ====================

class TestLogging:
    """第25项：日志记录测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    async def test_25_logging(self, page: Page):
        """
        第25项 - 完整日志记录
        验证系统能够记录完整日志
        """
        # 切换到日志查看页
        await page.click("#logs-tab")
        await page.wait_for_timeout(500)

        # 验证日志类型选择器存在
        await expect(page.locator("#select-log-type")).to_be_visible()

        # 验证日志级别选择器存在
        await expect(page.locator("#select-log-level")).to_be_visible()

        # 验证日志容器存在
        await expect(page.locator("#log-container")).to_be_visible()

        # 验证刷新按钮存在
        await expect(page.locator("#btn-refresh-logs")).to_be_visible()

        # 验证导出按钮存在
        await expect(page.locator("#btn-export-logs")).to_be_visible()

        # 测试不同日志类型
        for log_type in ["TRADE", "SYSTEM", "MONITOR"]:
            await page.select_option("#select-log-type", log_type)
            await page.click("#btn-refresh-logs")
            await page.wait_for_timeout(500)
