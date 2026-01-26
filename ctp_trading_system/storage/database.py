"""
交易记录数据库管理
SQLite持久化存储
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import TradeRecord


class TradeDatabase:
    """交易记录数据库管理"""

    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: 数据库文件路径，默认为 ctp_trading_system/data/trades.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "trades.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    global_id TEXT UNIQUE,
                    strategy_name TEXT,
                    config_name TEXT,
                    symbol TEXT,
                    run_id TEXT,

                    signal_datetime TEXT,
                    entry_datetime TEXT,
                    exit_datetime TEXT,
                    signal_timestamp_ms INTEGER,
                    entry_timestamp_ms INTEGER,
                    exit_timestamp_ms INTEGER,

                    direction INTEGER,
                    volume INTEGER,
                    position_state TEXT,
                    hold_duration_seconds REAL,
                    hold_bars INTEGER,
                    hold_ticks INTEGER,

                    signal_price REAL,
                    entry_price REAL,
                    exit_price REAL,
                    highest_price REAL,
                    lowest_price REAL,

                    entry_imb REAL,
                    entry_prob REAL,
                    signal_strength TEXT,
                    entry_depth INTEGER,
                    entry_volatility REAL,
                    entry_rsi REAL,

                    pnl_ticks REAL,
                    gross_pnl_pct REAL,
                    net_pnl_pct REAL,
                    commission REAL,
                    slippage_pct REAL,
                    total_cost_pct REAL,

                    mae_pct REAL,
                    mfe_pct REAL,
                    r_multiple REAL,

                    exit_reason TEXT,
                    final_state TEXT,

                    entry_order_ref TEXT,
                    exit_order_ref TEXT,
                    entry_order_sys_id TEXT,
                    exit_order_sys_id TEXT,

                    l2_snapshot_entry TEXT,
                    l2_snapshot_exit TEXT,
                    extra_data TEXT,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON trades(strategy_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entry_datetime ON trades(entry_datetime)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_run_id ON trades(run_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_global_id ON trades(global_id)')

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def insert_trade(self, trade: TradeRecord) -> int:
        """
        插入交易记录

        Args:
            trade: 交易记录

        Returns:
            插入的记录ID
        """
        data = trade.to_dict()

        # JSON序列化
        for key in ['l2_snapshot_entry', 'l2_snapshot_exit', 'extra_data']:
            if data.get(key):
                data[key] = json.dumps(data[key], ensure_ascii=False)

        # 时间格式化
        for key in ['signal_datetime', 'entry_datetime', 'exit_datetime', 'created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()

        columns = [k for k in data.keys() if k != 'id']
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)

        with self._get_connection() as conn:
            cursor = conn.execute(
                f'INSERT INTO trades ({column_names}) VALUES ({placeholders})',
                [data[k] for k in columns]
            )
            conn.commit()
            return cursor.lastrowid

    def update_trade(self, trade: TradeRecord) -> bool:
        """
        更新交易记录

        Args:
            trade: 交易记录 (需要有id或global_id)

        Returns:
            是否成功
        """
        data = trade.to_dict()

        # JSON序列化
        for key in ['l2_snapshot_entry', 'l2_snapshot_exit', 'extra_data']:
            if data.get(key):
                data[key] = json.dumps(data[key], ensure_ascii=False)

        # 时间格式化
        for key in ['signal_datetime', 'entry_datetime', 'exit_datetime']:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()

        data['updated_at'] = datetime.now().isoformat()

        # 确定更新条件
        if data.get('id'):
            where_clause = 'id = ?'
            where_value = data['id']
        elif data.get('global_id'):
            where_clause = 'global_id = ?'
            where_value = data['global_id']
        else:
            return False

        columns = [k for k in data.keys() if k not in ['id']]
        set_clause = ', '.join([f'{k} = ?' for k in columns])

        with self._get_connection() as conn:
            cursor = conn.execute(
                f'UPDATE trades SET {set_clause} WHERE {where_clause}',
                [data[k] for k in columns] + [where_value]
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_trade_by_id(self, trade_id: int) -> Optional[TradeRecord]:
        """按ID获取交易记录"""
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM trades WHERE id = ?', [trade_id]).fetchone()
            return self._row_to_trade(row) if row else None

    def get_trade_by_global_id(self, global_id: str) -> Optional[TradeRecord]:
        """按全局ID获取交易记录"""
        with self._get_connection() as conn:
            row = conn.execute('SELECT * FROM trades WHERE global_id = ?', [global_id]).fetchone()
            return self._row_to_trade(row) if row else None

    def get_trades_by_strategy(self, strategy_name: str,
                                start_date: str = None,
                                end_date: str = None) -> List[TradeRecord]:
        """
        按策略查询交易记录

        Args:
            strategy_name: 策略名称
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            交易记录列表
        """
        query = 'SELECT * FROM trades WHERE strategy_name = ?'
        params = [strategy_name]

        if start_date:
            query += ' AND entry_datetime >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND entry_datetime <= ?'
            params.append(end_date)

        query += ' ORDER BY entry_datetime'

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_trade(row) for row in rows]

    def get_trades_by_symbol(self, symbol: str,
                              start_date: str = None,
                              end_date: str = None) -> List[TradeRecord]:
        """按合约查询交易记录"""
        query = 'SELECT * FROM trades WHERE symbol = ?'
        params = [symbol]

        if start_date:
            query += ' AND entry_datetime >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND entry_datetime <= ?'
            params.append(end_date)

        query += ' ORDER BY entry_datetime'

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_trade(row) for row in rows]

    def get_trades_by_run_id(self, run_id: str) -> List[TradeRecord]:
        """按运行批次查询交易记录"""
        with self._get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM trades WHERE run_id = ? ORDER BY entry_datetime',
                [run_id]
            ).fetchall()
            return [self._row_to_trade(row) for row in rows]

    def get_daily_summary(self, date: str, strategy_name: str = None) -> Dict[str, Any]:
        """
        获取日统计

        Args:
            date: 日期 (YYYY-MM-DD)
            strategy_name: 策略名称 (可选)

        Returns:
            统计字典
        """
        query = '''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN net_pnl_pct > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(net_pnl_pct) as total_pnl_pct,
                AVG(net_pnl_pct) as avg_pnl_pct,
                MIN(net_pnl_pct) as min_pnl_pct,
                MAX(net_pnl_pct) as max_pnl_pct,
                SUM(commission) as total_commission
            FROM trades
            WHERE date(entry_datetime) = ?
        '''
        params = [date]

        if strategy_name:
            query += ' AND strategy_name = ?'
            params.append(strategy_name)

        with self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            if row:
                return {
                    'total_trades': row['total_trades'] or 0,
                    'winning_trades': row['winning_trades'] or 0,
                    'win_rate': (row['winning_trades'] or 0) / row['total_trades'] if row['total_trades'] else 0,
                    'total_pnl_pct': row['total_pnl_pct'] or 0,
                    'avg_pnl_pct': row['avg_pnl_pct'] or 0,
                    'min_pnl_pct': row['min_pnl_pct'] or 0,
                    'max_pnl_pct': row['max_pnl_pct'] or 0,
                    'total_commission': row['total_commission'] or 0
                }
            return {}

    def get_strategy_summary(self, strategy_name: str) -> Dict[str, Any]:
        """
        获取策略总体统计

        Args:
            strategy_name: 策略名称

        Returns:
            统计字典
        """
        query = '''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN net_pnl_pct > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(net_pnl_pct) as total_pnl_pct,
                AVG(net_pnl_pct) as avg_pnl_pct,
                MIN(net_pnl_pct) as min_pnl_pct,
                MAX(net_pnl_pct) as max_pnl_pct,
                AVG(hold_duration_seconds) as avg_hold_duration,
                MIN(entry_datetime) as first_trade,
                MAX(entry_datetime) as last_trade
            FROM trades
            WHERE strategy_name = ?
        '''

        with self._get_connection() as conn:
            row = conn.execute(query, [strategy_name]).fetchone()
            if row:
                return {
                    'strategy_name': strategy_name,
                    'total_trades': row['total_trades'] or 0,
                    'winning_trades': row['winning_trades'] or 0,
                    'win_rate': (row['winning_trades'] or 0) / row['total_trades'] if row['total_trades'] else 0,
                    'total_pnl_pct': row['total_pnl_pct'] or 0,
                    'avg_pnl_pct': row['avg_pnl_pct'] or 0,
                    'min_pnl_pct': row['min_pnl_pct'] or 0,
                    'max_pnl_pct': row['max_pnl_pct'] or 0,
                    'avg_hold_duration': row['avg_hold_duration'] or 0,
                    'first_trade': row['first_trade'],
                    'last_trade': row['last_trade']
                }
            return {}

    def export_to_csv(self, output_path: str, strategy_name: str = None):
        """
        导出CSV

        Args:
            output_path: 输出文件路径
            strategy_name: 策略名称 (可选)
        """
        import csv

        query = 'SELECT * FROM trades'
        params = []
        if strategy_name:
            query += ' WHERE strategy_name = ?'
            params.append(strategy_name)
        query += ' ORDER BY entry_datetime'

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

            if not rows:
                return

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(rows[0].keys())
                for row in rows:
                    writer.writerow(row)

    def _row_to_trade(self, row: sqlite3.Row) -> TradeRecord:
        """将数据库行转换为TradeRecord"""
        data = dict(row)

        # JSON反序列化
        for key in ['l2_snapshot_entry', 'l2_snapshot_exit', 'extra_data']:
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except:
                    data[key] = None

        # 时间转换
        for key in ['signal_datetime', 'entry_datetime', 'exit_datetime', 'created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except:
                    pass

        return TradeRecord.from_dict(data)

    def delete_trade(self, trade_id: int) -> bool:
        """删除交易记录"""
        with self._get_connection() as conn:
            cursor = conn.execute('DELETE FROM trades WHERE id = ?', [trade_id])
            conn.commit()
            return cursor.rowcount > 0

    def count_trades(self, strategy_name: str = None) -> int:
        """统计交易数量"""
        query = 'SELECT COUNT(*) FROM trades'
        params = []
        if strategy_name:
            query += ' WHERE strategy_name = ?'
            params.append(strategy_name)

        with self._get_connection() as conn:
            return conn.execute(query, params).fetchone()[0]
