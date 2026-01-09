"""
CTP程序化交易系统
符合 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》

模块说明：
- config: 系统配置
- core: CTP网关核心
- monitor: 监测模块（连接、报单、阈值）
- validator: 交易指令验证
- alert: 预警服务
- emergency: 应急处置
- logging: 日志系统
- strategy: 策略基类

评估表功能对照：
- 第1项（接口适应性）: core.ctp_gateway
- 第2-4项（基础交易功能）: core.ctp_gateway
- 第5项（连接监测）: monitor.connection_monitor
- 第6-10项（报单监测）: monitor.order_monitor
- 第11-13项（阈值管理）: monitor.threshold_manager
- 第14-19项（错误防范）: validator.order_validator
- 第20, 23-24项（应急处置）: emergency.emergency_handler
- 第25项（日志记录）: logging.trade_logger
"""

__version__ = "1.0.0"
__author__ = "CTP Trading System"
__description__ = "符合T/ZQX 0004-2025期货程序化交易系统功能测试指引的交易系统"

from .main import TradingSystem
