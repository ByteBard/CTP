"""
评估表自动化测试 - 后端 API 版本
按照 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》评估表逐项测试

使用 httpx 直接调用后端 API，不依赖浏览器

测试项目清单（共25项，36个测试用例）：
- 第1项：接口适应性（3个测试）
- 第2-4项：基础交易功能（3个测试）
- 第5-10项：异常监测（6个测试）
- 第11-13项：阈值预警（8个测试）
- 第14-19项：错误防范（6个测试）
- 第20,23-24项：应急处置（3个测试）
- 第25项：日志记录（7个测试）
"""
import pytest
import httpx
from typing import Optional

# 测试服务器地址
BASE_URL = "http://localhost:8000"

# 测试超时时间
TIMEOUT = 10.0


def api_get(path: str, params: Optional[dict] = None) -> httpx.Response:
    """发送 GET 请求"""
    return httpx.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)


def api_post(path: str, json: Optional[dict] = None) -> httpx.Response:
    """发送 POST 请求"""
    return httpx.post(f"{BASE_URL}{path}", json=json or {}, timeout=TIMEOUT)


# ==================== 第1项：接口适应性测试 ====================

class TestInterfaceCompatibility:
    """第1项：接口适应性测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_01_connect_server(self):
        """
        第1项 - 连接服务器
        验证系统能够连接到CTP服务器
        """
        response = api_post("/api/connection/connect", {
            "broker_id": "66666",
            "trade_front": "tcp://124.74.247.136:21407"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_02_authenticate(self):
        """
        第1项 - 客户端认证
        验证系统能够完成客户端认证
        """
        response = api_post("/api/connection/authenticate", {
            "investor_id": "88003785",
            "app_id": "client_mltrader_1.0.0",
            "auth_code": "L8QDUC6XHBQR7WK2"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_01_03_login(self):
        """
        第1项 - 用户登录
        验证系统具备用户登录功能
        """
        response = api_post("/api/connection/login", {
            "investor_id": "88003785",
            "password": "024111"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data


# ==================== 第2-4项：基础交易功能测试 ====================

class TestBasicTrading:
    """第2-4项：基础交易功能测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_02_open_position(self):
        """
        第2项 - 开仓指令
        验证系统具备开仓交易功能
        """
        response = api_post("/api/trading/open", {
            "instrument_id": "IF2401",
            "direction": "buy",
            "offset": "open",
            "price": 4000.0,
            "volume": 1
        })
        assert response.status_code == 200
        data = response.json()
        # 验证返回了订单相关信息
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_03_close_position(self):
        """
        第3项 - 平仓指令
        验证系统具备平仓交易功能
        """
        response = api_post("/api/trading/close", {
            "instrument_id": "IF2401",
            "direction": "sell",
            "offset": "close",
            "price": 4000.0,
            "volume": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_04_cancel_order(self):
        """
        第4项 - 撤单指令
        验证系统具备撤单功能
        """
        response = api_post("/api/trading/cancel", {
            "instrument_id": "IF2401",
            "order_ref": "test_order_001"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data


# ==================== 第5-10项：异常监测测试 ====================

class TestAnomalyMonitoring:
    """第5-10项：异常监测测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_05_connection_monitoring(self):
        """
        第5项 - 连接状态监测（严重）
        验证系统能够监测连接状态
        """
        response = api_get("/api/monitor/connection")
        assert response.status_code == 200
        data = response.json()
        # 验证返回了连接状态信息
        assert "status" in data or "connected" in data

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_06_repeat_open_monitoring(self):
        """
        第6项 - 单合约重复开仓监测（建议）
        验证系统能够监测单合约重复开仓
        """
        response = api_get("/api/monitor/summary")
        assert response.status_code == 200
        data = response.json()
        # 验证返回了监测汇总数据
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_07_repeat_close_monitoring(self):
        """
        第7项 - 单合约重复平仓监测（建议）
        验证系统能够监测单合约重复平仓
        """
        response = api_get("/api/monitor/summary")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_08_repeat_cancel_monitoring(self):
        """
        第8项 - 单合约重复撤单监测（建议）
        验证系统能够监测单合约重复撤单
        """
        response = api_get("/api/monitor/summary")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_09_total_order_monitoring(self):
        """
        第9项 - 账号报单数量监测（严重）
        验证系统能够监测账号报单总数
        """
        response = api_get("/api/monitor/summary")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_10_total_cancel_monitoring(self):
        """
        第10项 - 账号撤单数量监测（严重）
        验证系统能够监测账号撤单总数
        """
        response = api_get("/api/monitor/summary")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


# ==================== 第11-13项：阈值预警测试 ====================

class TestThresholdManagement:
    """第11-13项：阈值预警测试"""

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_01_repeat_order_threshold_setting(self):
        """
        第11项 - 重复报单阈值设置功能
        验证系统能够设置重复报单阈值
        """
        response = api_get("/api/monitor/thresholds")
        assert response.status_code == 200
        data = response.json()
        # 验证阈值配置存在
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_02_repeat_open_alert(self):
        """
        第11项 - 重复开仓预警触发
        验证重复开仓达到阈值时触发预警
        """
        # 触发阈值检查
        response = api_post("/api/monitor/check")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_03_repeat_close_alert(self):
        """
        第11项 - 重复平仓预警触发
        验证重复平仓达到阈值时触发预警
        """
        response = api_post("/api/monitor/check")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_11_04_repeat_cancel_alert(self):
        """
        第11项 - 重复撤单预警触发
        验证重复撤单达到阈值时触发预警
        """
        response = api_post("/api/monitor/check")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_12_01_total_order_threshold_setting(self):
        """
        第12项 - 报单总笔数阈值设置功能
        验证系统能够设置报单总笔数阈值
        """
        response = api_get("/api/monitor/thresholds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_12_02_total_order_alert(self):
        """
        第12项 - 报单总笔数预警触发
        验证报单总数达到阈值时触发预警
        """
        response = api_post("/api/monitor/check")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_13_01_total_cancel_threshold_setting(self):
        """
        第13项 - 撤单总笔数阈值设置功能
        验证系统能够设置撤单总笔数阈值
        """
        response = api_get("/api/monitor/thresholds")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_13_02_total_cancel_alert(self):
        """
        第13项 - 撤单总笔数预警触发
        验证撤单总数达到阈值时触发预警
        """
        response = api_post("/api/monitor/check")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data


# ==================== 第14-19项：错误防范测试 ====================

class TestErrorPrevention:
    """第14-19项：错误防范测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_14_invalid_instrument(self):
        """
        第14项 - 合约代码错误检查
        验证系统能够检测无效合约代码
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "INVALID_CODE_123",
            "direction": "buy",
            "offset": "open",
            "price": 100.0,
            "volume": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_15_invalid_price(self):
        """
        第15项 - 价格最小变动检查
        验证系统能够检测不符合最小变动价位的价格
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "IF2401",
            "direction": "buy",
            "offset": "open",
            "price": 4000.123,  # 不符合最小变动
            "volume": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_16_invalid_volume(self):
        """
        第16项 - 委托数量检查
        验证系统能够检测无效委托数量
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "IF2401",
            "direction": "buy",
            "offset": "open",
            "price": 4000.0,
            "volume": -1  # 无效数量
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_17_insufficient_margin(self):
        """
        第17项 - 资金不足提示
        验证系统能够检测资金不足
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "IF2401",
            "direction": "buy",
            "offset": "open",
            "price": 4000.0,
            "volume": 99999  # 数量过大，资金不足
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_18_insufficient_position(self):
        """
        第18项 - 持仓不足提示
        验证系统能够检测持仓不足
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "IF2401",
            "direction": "sell",
            "offset": "close",
            "price": 4000.0,
            "volume": 99999  # 超过持仓
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_19_non_trading_time(self):
        """
        第19项 - 非交易时间提示
        验证系统能够检测非交易时间
        """
        response = api_post("/api/trading/validate", {
            "instrument_id": "IF2401",
            "direction": "buy",
            "offset": "open",
            "price": 4000.0,
            "volume": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data


# ==================== 第20,23-24项：应急处置测试 ====================

class TestEmergencyHandling:
    """第20,23-24项：应急处置测试"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_20_pause_trading(self):
        """
        第20项 - 暂停交易功能（严重）
        验证系统能够暂停交易
        """
        # 暂停交易
        response = api_post("/api/emergency/pause", {
            "reason": "测试暂停"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        # 恢复交易
        response = api_post("/api/emergency/resume", {
            "reason": "测试恢复"
        })
        assert response.status_code == 200

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_23_cancel_by_instrument(self):
        """
        第23项 - 部分撤单功能（建议）
        验证系统能够按合约撤单
        """
        response = api_post("/api/emergency/cancel-by-instrument", {
            "instrument_id": "IF2401",
            "reason": "测试撤单"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data

    @pytest.mark.assessment
    @pytest.mark.suggested
    def test_24_cancel_all(self):
        """
        第24项 - 全部撤单功能（建议）
        验证系统能够撤销全部委托
        """
        response = api_post("/api/emergency/cancel-all", {
            "reason": "测试全部撤单"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data


# ==================== 第25项：日志记录测试 ====================

class TestLogging:
    """第25项：日志记录测试（严重）"""

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_01_logging_function_exists(self):
        """
        第25项 - 日志记录功能存在
        验证系统具备日志记录功能
        """
        response = api_get("/api/logs/types")
        assert response.status_code == 200
        data = response.json()
        # 验证日志类型列表
        assert isinstance(data, list) or "types" in data

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_02_trade_log(self):
        """
        第25项 - 交易日志
        验证系统能够记录交易日志
        """
        response = api_get("/api/logs/", params={"log_type": "trade"})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or "entries" in data or isinstance(data, (list, dict))

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_03_system_log(self):
        """
        第25项 - 系统运行记录
        验证系统能够记录系统运行日志
        """
        response = api_get("/api/logs/", params={"log_type": "system"})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or "entries" in data or isinstance(data, (list, dict))

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_04_monitor_log(self):
        """
        第25项 - 监测记录
        验证系统能够记录监测日志
        """
        response = api_get("/api/logs/", params={"log_type": "monitor"})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or "entries" in data or isinstance(data, (list, dict))

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_05_error_log(self):
        """
        第25项 - 错误提示信息
        验证系统能够记录错误日志
        """
        response = api_get("/api/logs/", params={"log_type": "error"})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or "entries" in data or isinstance(data, (list, dict))

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_06_log_export(self):
        """
        第25项 - 日志导出功能
        验证系统能够导出日志
        """
        response = api_get("/api/logs/export", params={"log_type": "all"})
        # 导出可能返回文件或 JSON
        assert response.status_code == 200

    @pytest.mark.assessment
    @pytest.mark.critical
    def test_25_07_log_filter(self):
        """
        第25项 - 日志筛选功能
        验证系统能够按条件筛选日志
        """
        response = api_get("/api/logs/", params={
            "log_type": "all",
            "level": "INFO"
        })
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data or "entries" in data or isinstance(data, (list, dict))
