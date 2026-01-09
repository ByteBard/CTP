#!/usr/bin/env python
"""
运行评估表自动化测试
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description='运行CTP程序化交易系统评估表测试')
    parser.add_argument('--headed', action='store_true', help='显示浏览器窗口')
    parser.add_argument('--slow', type=int, default=0, help='慢速模式（毫秒）')
    parser.add_argument('--base-url', default='http://localhost:8000', help='测试服务器URL')
    parser.add_argument('--output', default='test_reports', help='报告输出目录')
    args = parser.parse_args()

    # 设置环境变量
    os.environ['HEADLESS'] = 'false' if args.headed else 'true'
    os.environ['SLOW_MO'] = str(args.slow)
    os.environ['TEST_BASE_URL'] = args.base_url

    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)

    # 生成报告文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = os.path.join(args.output, f"report_{timestamp}.html")
    json_report = os.path.join(args.output, f"report_{timestamp}.json")

    print("=" * 60)
    print("CTP程序化交易系统 - 评估表自动化测试")
    print("=" * 60)
    print(f"测试服务器: {args.base_url}")
    print(f"浏览器模式: {'有界面' if args.headed else '无界面'}")
    print(f"报告目录: {args.output}")
    print("=" * 60)

    # 运行pytest
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/test_assessment.py',
        '-v',
        '--tb=short',
        f'--html={html_report}',
        '--self-contained-html',
        f'--json-report',
        f'--json-report-file={json_report}',
    ]

    print(f"\n运行命令: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("测试完成: 全部通过")
        else:
            print(f"测试完成: 有 {result.returncode} 个测试失败")
        print("=" * 60)
        print(f"HTML报告: {html_report}")
        print(f"JSON报告: {json_report}")

        return result.returncode

    except FileNotFoundError:
        print("错误: 请先安装 pytest-html 和 pytest-json-report")
        print("运行: pip install pytest-html pytest-json-report")
        return 1


if __name__ == '__main__':
    sys.exit(main())
