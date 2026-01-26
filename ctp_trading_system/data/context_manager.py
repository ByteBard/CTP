"""
交易上下文异步保存管理器
来源: C:\Repo\future-trading-strategy\live\trade_context.py

特点:
- 异步保存 (非阻塞，不影响交易执行)
- 后台线程 + 消息队列
- 双格式存储: Pickle (完整) + JSON (可读)
"""

import queue
import threading
import pickle
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import logging

from .trade_context import TradeContext

logger = logging.getLogger(__name__)


class ContextManager:
    """
    交易上下文异步保存管理器

    来源: C:\Repo\future-trading-strategy\live\trade_context.py

    特点:
    - 异步保存 (非阻塞，不影响交易执行)
    - 后台线程 + 消息队列
    - 双格式存储: Pickle (完整) + JSON (可读摘要)
    """

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: 备份数据根目录，默认为 ctp_trading_system/data_backup
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data_backup"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._save_count = 0
        self._error_count = 0

    def start(self):
        """启动后台保存线程"""
        if self._running:
            logger.warning("[ContextManager] 已在运行中")
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._worker_thread.start()
        logger.info(f"[ContextManager] 启动，保存目录: {self.base_dir}")

    def stop(self):
        """停止后台线程"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info(f"[ContextManager] 停止，保存{self._save_count}个，错误{self._error_count}个")

    def save(self, ctx: TradeContext):
        """
        保存交易上下文 (非阻塞)

        立即返回，实际保存在后台线程执行

        Args:
            ctx: 交易上下文
        """
        if not ctx.trade_id:
            ctx.trade_id = ctx.generate_id()
        self._queue.put(ctx)

    def save_sync(self, ctx: TradeContext):
        """
        同步保存交易上下文 (阻塞)

        用于测试或强制保存

        Args:
            ctx: 交易上下文
        """
        if not ctx.trade_id:
            ctx.trade_id = ctx.generate_id()
        self._save_to_disk(ctx)

    def _save_worker(self):
        """后台保存线程"""
        while self._running:
            try:
                ctx = self._queue.get(timeout=1)
                self._save_to_disk(ctx)
                self._save_count += 1
            except queue.Empty:
                continue
            except Exception as e:
                self._error_count += 1
                logger.error(f"[ContextManager] 保存失败: {e}")

        # 处理剩余队列
        while not self._queue.empty():
            try:
                ctx = self._queue.get_nowait()
                self._save_to_disk(ctx)
                self._save_count += 1
            except:
                break

    def _save_to_disk(self, ctx: TradeContext):
        """实际保存到磁盘"""
        # 构建路径: base_dir/{symbol}/{date}/
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_dir = self.base_dir / ctx.symbol / date_str
        save_dir.mkdir(parents=True, exist_ok=True)

        base_name = f"ctx_{ctx.trade_id}"

        # 保存Pickle (完整数据)
        pkl_path = save_dir / f"{base_name}.pkl"
        with open(pkl_path, 'wb') as f:
            pickle.dump(ctx, f)

        # 保存JSON (可读摘要)
        json_path = save_dir / f"{base_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ctx.to_summary(), f, ensure_ascii=False, indent=2, default=str)

    def get_daily_contexts(self, symbol: str, date: str) -> List[TradeContext]:
        """
        获取某日所有上下文

        Args:
            symbol: 合约代码
            date: 日期 (YYYY-MM-DD)

        Returns:
            上下文列表
        """
        save_dir = self.base_dir / symbol / date
        if not save_dir.exists():
            return []

        contexts = []
        for pkl_file in sorted(save_dir.glob("ctx_*.pkl")):
            try:
                with open(pkl_file, 'rb') as f:
                    ctx = pickle.load(f)
                    contexts.append(ctx)
            except Exception as e:
                logger.warning(f"[ContextManager] 加载失败 {pkl_file}: {e}")

        return sorted(contexts, key=lambda x: x.timestamp)

    def get_context_by_id(self, symbol: str, date: str, trade_id: str) -> Optional[TradeContext]:
        """
        按ID获取上下文

        Args:
            symbol: 合约代码
            date: 日期 (YYYY-MM-DD)
            trade_id: 交易ID

        Returns:
            交易上下文或None
        """
        pkl_path = self.base_dir / symbol / date / f"ctx_{trade_id}.pkl"
        if not pkl_path.exists():
            return None

        try:
            with open(pkl_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"[ContextManager] 加载失败 {pkl_path}: {e}")
            return None

    def get_daily_summary(self, symbol: str, date: str) -> List[dict]:
        """
        获取某日的摘要列表 (从JSON文件)

        Args:
            symbol: 合约代码
            date: 日期 (YYYY-MM-DD)

        Returns:
            摘要字典列表
        """
        save_dir = self.base_dir / symbol / date
        if not save_dir.exists():
            return []

        summaries = []
        for json_file in sorted(save_dir.glob("ctx_*.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    summaries.append(json.load(f))
            except Exception as e:
                logger.warning(f"[ContextManager] 加载失败 {json_file}: {e}")

        return summaries

    def get_available_dates(self, symbol: str) -> List[str]:
        """
        获取某合约可用的日期列表

        Args:
            symbol: 合约代码

        Returns:
            日期列表
        """
        symbol_dir = self.base_dir / symbol
        if not symbol_dir.exists():
            return []

        dates = []
        for date_dir in symbol_dir.iterdir():
            if date_dir.is_dir():
                dates.append(date_dir.name)

        return sorted(dates)

    def get_available_symbols(self) -> List[str]:
        """
        获取所有可用的合约列表

        Returns:
            合约代码列表
        """
        symbols = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                symbols.append(item.name)
        return sorted(symbols)

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计字典
        """
        return {
            'running': self._running,
            'save_count': self._save_count,
            'error_count': self._error_count,
            'queue_size': self._queue.qsize(),
            'base_dir': str(self.base_dir)
        }

    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        清理旧数据

        Args:
            days_to_keep: 保留天数
        """
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")

        for symbol_dir in self.base_dir.iterdir():
            if not symbol_dir.is_dir():
                continue

            for date_dir in symbol_dir.iterdir():
                if date_dir.is_dir() and date_dir.name < cutoff:
                    # 删除旧目录
                    import shutil
                    shutil.rmtree(date_dir)
                    logger.info(f"[ContextManager] 清理旧数据: {date_dir}")
