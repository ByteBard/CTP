"""
测试报告生成器
生成符合评估表格式的测试报告
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any


class AssessmentReportGenerator:
    """评估表测试报告生成器"""

    # 评估项目定义
    ASSESSMENT_ITEMS = {
        1: {"name": "接口适应性 - 连通性", "sub": ["连接服务器", "客户端认证", "用户登录"], "level": "严重"},
        2: {"name": "基础交易功能 - 开仓指令", "level": "严重"},
        3: {"name": "基础交易功能 - 平仓指令", "level": "严重"},
        4: {"name": "基础交易功能 - 撤单指令", "level": "严重"},
        5: {"name": "异常监测 - 连接状态监测", "level": "严重"},
        6: {"name": "异常监测 - 单合约重复开仓监测", "level": "建议"},
        7: {"name": "异常监测 - 单合约重复平仓监测", "level": "建议"},
        8: {"name": "异常监测 - 单合约重复撤单监测", "level": "建议"},
        9: {"name": "异常监测 - 账号报单数量监测", "level": "严重"},
        10: {"name": "异常监测 - 账号撤单数量监测", "level": "严重"},
        11: {"name": "阈值管理 - 重复报单阈值及预警", "level": "建议"},
        12: {"name": "阈值管理 - 报单总笔数阈值及预警", "level": "严重"},
        13: {"name": "阈值管理 - 撤单总笔数阈值及预警", "level": "严重"},
        14: {"name": "错误防范 - 合约代码错误检查", "level": "严重"},
        15: {"name": "错误防范 - 价格最小变动检查", "level": "严重"},
        16: {"name": "错误防范 - 委托数量检查", "level": "严重"},
        17: {"name": "错误防范 - 资金不足提示", "level": "严重"},
        18: {"name": "错误防范 - 持仓不足提示", "level": "严重"},
        19: {"name": "错误防范 - 非交易时间提示", "level": "严重"},
        20: {"name": "应急处置 - 暂停交易功能", "level": "严重"},
        23: {"name": "应急处置 - 部分撤单功能", "level": "建议"},
        24: {"name": "应急处置 - 全部撤单功能", "level": "建议"},
        25: {"name": "日志记录 - 完整日志记录", "level": "严重"},
    }

    def __init__(self):
        self.results: Dict[int, Dict[str, Any]] = {}
        self.start_time = None
        self.end_time = None

    def start(self):
        """开始测试"""
        self.start_time = datetime.now()
        self.results = {}

    def record_result(self, item_num: int, passed: bool, duration: float = 0,
                      sub_item: str = None, message: str = ""):
        """记录测试结果"""
        if item_num not in self.results:
            self.results[item_num] = {
                "passed": True,
                "sub_results": [],
                "duration": 0,
                "messages": []
            }

        if sub_item:
            self.results[item_num]["sub_results"].append({
                "name": sub_item,
                "passed": passed,
                "duration": duration,
                "message": message
            })
            if not passed:
                self.results[item_num]["passed"] = False
        else:
            self.results[item_num]["passed"] = passed

        self.results[item_num]["duration"] += duration
        if message:
            self.results[item_num]["messages"].append(message)

    def finish(self):
        """结束测试"""
        self.end_time = datetime.now()

    def generate_text_report(self) -> str:
        """生成文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("评估表测试报告")
        lines.append("=" * 60)
        lines.append(f"测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}")
        lines.append(f"测试环境: Windows / Python / Playwright")
        lines.append("")
        lines.append(f"{'评估项目':<40} {'结果':<8} {'用时':<8}")
        lines.append("-" * 60)

        critical_total = 0
        critical_passed = 0
        suggested_total = 0
        suggested_passed = 0
        total_duration = 0

        for item_num, item_info in sorted(self.ASSESSMENT_ITEMS.items()):
            result = self.results.get(item_num, {"passed": False, "duration": 0, "sub_results": []})
            passed = result.get("passed", False)
            duration = result.get("duration", 0)
            total_duration += duration

            # 统计
            if item_info["level"] == "严重":
                critical_total += 1
                if passed:
                    critical_passed += 1
            else:
                suggested_total += 1
                if passed:
                    suggested_passed += 1

            # 格式化结果
            status = "✓" if passed else "✗"
            duration_str = f"{duration:.1f}s" if duration else "-"

            # 主项
            item_name = f"第{item_num}项 - {item_info['name']}"
            if "sub" in item_info:
                lines.append(f"{item_name:<40}")
                for sub in item_info["sub"]:
                    sub_result = next(
                        (sr for sr in result.get("sub_results", []) if sr["name"] == sub),
                        {"passed": False, "duration": 0}
                    )
                    sub_status = "✓" if sub_result.get("passed") else "✗"
                    sub_duration = f"{sub_result.get('duration', 0):.1f}s"
                    lines.append(f"  ├─ {sub:<36} {sub_status:<8} {sub_duration:<8}")
            else:
                lines.append(f"{item_name:<40} {status:<8} {duration_str:<8}")

        lines.append("=" * 60)
        total_items = critical_total + suggested_total
        total_passed = critical_passed + suggested_passed
        lines.append(f"总计: {total_passed}/{total_items} 通过 ({100*total_passed/total_items:.0f}%)")
        lines.append(f"严重项: {critical_passed}/{critical_total} 通过")
        lines.append(f"建议项: {suggested_passed}/{suggested_total} 通过")
        lines.append(f"总用时: {total_duration:.1f}s")

        return "\n".join(lines)

    def generate_json_report(self) -> dict:
        """生成JSON格式报告"""
        critical_total = 0
        critical_passed = 0
        suggested_total = 0
        suggested_passed = 0

        items = []
        for item_num, item_info in sorted(self.ASSESSMENT_ITEMS.items()):
            result = self.results.get(item_num, {"passed": False, "duration": 0})
            passed = result.get("passed", False)

            if item_info["level"] == "严重":
                critical_total += 1
                if passed:
                    critical_passed += 1
            else:
                suggested_total += 1
                if passed:
                    suggested_passed += 1

            items.append({
                "number": item_num,
                "name": item_info["name"],
                "level": item_info["level"],
                "passed": passed,
                "duration": result.get("duration", 0),
                "sub_results": result.get("sub_results", []),
                "messages": result.get("messages", [])
            })

        return {
            "title": "评估表测试报告",
            "test_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "summary": {
                "total": critical_total + suggested_total,
                "passed": critical_passed + suggested_passed,
                "critical_total": critical_total,
                "critical_passed": critical_passed,
                "suggested_total": suggested_total,
                "suggested_passed": suggested_passed
            },
            "items": items
        }

    def generate_html_report(self) -> str:
        """生成HTML格式报告"""
        json_data = self.generate_json_report()

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>评估表测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #4a90d9; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .passed {{ color: #28a745; font-weight: bold; }}
        .failed {{ color: #dc3545; font-weight: bold; }}
        .critical {{ background: #fff3cd; }}
        .suggested {{ background: #d1ecf1; }}
    </style>
</head>
<body>
    <h1>CTP程序化交易系统 - 评估表测试报告</h1>
    <p>测试时间: {json_data['test_time']}</p>

    <div class="summary">
        <div class="summary-item"><strong>总计:</strong> {json_data['summary']['passed']}/{json_data['summary']['total']} 通过</div>
        <div class="summary-item"><strong>严重项:</strong> {json_data['summary']['critical_passed']}/{json_data['summary']['critical_total']} 通过</div>
        <div class="summary-item"><strong>建议项:</strong> {json_data['summary']['suggested_passed']}/{json_data['summary']['suggested_total']} 通过</div>
    </div>

    <table>
        <tr>
            <th>序号</th>
            <th>评估项目</th>
            <th>问题等级</th>
            <th>测试结果</th>
            <th>用时</th>
        </tr>
"""
        for item in json_data['items']:
            level_class = "critical" if item['level'] == "严重" else "suggested"
            result_class = "passed" if item['passed'] else "failed"
            result_text = "✓ 通过" if item['passed'] else "✗ 失败"

            html += f"""        <tr class="{level_class}">
            <td>第{item['number']}项</td>
            <td>{item['name']}</td>
            <td>{item['level']}</td>
            <td class="{result_class}">{result_text}</td>
            <td>{item['duration']:.1f}s</td>
        </tr>
"""

        html += """    </table>
</body>
</html>"""
        return html

    def save_reports(self, output_dir: str = "test_reports"):
        """保存所有格式的报告"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 文本报告
        text_path = os.path.join(output_dir, f"report_{timestamp}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_text_report())

        # JSON报告
        json_path = os.path.join(output_dir, f"report_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.generate_json_report(), f, ensure_ascii=False, indent=2)

        # HTML报告
        html_path = os.path.join(output_dir, f"report_{timestamp}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_html_report())

        return {
            "text": text_path,
            "json": json_path,
            "html": html_path
        }


# 全局报告生成器实例
report_generator = AssessmentReportGenerator()


def get_report_generator() -> AssessmentReportGenerator:
    """获取报告生成器实例"""
    return report_generator
