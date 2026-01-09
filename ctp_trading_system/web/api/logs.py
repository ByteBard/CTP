"""
日志管理 API
满足评估表第25项：日志记录功能
"""
import os
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..app import get_trading_system
from ..websocket import get_ws_manager

router = APIRouter()


# ==================== 请求/响应模型 ====================

class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str
    level: str
    type: str
    message: str
    data: Optional[dict] = None


class LogsResponse(BaseModel):
    """日志响应"""
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int


# ==================== API端点 ====================

@router.get("/")
async def get_logs(
    log_type: Optional[str] = None,
    level: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    获取日志
    评估表第25项：日志记录功能

    参数:
    - log_type: 日志类型 (TRADE, SYSTEM, MONITOR, ERROR)
    - level: 日志级别 (INFO, WARNING, ERROR, CRITICAL)
    - page: 页码
    - page_size: 每页条数
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    """
    system = get_trading_system()

    try:
        # 获取日志目录
        log_dir = system.settings.log.log_dir

        # 读取日志文件
        logs = []

        # 确定要读取的日期范围
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = date.today()

        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = date.today()

        # 遍历日期范围内的日志文件
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")

            # 读取各类型日志
            log_types = ["trade", "system", "monitor", "error"]
            if log_type:
                log_types = [log_type.lower()]

            for lt in log_types:
                log_file = os.path.join(log_dir, f"{lt}_{date_str}.log")
                if os.path.exists(log_file):
                    logs.extend(_parse_log_file(log_file, lt.upper(), level))

            current = date.fromordinal(current.toordinal() + 1)

        # 排序（最新的在前）
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        # 分页
        total = len(logs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_logs = logs[start_idx:end_idx]

        return {
            "logs": paged_logs,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_logs(
    log_type: Optional[str] = None,
    log_date: Optional[str] = None
):
    """
    导出日志文件
    评估表第25项：日志记录功能
    """
    system = get_trading_system()

    try:
        log_dir = system.settings.log.log_dir
        target_date = log_date or date.today().strftime("%Y-%m-%d")

        # 确定文件名
        if log_type:
            filename = f"{log_type.lower()}_{target_date}.log"
        else:
            filename = f"all_{target_date}.log"

        file_path = os.path.join(log_dir, filename)

        # 如果请求所有日志，需要合并
        if not log_type:
            # 创建临时合并文件
            merged_content = []
            for lt in ["trade", "system", "monitor", "error"]:
                lt_file = os.path.join(log_dir, f"{lt}_{target_date}.log")
                if os.path.exists(lt_file):
                    with open(lt_file, 'r', encoding='utf-8') as f:
                        merged_content.append(f"=== {lt.upper()} LOGS ===\n")
                        merged_content.append(f.read())
                        merged_content.append("\n\n")

            if merged_content:
                # 写入临时文件
                temp_file = os.path.join(log_dir, filename)
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.writelines(merged_content)
                file_path = temp_file
            else:
                raise HTTPException(status_code=404, detail="没有找到日志文件")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="日志文件不存在")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/plain"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_log_types():
    """获取日志类型列表"""
    return {
        "types": [
            {"value": "TRADE", "label": "交易日志"},
            {"value": "SYSTEM", "label": "系统日志"},
            {"value": "MONITOR", "label": "监测日志"},
            {"value": "ERROR", "label": "错误日志"}
        ]
    }


@router.get("/levels")
async def get_log_levels():
    """获取日志级别列表"""
    return {
        "levels": [
            {"value": "INFO", "label": "信息"},
            {"value": "WARNING", "label": "警告"},
            {"value": "ERROR", "label": "错误"},
            {"value": "CRITICAL", "label": "严重"}
        ]
    }


@router.get("/realtime")
async def get_realtime_logs(limit: int = 50):
    """获取实时日志（最近N条）"""
    system = get_trading_system()

    try:
        log_dir = system.settings.log.log_dir
        today = date.today().strftime("%Y-%m-%d")

        all_logs = []

        for lt in ["trade", "system", "monitor", "error"]:
            log_file = os.path.join(log_dir, f"{lt}_{today}.log")
            if os.path.exists(log_file):
                all_logs.extend(_parse_log_file(log_file, lt.upper(), None))

        # 排序并限制数量
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return {"logs": all_logs[:limit]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_log_file(file_path: str, log_type: str, level_filter: Optional[str]) -> List[dict]:
    """解析日志文件"""
    logs = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 尝试解析JSON格式日志
                try:
                    import json
                    log_entry = json.loads(line)
                    entry = {
                        "timestamp": log_entry.get("timestamp", ""),
                        "level": log_entry.get("level", "INFO"),
                        "type": log_type,
                        "message": log_entry.get("message", line),
                        "data": log_entry.get("data")
                    }
                except json.JSONDecodeError:
                    # 解析普通文本格式
                    entry = {
                        "timestamp": "",
                        "level": "INFO",
                        "type": log_type,
                        "message": line,
                        "data": None
                    }

                    # 尝试从行中提取时间戳和级别
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            entry["timestamp"] = parts[0].strip()
                            entry["level"] = parts[1].strip()
                            entry["message"] = "|".join(parts[2:]).strip()

                # 应用级别过滤
                if level_filter and entry["level"] != level_filter:
                    continue

                logs.append(entry)

    except Exception:
        pass

    return logs
