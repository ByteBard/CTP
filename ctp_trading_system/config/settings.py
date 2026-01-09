"""
系统配置模块
符合评估表要求：阈值设置、连接配置
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
import yaml
import os


@dataclass
class ConnectionConfig:
    """CTP连接配置"""
    broker_id: str = "9999"                              # 经纪公司代码
    investor_id: str = ""                                # 投资者账号
    password: str = ""                                   # 密码
    app_id: str = "simnow_client_test"                   # 应用ID
    auth_code: str = "0000000000000000"                  # 认证码
    trade_front: str = "tcp://180.168.146.187:10201"     # 交易前置（SimNow）
    md_front: str = "tcp://180.168.146.187:10211"        # 行情前置（SimNow）
    flow_path: str = "./flow/"                           # 流文件路径


@dataclass
class ThresholdConfig:
    """
    阈值配置
    满足评估表第11-13项：阈值设置功能
    """
    # 重复报单阈值（建议项）
    repeat_open_threshold: int = 10      # 单合约重复开仓阈值
    repeat_close_threshold: int = 10     # 单合约重复平仓阈值
    repeat_cancel_threshold: int = 10    # 单合约重复撤单阈值

    # 总笔数阈值（严重项）
    total_order_threshold: int = 500     # 报单总笔数阈值
    total_cancel_threshold: int = 500    # 撤单总笔数阈值

    # 单笔委托限制
    max_order_volume: int = 1000         # 单笔最大委托手数


@dataclass
class AlertConfig:
    """预警配置"""
    enable_popup: bool = True            # 启用弹窗提示
    enable_sound: bool = True            # 启用声音提示
    enable_email: bool = False           # 启用邮件通知
    enable_sms: bool = False             # 启用短信通知

    # 邮件配置
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email: str = ""                # 接收预警的邮箱


@dataclass
class LogConfig:
    """日志配置"""
    log_dir: str = "./logs"              # 日志目录
    trade_log: str = "trade.log"         # 交易日志
    system_log: str = "system.log"       # 系统日志
    monitor_log: str = "monitor.log"     # 监测日志
    error_log: str = "error.log"         # 错误日志
    rotation: str = "1 day"              # 日志轮转
    retention: str = "30 days"           # 日志保留


@dataclass
class Settings:
    """系统总配置"""
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log: LogConfig = field(default_factory=LogConfig)

    # 合约信息缓存
    instruments: Dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load_from_yaml(cls, path: str) -> "Settings":
        """从YAML文件加载配置"""
        if not os.path.exists(path):
            return cls()

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        settings = cls()

        if 'connection' in data:
            settings.connection = ConnectionConfig(**data['connection'])
        if 'threshold' in data:
            settings.threshold = ThresholdConfig(**data['threshold'])
        if 'alert' in data:
            settings.alert = AlertConfig(**data['alert'])
        if 'log' in data:
            settings.log = LogConfig(**data['log'])

        return settings

    def save_to_yaml(self, path: str):
        """保存配置到YAML文件"""
        data = {
            'connection': {
                'broker_id': self.connection.broker_id,
                'investor_id': self.connection.investor_id,
                'password': self.connection.password,
                'app_id': self.connection.app_id,
                'auth_code': self.connection.auth_code,
                'trade_front': self.connection.trade_front,
                'md_front': self.connection.md_front,
            },
            'threshold': {
                'repeat_open_threshold': self.threshold.repeat_open_threshold,
                'repeat_close_threshold': self.threshold.repeat_close_threshold,
                'repeat_cancel_threshold': self.threshold.repeat_cancel_threshold,
                'total_order_threshold': self.threshold.total_order_threshold,
                'total_cancel_threshold': self.threshold.total_cancel_threshold,
                'max_order_volume': self.threshold.max_order_volume,
            },
            'alert': {
                'enable_popup': self.alert.enable_popup,
                'enable_sound': self.alert.enable_sound,
                'enable_email': self.alert.enable_email,
            },
            'log': {
                'log_dir': self.log.log_dir,
            }
        }

        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
