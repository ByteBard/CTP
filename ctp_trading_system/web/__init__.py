"""
Web UI 模块
提供基于FastAPI的Web界面，用于第三方评估测试
"""

from .app import create_app, get_trading_system

__all__ = ['create_app', 'get_trading_system']
