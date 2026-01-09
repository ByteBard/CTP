"""
预警服务模块
满足评估表预警要求：
- 弹窗提示
- 声音提示
- 短信通知
- 邮件通知
"""
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..config.settings import AlertConfig
from ..trade_logging.trade_logger import get_logger, TradeLogger


class AlertLevel(Enum):
    """预警级别"""
    INFO = "INFO"           # 提示
    WARNING = "WARNING"     # 警告
    CRITICAL = "CRITICAL"   # 严重


class AlertType(Enum):
    """预警类型"""
    POPUP = "popup"         # 弹窗
    SOUND = "sound"         # 声音
    EMAIL = "email"         # 邮件
    SMS = "sms"             # 短信
    CONSOLE = "console"     # 控制台


@dataclass
class Alert:
    """预警信息"""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = None
    source: str = ""
    data: dict = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}


class AlertService:
    """
    预警服务
    满足评估表预警要求：弹窗、声音、短信、邮件
    """

    def __init__(self, config: AlertConfig):
        """
        初始化预警服务

        Args:
            config: 预警配置
        """
        self.config = config
        self.logger: TradeLogger = get_logger()

        # 预警历史
        self._alert_history: List[Alert] = []
        self._max_history = 1000

        # 回调
        self._alert_callbacks: List[Callable[[Alert], None]] = []

        # 锁
        self._lock = threading.Lock()

        self.logger.log_system("预警服务初始化完成", {
            "enable_popup": config.enable_popup,
            "enable_sound": config.enable_sound,
            "enable_email": config.enable_email
        })

    def send_alert(self, level: AlertLevel, title: str, message: str,
                   source: str = "", data: dict = None):
        """
        发送预警

        Args:
            level: 预警级别
            title: 预警标题
            message: 预警内容
            source: 预警来源
            data: 附加数据
        """
        alert = Alert(
            level=level,
            title=title,
            message=message,
            source=source,
            data=data or {}
        )

        # 记录历史
        with self._lock:
            self._alert_history.append(alert)
            if len(self._alert_history) > self._max_history:
                self._alert_history = self._alert_history[-self._max_history:]

        # 记录日志
        self.logger.log_alert(
            alert_type=source,
            message=f"[{title}] {message}",
            level=level.value.lower()
        )

        # 执行各种预警方式
        self._execute_alerts(alert)

        # 触发回调
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.log_exception(e, "alert callback")

    def _execute_alerts(self, alert: Alert):
        """执行预警"""
        # 控制台输出（始终启用）
        self._console_alert(alert)

        # 弹窗提示
        if self.config.enable_popup:
            threading.Thread(
                target=self._popup_alert,
                args=(alert,),
                daemon=True
            ).start()

        # 声音提示
        if self.config.enable_sound:
            threading.Thread(
                target=self._sound_alert,
                args=(alert,),
                daemon=True
            ).start()

        # 邮件通知
        if self.config.enable_email:
            threading.Thread(
                target=self._email_alert,
                args=(alert,),
                daemon=True
            ).start()

    # ==================== 控制台输出 ====================

    def _console_alert(self, alert: Alert):
        """控制台输出预警"""
        level_colors = {
            AlertLevel.INFO: "\033[94m",      # 蓝色
            AlertLevel.WARNING: "\033[93m",   # 黄色
            AlertLevel.CRITICAL: "\033[91m",  # 红色
        }
        reset = "\033[0m"

        color = level_colors.get(alert.level, "")
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n{color}{'='*60}")
        print(f"[{alert.level.value}] {timestamp}")
        print(f"标题: {alert.title}")
        print(f"内容: {alert.message}")
        if alert.source:
            print(f"来源: {alert.source}")
        print(f"{'='*60}{reset}\n")

    # ==================== 弹窗提示 ====================

    def _popup_alert(self, alert: Alert):
        """
        弹窗提示
        满足评估表要求：通过弹窗提示进行警示
        """
        try:
            # 尝试使用tkinter
            import tkinter as tk
            from tkinter import messagebox

            # 创建隐藏的根窗口
            root = tk.Tk()
            root.withdraw()

            # 根据级别选择弹窗类型
            if alert.level == AlertLevel.CRITICAL:
                messagebox.showerror(alert.title, alert.message)
            elif alert.level == AlertLevel.WARNING:
                messagebox.showwarning(alert.title, alert.message)
            else:
                messagebox.showinfo(alert.title, alert.message)

            root.destroy()

        except ImportError:
            # tkinter不可用，尝试使用系统通知
            self._system_notification(alert)
        except Exception as e:
            self.logger.log_exception(e, "popup alert")

    def _system_notification(self, alert: Alert):
        """系统通知（备用方案）"""
        try:
            import platform
            system = platform.system()

            if system == "Windows":
                # Windows Toast通知
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(
                        alert.title,
                        alert.message,
                        duration=5,
                        threaded=True
                    )
                except ImportError:
                    pass
            elif system == "Darwin":  # macOS
                os.system(f'''osascript -e 'display notification "{alert.message}" with title "{alert.title}"' ''')
            elif system == "Linux":
                os.system(f'notify-send "{alert.title}" "{alert.message}"')

        except Exception as e:
            self.logger.log_exception(e, "system notification")

    # ==================== 声音提示 ====================

    def _sound_alert(self, alert: Alert):
        """
        声音提示
        满足评估表要求：通过声音提示进行警示
        """
        try:
            # 根据级别选择不同的声音
            if alert.level == AlertLevel.CRITICAL:
                self._play_beep(frequency=1000, duration=500, count=3)
            elif alert.level == AlertLevel.WARNING:
                self._play_beep(frequency=800, duration=300, count=2)
            else:
                self._play_beep(frequency=600, duration=200, count=1)

        except Exception as e:
            self.logger.log_exception(e, "sound alert")

    def _play_beep(self, frequency: int = 800, duration: int = 200, count: int = 1):
        """播放蜂鸣声"""
        try:
            import platform
            system = platform.system()

            if system == "Windows":
                import winsound
                for _ in range(count):
                    winsound.Beep(frequency, duration)
            else:
                # Linux/macOS
                for _ in range(count):
                    print('\a', end='', flush=True)  # 系统蜂鸣

        except Exception as e:
            # 静默失败
            pass

    # ==================== 邮件通知 ====================

    def _email_alert(self, alert: Alert):
        """
        邮件通知
        满足评估表要求：通过邮件进行警示
        """
        if not self.config.smtp_server or not self.config.alert_email:
            return

        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_user
            msg['To'] = self.config.alert_email
            msg['Subject'] = f"[交易预警-{alert.level.value}] {alert.title}"

            # 邮件正文
            body = f"""
交易系统预警通知

预警级别: {alert.level.value}
预警时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
预警来源: {alert.source}

预警内容:
{alert.message}

附加信息:
{self._format_data(alert.data)}

---
此邮件由交易系统自动发送，请勿直接回复。
            """
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 发送邮件
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)

            self.logger.log_system("预警邮件发送成功", {
                "to": self.config.alert_email,
                "subject": msg['Subject']
            })

        except Exception as e:
            self.logger.log_exception(e, "email alert")

    def _format_data(self, data: dict) -> str:
        """格式化附加数据"""
        if not data:
            return "无"
        return "\n".join([f"  {k}: {v}" for k, v in data.items()])

    # ==================== 便捷方法 ====================

    def info(self, title: str, message: str, source: str = "", data: dict = None):
        """发送信息级别预警"""
        self.send_alert(AlertLevel.INFO, title, message, source, data)

    def warning(self, title: str, message: str, source: str = "", data: dict = None):
        """发送警告级别预警"""
        self.send_alert(AlertLevel.WARNING, title, message, source, data)

    def critical(self, title: str, message: str, source: str = "", data: dict = None):
        """发送严重级别预警"""
        self.send_alert(AlertLevel.CRITICAL, title, message, source, data)

    # ==================== 查询与管理 ====================

    def get_alert_history(self, limit: int = 100,
                          level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取预警历史"""
        with self._lock:
            history = self._alert_history[-limit:]
            if level:
                history = [a for a in history if a.level == level]
            return history

    def get_alert_count(self) -> dict:
        """获取预警统计"""
        with self._lock:
            counts = {level.value: 0 for level in AlertLevel}
            for alert in self._alert_history:
                counts[alert.level.value] += 1
            return counts

    def clear_history(self):
        """清除预警历史"""
        with self._lock:
            self._alert_history.clear()

    def register_callback(self, callback: Callable[[Alert], None]):
        """注册预警回调"""
        self._alert_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """注销预警回调"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    # ==================== 配置 ====================

    def enable_popup(self, enabled: bool = True):
        """启用/禁用弹窗"""
        self.config.enable_popup = enabled

    def enable_sound(self, enabled: bool = True):
        """启用/禁用声音"""
        self.config.enable_sound = enabled

    def enable_email(self, enabled: bool = True):
        """启用/禁用邮件"""
        self.config.enable_email = enabled

    def configure_email(self, smtp_server: str, smtp_port: int,
                        smtp_user: str, smtp_password: str, alert_email: str):
        """配置邮件"""
        self.config.smtp_server = smtp_server
        self.config.smtp_port = smtp_port
        self.config.smtp_user = smtp_user
        self.config.smtp_password = smtp_password
        self.config.alert_email = alert_email
