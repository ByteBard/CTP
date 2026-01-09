"""
Pytest配置和Fixtures
用于Playwright自动化测试
"""
import os
import sys
import pytest
import asyncio
from typing import Generator

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
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_url() -> str:
    """测试服务器URL"""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


# ==================== Playwright Fixtures ====================

@pytest.fixture(scope="session")
async def browser_context_args():
    """浏览器上下文参数"""
    return {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai"
    }


@pytest.fixture(scope="session")
async def browser(playwright):
    """创建浏览器实例"""
    browser = await playwright.chromium.launch(
        headless=os.environ.get("HEADLESS", "true").lower() == "true",
        slow_mo=int(os.environ.get("SLOW_MO", "0"))
    )
    yield browser
    await browser.close()


@pytest.fixture
async def page(browser, browser_context_args, base_url):
    """创建页面实例"""
    context = await browser.new_context(**browser_context_args)
    page = await context.new_page()

    # 设置默认超时
    page.set_default_timeout(30000)

    # 导航到主页
    await page.goto(base_url)
    await page.wait_for_load_state("networkidle")

    yield page

    await page.close()
    await context.close()


@pytest.fixture
async def connected_page(page):
    """已连接的页面（用于需要登录后的测试）"""
    # 填写连接信息
    await page.fill("#input-broker-id", "9999")
    await page.fill("#input-trade-front", "tcp://180.168.146.187:10201")

    # 连接
    await page.click("#btn-connect")
    await page.wait_for_timeout(2000)

    # 认证
    await page.click("#btn-authenticate")
    await page.wait_for_timeout(1000)

    # 登录（使用测试账号）
    await page.fill("#input-investor-id", os.environ.get("TEST_USER", "test_user"))
    await page.fill("#input-password", os.environ.get("TEST_PASSWORD", "test_pass"))
    await page.click("#btn-login")
    await page.wait_for_timeout(2000)

    yield page


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

async def wait_for_element(page, selector, timeout=5000):
    """等待元素出现"""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        return False


async def get_text(page, selector):
    """获取元素文本"""
    element = await page.query_selector(selector)
    if element:
        return await element.text_content()
    return None


async def click_and_wait(page, selector, wait_time=500):
    """点击并等待"""
    await page.click(selector)
    await page.wait_for_timeout(wait_time)
