"""
Pytest配置和Fixtures
用于Playwright自动化测试
"""
import os
import sys
import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== Pytest配置 ====================

def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "assessment: 评估表测试用例")
    config.addinivalue_line("markers", "critical: 严重级别测试")
    config.addinivalue_line("markers", "suggested: 建议级别测试")


# ==================== 基础Fixtures ====================

@pytest.fixture(scope="session")
def base_url() -> str:
    """测试服务器URL"""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """浏览器上下文参数"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai"
    }


# ==================== 测试报告Fixtures ====================

@pytest.fixture(scope="session")
def test_results():
    """收集测试结果"""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "critical_total": 0,
        "critical_passed": 0,
        "suggested_total": 0,
        "suggested_passed": 0,
        "items": []
    }
    yield results


@pytest.fixture(autouse=True)
def record_result(request, test_results):
    """记录每个测试结果"""
    yield

    # 获取测试结果
    test_results["total"] += 1

    is_critical = "critical" in [m.name for m in request.node.iter_markers()]
    is_suggested = "suggested" in [m.name for m in request.node.iter_markers()]

    if is_critical:
        test_results["critical_total"] += 1
    if is_suggested:
        test_results["suggested_total"] += 1

    if hasattr(request.node, "rep_call") and request.node.rep_call.passed:
        test_results["passed"] += 1
        if is_critical:
            test_results["critical_passed"] += 1
        if is_suggested:
            test_results["suggested_passed"] += 1
        status = "PASSED"
    else:
        test_results["failed"] += 1
        status = "FAILED"

    test_results["items"].append({
        "name": request.node.name,
        "status": status,
        "critical": is_critical,
        "suggested": is_suggested
    })


# ==================== 辅助函数 ====================

def wait_for_element(page, selector, timeout=5000):
    """等待元素出现"""
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        return False


def get_text(page, selector):
    """获取元素文本"""
    element = page.query_selector(selector)
    if element:
        return element.text_content()
    return None


def click_and_wait(page, selector, wait_time=500):
    """点击并等待"""
    page.click(selector)
    page.wait_for_timeout(wait_time)
