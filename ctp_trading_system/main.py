"""
CTP程序化交易系统 - 主程序入口
符合 T/ZQX 0004-2025《期货程序化交易系统功能测试指引》

功能清单：
- 接口适应性：认证、登录 (第1项)
- 基础交易功能：开仓、平仓、撤单 (第2-4项)
- 异常监测：连接状态、报单监测 (第5-10项)
- 阈值管理：阈值设置、预警功能 (第11-13项)
- 错误防范：指令检查、错误提示 (第14-19项)
- 应急处置：暂停交易、批量撤单 (第20, 23-24项)
- 日志记录：完整日志功能 (第25项)
"""
import os
import sys
import time
import signal
import argparse
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctp_trading_system.config.settings import Settings, ConnectionConfig, ThresholdConfig, AlertConfig
from ctp_trading_system.logging.trade_logger import init_logger, get_logger
from ctp_trading_system.core.ctp_gateway import CtpGateway, Direction
from ctp_trading_system.monitor.connection_monitor import ConnectionMonitor, ConnectionState
from ctp_trading_system.monitor.order_monitor import OrderMonitor
from ctp_trading_system.monitor.threshold_manager import ThresholdManager
from ctp_trading_system.validator.order_validator import OrderValidator
from ctp_trading_system.alert.alert_service import AlertService, AlertLevel
from ctp_trading_system.emergency.emergency_handler import EmergencyHandler


class TradingSystem:
    """
    程序化交易系统
    整合所有模块，提供统一接口
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化交易系统

        Args:
            config_path: 配置文件路径（可选）
        """
        # 加载配置
        if config_path and os.path.exists(config_path):
            self.settings = Settings.load_from_yaml(config_path)
        else:
            self.settings = Settings()

        # 初始化日志系统（第25项）
        self.logger = init_logger(
            log_dir=self.settings.log.log_dir,
            rotation=self.settings.log.rotation,
            retention=self.settings.log.retention
        )
        self.logger.log_system("="*60)
        self.logger.log_system("CTP程序化交易系统启动")
        self.logger.log_system("符合 T/ZQX 0004-2025 期货程序化交易系统功能测试指引")
        self.logger.log_system("="*60)

        # 初始化各模块
        self._init_modules()

        # 运行状态
        self._running = False

    def _init_modules(self):
        """初始化各功能模块"""
        # CTP网关（第1-4项）
        self.gateway = CtpGateway(self.settings)
        self.logger.log_system("CTP网关初始化完成")

        # 连接监测（第5项）
        self.connection_monitor = ConnectionMonitor(self.gateway)
        self.logger.log_system("连接监测器初始化完成")

        # 报单监测（第6-10项）
        self.order_monitor = OrderMonitor()
        self.logger.log_system("报单监测器初始化完成")

        # 阈值管理（第11-13项）
        self.threshold_manager = ThresholdManager(
            self.settings.threshold,
            self.order_monitor
        )
        self.logger.log_system("阈值管理器初始化完成")

        # 交易指令验证器（第14-19项）
        self.validator = OrderValidator(self.settings)
        self.logger.log_system("交易指令验证器初始化完成")

        # 预警服务
        self.alert_service = AlertService(self.settings.alert)
        self.logger.log_system("预警服务初始化完成")

        # 应急处置（第20, 23-24项）
        self.emergency_handler = EmergencyHandler(
            self.gateway,
            self.alert_service
        )
        self.logger.log_system("应急处置器初始化完成")

        # 连接阈值预警到预警服务
        self.threshold_manager.register_alert_callback(self._on_threshold_alert)

    def _on_threshold_alert(self, alert):
        """阈值预警回调"""
        level = AlertLevel.CRITICAL if alert.alert_level.value == "CRITICAL" else AlertLevel.WARNING
        self.alert_service.send_alert(
            level=level,
            title=f"阈值预警 - {alert.threshold_type.value}",
            message=alert.message,
            source="ThresholdManager",
            data={
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "instrument_id": alert.instrument_id
            }
        )

    # ==================== 系统启动与连接 ====================

    def start(self) -> bool:
        """
        启动系统

        Returns:
            是否启动成功
        """
        self.logger.log_system("开始启动交易系统...")

        # 启动连接监测
        self.connection_monitor.start()

        # 连接CTP服务器（第1项：连通性）
        self.logger.log_system("正在连接CTP服务器...")
        if not self.gateway.connect(timeout=30):
            self.logger.log_error("连接CTP服务器失败")
            self.alert_service.critical("连接失败", "无法连接到CTP服务器")
            return False

        # 客户端认证（第1项：认证功能）
        self.logger.log_system("正在进行客户端认证...")
        if not self.gateway.authenticate(timeout=10):
            self.logger.log_error("客户端认证失败")
            self.alert_service.critical("认证失败", "客户端认证失败")
            return False

        # 用户登录（第1项：登录系统）
        self.logger.log_system("正在登录...")
        if not self.gateway.login(timeout=10):
            self.logger.log_error("用户登录失败")
            self.alert_service.critical("登录失败", "用户登录失败")
            return False

        # 确认结算单
        self.logger.log_system("正在确认结算单...")
        self.gateway.confirm_settlement(timeout=10)

        # 查询合约信息
        self.logger.log_system("正在查询合约信息...")
        instruments = self.gateway.query_instruments(timeout=60)
        self.validator.update_instruments(instruments)
        self.logger.log_system(f"已加载{len(instruments)}个合约")

        self._running = True
        self.logger.log_system("交易系统启动成功")
        self.alert_service.info("系统启动", "交易系统启动成功")

        return True

    def stop(self):
        """停止系统"""
        self.logger.log_system("正在停止交易系统...")

        self._running = False

        # 停止连接监测
        self.connection_monitor.stop()

        # 关闭网关
        self.gateway.close()

        self.logger.log_system("交易系统已停止")

    # ==================== 交易接口 ====================

    def open_long(self, instrument_id: str, price: float, volume: int) -> Optional[str]:
        """
        买入开仓（做多）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量

        Returns:
            报单引用
        """
        # 验证（第14-19项）
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='0',
            offset='0',
            price=price,
            volume=volume
        )
        if not result.is_valid:
            self.alert_service.warning("报单验证失败", result.error_message)
            return None

        # 记录监测（第6项）
        self.order_monitor.count_open_order(instrument_id, volume)

        # 发送报单（第2项）
        return self.gateway.open_position(instrument_id, Direction.BUY, price, volume)

    def open_short(self, instrument_id: str, price: float, volume: int) -> Optional[str]:
        """
        卖出开仓（做空）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量

        Returns:
            报单引用
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='1',
            offset='0',
            price=price,
            volume=volume
        )
        if not result.is_valid:
            self.alert_service.warning("报单验证失败", result.error_message)
            return None

        self.order_monitor.count_open_order(instrument_id, volume)
        return self.gateway.open_position(instrument_id, Direction.SELL, price, volume)

    def close_long(self, instrument_id: str, price: float, volume: int,
                   close_today: bool = False) -> Optional[str]:
        """
        卖出平仓（平多仓）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量
            close_today: 是否平今

        Returns:
            报单引用
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='1',
            offset='1',
            price=price,
            volume=volume
        )
        if not result.is_valid:
            self.alert_service.warning("报单验证失败", result.error_message)
            return None

        # 记录监测（第7项）
        self.order_monitor.count_close_order(instrument_id, volume)

        # 发送报单（第3项）
        return self.gateway.close_position(instrument_id, Direction.SELL, price, volume, close_today)

    def close_short(self, instrument_id: str, price: float, volume: int,
                    close_today: bool = False) -> Optional[str]:
        """
        买入平仓（平空仓）

        Args:
            instrument_id: 合约代码
            price: 价格
            volume: 数量
            close_today: 是否平今

        Returns:
            报单引用
        """
        result = self.validator.validate_order(
            instrument_id=instrument_id,
            direction='0',
            offset='1',
            price=price,
            volume=volume
        )
        if not result.is_valid:
            self.alert_service.warning("报单验证失败", result.error_message)
            return None

        self.order_monitor.count_close_order(instrument_id, volume)
        return self.gateway.close_position(instrument_id, Direction.BUY, price, volume, close_today)

    def cancel_order(self, instrument_id: str, order_ref: str) -> bool:
        """
        撤单

        Args:
            instrument_id: 合约代码
            order_ref: 报单引用

        Returns:
            是否发送成功
        """
        # 记录监测（第8项）
        self.order_monitor.count_cancel_order(instrument_id)

        # 发送撤单（第4项）
        return self.gateway.cancel_order(instrument_id, order_ref)

    # ==================== 应急处置 ====================

    def emergency_stop(self, reason: str = "紧急停止"):
        """一键紧急停止（第20项）"""
        self.emergency_handler.emergency_stop(reason)

    def pause_trading(self, reason: str = "暂停交易"):
        """暂停交易（第20项）"""
        self.emergency_handler.pause_trading(reason)

    def resume_trading(self, reason: str = "恢复交易"):
        """恢复交易"""
        self.emergency_handler.resume_trading(reason)

    def cancel_all_orders(self, reason: str = "全部撤单"):
        """全部撤单（第24项）"""
        return self.emergency_handler.cancel_all_orders(reason)

    # ==================== 状态查询 ====================

    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            "running": self._running,
            "connection": self.connection_monitor.get_status_report(),
            "order_stats": self.order_monitor.get_summary_report(),
            "threshold_status": self.threshold_manager.get_threshold_status(),
            "emergency_status": self.emergency_handler.get_status_report()
        }

    def print_status(self):
        """打印系统状态"""
        status = self.get_system_status()
        print("\n" + "="*60)
        print("系统状态报告")
        print("="*60)
        print(f"运行状态: {'运行中' if status['running'] else '已停止'}")
        print(f"连接状态: {status['connection']['current_state']}")
        print(f"报单总数: {status['order_stats']['total_order_count']}")
        print(f"撤单总数: {status['order_stats']['total_cancel_count']}")
        print(f"交易暂停: {status['emergency_status']['trading_paused']}")
        print("="*60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CTP程序化交易系统')
    parser.add_argument('-c', '--config', help='配置文件路径')
    parser.add_argument('--broker', default='9999', help='经纪公司代码')
    parser.add_argument('--user', help='投资者账号')
    parser.add_argument('--password', help='密码')
    parser.add_argument('--front', default='tcp://180.168.146.187:10201', help='交易前置')
    args = parser.parse_args()

    # 创建系统实例
    system = TradingSystem(args.config)

    # 更新配置
    if args.user:
        system.settings.connection.investor_id = args.user
    if args.password:
        system.settings.connection.password = args.password
    if args.broker:
        system.settings.connection.broker_id = args.broker
    if args.front:
        system.settings.connection.trade_front = args.front

    # 信号处理
    def signal_handler(signum, frame):
        print("\n收到退出信号，正在停止系统...")
        system.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动系统
    if system.start():
        print("\n系统已启动，按Ctrl+C退出")
        system.print_status()

        # 主循环
        while system._running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break

        system.stop()
    else:
        print("系统启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
