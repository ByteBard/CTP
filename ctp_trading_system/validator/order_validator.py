"""
交易指令验证器
满足评估表错误防范要求：
- 第14项：合约代码错误检查（严重）
- 第15项：委托价格最小变动价位错误检查（严重）
- 第16项：委托数量超出单笔最大委托手数检查（严重）
- 第17项：资金不足错误提示（严重）
- 第18项：持仓不足错误提示（严重）
- 第19项：非交易时间错误提示（严重）
"""
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum

from ..config.settings import Settings
from ..trade_logging.trade_logger import get_logger, TradeLogger


class ValidationErrorType(Enum):
    """验证错误类型"""
    INVALID_INSTRUMENT = "INVALID_INSTRUMENT"           # 合约代码错误
    INVALID_PRICE_TICK = "INVALID_PRICE_TICK"          # 价格最小变动错误
    EXCEED_MAX_VOLUME = "EXCEED_MAX_VOLUME"            # 超出最大委托数量
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"         # 资金不足
    INSUFFICIENT_POSITION = "INSUFFICIENT_POSITION"     # 持仓不足
    NOT_TRADING_TIME = "NOT_TRADING_TIME"              # 非交易时间


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    error_type: Optional[ValidationErrorType] = None
    error_message: str = ""
    details: Optional[dict] = None


@dataclass
class TradingTimeRange:
    """交易时间段"""
    start: time
    end: time
    name: str = ""


class OrderValidator:
    """
    交易指令验证器
    满足评估表第14-19项要求
    """

    # 中国期货交易时间段
    TRADING_TIMES: List[TradingTimeRange] = [
        # 日盘
        TradingTimeRange(time(9, 0), time(10, 15), "日盘上午第一节"),
        TradingTimeRange(time(10, 30), time(11, 30), "日盘上午第二节"),
        TradingTimeRange(time(13, 30), time(15, 0), "日盘下午"),
        # 夜盘（部分品种）
        TradingTimeRange(time(21, 0), time(23, 0), "夜盘第一段"),
        TradingTimeRange(time(23, 0), time(23, 59, 59), "夜盘第二段"),
        TradingTimeRange(time(0, 0), time(2, 30), "夜盘第三段"),
    ]

    def __init__(self, settings: Settings):
        """
        初始化验证器

        Args:
            settings: 系统配置（包含合约信息）
        """
        self.settings = settings
        self.logger: TradeLogger = get_logger()

        # 合约信息缓存
        self._instruments: Dict[str, dict] = settings.instruments

        # 账户信息缓存（需要外部更新）
        self._account: Optional[dict] = None
        self._positions: Dict[str, dict] = {}

        self.logger.log_system("交易指令验证器初始化完成")

    def update_instruments(self, instruments: Dict[str, dict]):
        """更新合约信息"""
        self._instruments = instruments
        self.settings.instruments = instruments

    def update_account(self, account: dict):
        """更新账户信息"""
        self._account = account

    def update_positions(self, positions: Dict[str, dict]):
        """更新持仓信息"""
        self._positions = positions

    # ==================== 完整验证 ====================

    def validate_order(self, instrument_id: str, direction: str, offset: str,
                       price: float, volume: int) -> ValidationResult:
        """
        完整验证交易指令

        Args:
            instrument_id: 合约代码
            direction: 买卖方向 ('0'买, '1'卖)
            offset: 开平标志 ('0'开仓, '1'平仓)
            price: 委托价格
            volume: 委托数量

        Returns:
            验证结果
        """
        # 1. 验证合约代码（第14项）
        result = self.validate_instrument(instrument_id)
        if not result.is_valid:
            return result

        # 获取合约信息
        instrument = self._instruments.get(instrument_id, {})

        # 2. 验证价格（第15项）
        price_tick = instrument.get("price_tick", 0.01)
        result = self.validate_price(price, price_tick)
        if not result.is_valid:
            return result

        # 3. 验证数量（第16项）
        max_volume = instrument.get("max_order_volume", 1000)
        result = self.validate_volume(volume, max_volume)
        if not result.is_valid:
            return result

        # 4. 验证资金/持仓（第17、18项）
        if offset == '0':  # 开仓
            result = self.validate_margin(instrument_id, price, volume)
            if not result.is_valid:
                return result
        else:  # 平仓
            result = self.validate_position(instrument_id, direction, volume)
            if not result.is_valid:
                return result

        # 5. 验证交易时间（第19项）
        result = self.validate_trading_time()
        if not result.is_valid:
            return result

        return ValidationResult(is_valid=True)

    # ==================== 第14项：合约代码检查 ====================

    def validate_instrument(self, instrument_id: str) -> ValidationResult:
        """
        验证合约代码
        满足评估表第14项：合约代码错误检查

        Args:
            instrument_id: 合约代码

        Returns:
            验证结果
        """
        if not instrument_id:
            error_msg = "合约代码不能为空"
            self.logger.log_validation_error(
                validation_type="INSTRUMENT",
                message=error_msg
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_INSTRUMENT,
                error_message=error_msg
            )

        if not self._instruments:
            # 如果没有合约信息，暂时允许通过（由服务器验证）
            self.logger.log_monitor("合约信息未加载，跳过本地验证", {
                "instrument_id": instrument_id
            })
            return ValidationResult(is_valid=True)

        if instrument_id not in self._instruments:
            error_msg = f"合约代码错误：{instrument_id} 不存在"
            self.logger.log_validation_error(
                validation_type="INSTRUMENT",
                message=error_msg,
                instrument_id=instrument_id
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_INSTRUMENT,
                error_message=error_msg,
                details={"instrument_id": instrument_id}
            )

        return ValidationResult(is_valid=True)

    # ==================== 第15项：价格最小变动检查 ====================

    def validate_price(self, price: float, price_tick: float) -> ValidationResult:
        """
        验证委托价格
        满足评估表第15项：委托价格最小变动价位错误检查

        Args:
            price: 委托价格
            price_tick: 最小变动价位

        Returns:
            验证结果
        """
        if price <= 0:
            error_msg = f"委托价格必须大于0，当前价格：{price}"
            self.logger.log_validation_error(
                validation_type="PRICE",
                message=error_msg,
                price=price
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_PRICE_TICK,
                error_message=error_msg
            )

        if price_tick <= 0:
            return ValidationResult(is_valid=True)  # 无法验证

        # 检查价格是否为最小变动价位的整数倍
        remainder = round(price % price_tick, 10)
        if remainder > 1e-9 and abs(remainder - price_tick) > 1e-9:
            error_msg = f"委托价格最小变动价位错误：价格{price}不是最小变动价位{price_tick}的整数倍"
            self.logger.log_validation_error(
                validation_type="PRICE_TICK",
                message=error_msg,
                price=price,
                price_tick=price_tick,
                remainder=remainder
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INVALID_PRICE_TICK,
                error_message=error_msg,
                details={
                    "price": price,
                    "price_tick": price_tick,
                    "remainder": remainder
                }
            )

        return ValidationResult(is_valid=True)

    # ==================== 第16项：委托数量检查 ====================

    def validate_volume(self, volume: int, max_volume: int) -> ValidationResult:
        """
        验证委托数量
        满足评估表第16项：委托数量超出单笔最大委托手数检查

        Args:
            volume: 委托数量
            max_volume: 单笔最大委托手数

        Returns:
            验证结果
        """
        if volume <= 0:
            error_msg = f"委托数量必须大于0，当前数量：{volume}"
            self.logger.log_validation_error(
                validation_type="VOLUME",
                message=error_msg,
                volume=volume
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.EXCEED_MAX_VOLUME,
                error_message=error_msg
            )

        if volume > max_volume:
            error_msg = f"委托数量错误：委托数量{volume}超出单笔最大委托手数{max_volume}"
            self.logger.log_validation_error(
                validation_type="MAX_VOLUME",
                message=error_msg,
                volume=volume,
                max_volume=max_volume
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.EXCEED_MAX_VOLUME,
                error_message=error_msg,
                details={
                    "volume": volume,
                    "max_volume": max_volume
                }
            )

        return ValidationResult(is_valid=True)

    # ==================== 第17项：资金不足检查 ====================

    def validate_margin(self, instrument_id: str, price: float, volume: int,
                        margin_rate: float = 0.1) -> ValidationResult:
        """
        验证资金是否充足
        满足评估表第17项：资金不足错误提示

        Args:
            instrument_id: 合约代码
            price: 委托价格
            volume: 委托数量
            margin_rate: 保证金比例（默认10%）

        Returns:
            验证结果
        """
        if not self._account:
            self.logger.log_monitor("账户信息未加载，跳过资金验证")
            return ValidationResult(is_valid=True)

        available = self._account.get("available", 0)

        # 获取合约乘数
        instrument = self._instruments.get(instrument_id, {})
        multiplier = instrument.get("volume_multiple", 10)

        # 计算所需保证金
        required_margin = price * volume * multiplier * margin_rate

        if required_margin > available:
            error_msg = f"资金不足：开仓所需保证金{required_margin:.2f}，可用资金{available:.2f}"
            self.logger.log_validation_error(
                validation_type="MARGIN",
                message=error_msg,
                required_margin=required_margin,
                available=available,
                instrument_id=instrument_id
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INSUFFICIENT_MARGIN,
                error_message=error_msg,
                details={
                    "required_margin": required_margin,
                    "available": available,
                    "shortfall": required_margin - available
                }
            )

        return ValidationResult(is_valid=True)

    # ==================== 第18项：持仓不足检查 ====================

    def validate_position(self, instrument_id: str, direction: str,
                          volume: int) -> ValidationResult:
        """
        验证持仓是否充足
        满足评估表第18项：持仓不足错误提示

        Args:
            instrument_id: 合约代码
            direction: 买卖方向（平仓方向）
            volume: 委托数量

        Returns:
            验证结果
        """
        if not self._positions:
            self.logger.log_monitor("持仓信息未加载，跳过持仓验证")
            return ValidationResult(is_valid=True)

        # 平仓方向与持仓方向相反
        # 买平 -> 空头持仓，卖平 -> 多头持仓
        if direction == '0':  # 买入（平空仓）
            position_direction = '3'  # 空头
        else:  # 卖出（平多仓）
            position_direction = '2'  # 多头

        position_key = f"{instrument_id}_{position_direction}"
        position = self._positions.get(position_key, {})
        available_position = position.get("position", 0)

        if volume > available_position:
            error_msg = f"持仓不足：平仓数量{volume}，可平持仓{available_position}"
            self.logger.log_validation_error(
                validation_type="POSITION",
                message=error_msg,
                volume=volume,
                available_position=available_position,
                instrument_id=instrument_id
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.INSUFFICIENT_POSITION,
                error_message=error_msg,
                details={
                    "volume": volume,
                    "available_position": available_position,
                    "instrument_id": instrument_id
                }
            )

        return ValidationResult(is_valid=True)

    # ==================== 第19项：交易时间检查 ====================

    def validate_trading_time(self, check_time: Optional[datetime] = None) -> ValidationResult:
        """
        验证是否在交易时间内
        满足评估表第19项：非交易时间错误提示

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            验证结果
        """
        if check_time is None:
            check_time = datetime.now()

        current_time = check_time.time()
        weekday = check_time.weekday()

        # 周末不交易
        if weekday >= 5:  # 周六、周日
            error_msg = f"非交易时间：当前为周末（周{weekday + 1}）"
            self.logger.log_validation_error(
                validation_type="TRADING_TIME",
                message=error_msg,
                weekday=weekday
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.NOT_TRADING_TIME,
                error_message=error_msg
            )

        # 检查是否在交易时间段内
        is_trading_time = False
        for time_range in self.TRADING_TIMES:
            if time_range.start <= current_time <= time_range.end:
                is_trading_time = True
                break

        if not is_trading_time:
            error_msg = f"非交易时间：当前时间{current_time.strftime('%H:%M:%S')}不在交易时段内"
            self.logger.log_validation_error(
                validation_type="TRADING_TIME",
                message=error_msg,
                current_time=current_time.strftime('%H:%M:%S')
            )
            return ValidationResult(
                is_valid=False,
                error_type=ValidationErrorType.NOT_TRADING_TIME,
                error_message=error_msg,
                details={
                    "current_time": current_time.strftime('%H:%M:%S'),
                    "trading_times": [
                        f"{tr.start.strftime('%H:%M')}-{tr.end.strftime('%H:%M')}"
                        for tr in self.TRADING_TIMES
                    ]
                }
            )

        return ValidationResult(is_valid=True)

    # ==================== 工具方法 ====================

    def get_instrument_info(self, instrument_id: str) -> Optional[dict]:
        """获取合约信息"""
        return self._instruments.get(instrument_id)

    def get_all_instruments(self) -> Dict[str, dict]:
        """获取所有合约"""
        return self._instruments

    def is_trading_time(self) -> bool:
        """是否在交易时间"""
        result = self.validate_trading_time()
        return result.is_valid

    def get_next_trading_time(self) -> Optional[TradingTimeRange]:
        """获取下一个交易时间段"""
        current_time = datetime.now().time()

        for time_range in self.TRADING_TIMES:
            if time_range.start > current_time:
                return time_range

        # 如果当天没有更多交易时间，返回第一个时段（明天）
        return self.TRADING_TIMES[0] if self.TRADING_TIMES else None
