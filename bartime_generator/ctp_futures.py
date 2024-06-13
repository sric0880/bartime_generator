import datetime
import logging
from enum import Enum

from bartime_generator.common import *

__all__ = [
    'set_is_trading_day_func',
    'ProductType',
    'get_product_type',
    "get_next_bartime",
]

_microsecond = datetime.timedelta(microseconds=1)

_is_trading_day = None


def set_is_trading_day_func(func):
    global _is_trading_day
    _is_trading_day = func


class ProductType(Enum):
    Commodity = 0  # 大宗商品
    StockIndex = 1  # 股指
    Bonds = 2  # 债券期货


def get_product_type(pid):
    if pid in ['T', 'TS', 'TF', 'TL']:
        return ProductType.Bonds
    elif pid in ['IC', 'IH', 'IF', 'IM']:
        return ProductType.StockIndex
    else:
        return ProductType.Commodity


def get_next_bartime(dt, interval: int, interval_type: IntervalType, market_time, product_type):
    ticktime = dt
    if is_opening_time(
        ticktime, market_time
    ):  # 开盘时间要加一个微小的时间差，以便算入当前的K线
        ticktime += _microsecond
    if interval_type == IntervalType.SECOND:
        return get_next_second_bartime(ticktime, interval)

    elif interval_type == IntervalType.MINUTE:
        if product_type == ProductType.Commodity:
            if interval == 30:
                special_times = (36000, 38700, 40500, 49500, 51300, 53100, 54000)
                _ticktime = get_next_special_time(ticktime, special_times)
                if _ticktime is not None:
                    return _ticktime
            return get_next_minute_bartime(ticktime, interval)
        elif product_type == ProductType.StockIndex:
            return get_next_minute_bartime(ticktime, interval)
        elif product_type == ProductType.Bonds:
            special_times = (54000, 54900)
            _ticktime = get_next_special_time(ticktime, special_times)
            return (
                get_next_minute_bartime(ticktime, interval)
                if _ticktime is None
                else _ticktime
            )

    elif interval_type == IntervalType.HOUR:
        if product_type == ProductType.Commodity:
            special_times = _ctpHourTimes(market_time, interval)
            crossdaytime = _ctpCrossTimes(market_time, interval)
            return get_next_special_time(
                ticktime, special_times, crossdaytime=crossdaytime
            )
        elif product_type == ProductType.StockIndex:
            if interval == 1:
                special_times = (34200, 37800, 41400, 50400, 54000)
            elif interval == 2:
                special_times = (34200, 41400, 54000)
            return get_next_special_time(ticktime, special_times)
        elif product_type == ProductType.Bonds:
            if interval == 1:
                special_times = (34200, 37800, 41400, 50400, 54000, 54900)
            elif interval == 2:
                special_times = (34200, 41400, 54000, 54900)
            return get_next_special_time(ticktime, special_times)

    elif interval_type == IntervalType.DAILY:
        if interval > 1:
            raise ValueError("Day interval only support 1 day")
        if product_type == ProductType.Commodity:
            special_times = (-1, 54000, 140400)
        elif product_type == ProductType.StockIndex:
            special_times = (34200, 54000)
        elif product_type == ProductType.Bonds:
            special_times = (34200, 54900)
        ticktime = get_next_special_time(ticktime, special_times)
        ticktime = time_until_openday(ticktime)
        return ticktime

    elif interval_type == IntervalType.WEEKLY:
        if interval > 1:
            raise ValueError("Week interval only support 1 week")
        if product_type == ProductType.Commodity:
            special_times = (-1, 54000, 140400)
        elif product_type == ProductType.StockIndex:
            special_times = (34200, 54000)
        elif product_type == ProductType.Bonds:
            special_times = (34200, 54900)
        ticktime = get_next_special_time(ticktime, special_times)
        ticktime = time_until_openday(ticktime)
        ticktime = _to_weekend(ticktime)
        return ticktime
    return None


def is_opening_time(tm, open_period):
    total_sec = tm.hour * 3600 + tm.minute * 60 + tm.second + tm.microsecond / 1000000
    for start, _ in open_period:
        if start == total_sec:
            return True
    return False


def get_next_special_time(ticktime, special_times, crossdaytime=0):
    seconds = (
        ticktime.hour * 3600
        + ticktime.minute * 60
        + ticktime.second
        + ticktime.microsecond * 0.000001
    )
    if seconds > special_times[0] and seconds <= special_times[-1]:
        for t in special_times:
            if seconds <= t:
                _t = t
                if t >= 86400:
                    _t = t - 86400
                    ticktime = ticktime + datetime.timedelta(days=1)
                if t == crossdaytime:
                    ticktime = time_until_openday(ticktime)
                h = int(_t / 3600)
                m = int((_t - h * 3600) / 60)
                return ticktime.replace(hour=h, minute=m, second=0, microsecond=0)
    return None


def _to_weekend(ticktime):
    _weekday = ticktime.isocalendar()[2]
    for i in [5, 4, 3, 2, 1]:
        if i == _weekday:
            return ticktime
        else:
            _ticktime = ticktime + datetime.timedelta(days=(i - _weekday))
            if _is_trading_day(_ticktime):
                return _ticktime


def _ctpHourTimes(timeperiod, interval):
    if len(timeperiod) == 3:  # 无夜盘品种
        if interval == 1:
            return (32400, 36000, 40500, 51300, 54000)  # 10:00 11:15 14:15 15:00
        elif interval == 2:
            return (32400, 40500, 54000)  # 11:15 15:00
        elif interval == 3:
            return (32400, 51300, 54000)  # 14:15 15:00
        elif interval == 4:
            return (32400, 54000)  # 15:00
    elif timeperiod[-1][1] == 82800:  # 23:00
        if interval == 1:
            return (
                32400,
                36000,
                40500,
                51300,
                54000,
                79200,
                82800,
            )  # 10:00 11:15 14:15 15:00 22:00 23:00
        elif interval == 2:
            return (32400, 40500, 54000, 82800)  # 11:15 15:00 23:00
        elif interval == 3:
            return (32400, 36000, 54000, 122400)  # 10:00 15:00 (21:00-10:00可能跨天)
        elif interval == 4:
            return (32400, 40500, 54000, 126900)  # 11:15 15:00 (21:00-11:15可能跨天)
    elif timeperiod[-1][1] == 3600:  # 01:00
        if interval == 1:
            return (
                -1,
                3600,
                36000,
                40500,
                51300,
                54000,
                79200,
                82800,
                86400,
            )  # 10:00 11:15 14:15 15:00 22:00 23:00, 00:00 01:00
        elif interval == 2:
            return (-1, 3600, 40500, 54000, 82800, 90000)  # 11:15 15:00 23:00 01:00
        elif interval == 3:
            return (-1, 40500, 54000, 86400)  # 11:15 15:00 00:00 (00:00-11:15可能跨天)
        elif interval == 4:
            return (-1, 3600, 54000, 90000)  # 01:00 15:00
    elif timeperiod[-1][1] == 9000:  # 02:30
        if interval == 1:
            return (
                -1,
                3600,
                7200,
                34200,
                38700,
                49500,
                53100,
                54000,
                79200,
                82800,
                86400,
            )  # 09:30 10:45 13:45 14:45 15:00 22:00 23:00, 00:00 01:00 02:00 (02:00-09:30可能跨天)
        elif interval == 2:
            return (
                -1,
                3600,
                34200,
                49500,
                54000,
                82800,
                90000,
            )  # 09:30 13:45 15:00 23:00 01:00 (01:00-09:30可能跨天)
        elif interval == 3:
            return (
                -1,
                34200,
                53100,
                54000,
                86400,
            )  # 09:30 14:45 15:00 00:00 (00:00-09:30可能跨天)
        elif interval == 4:
            return (
                -1,
                3600,
                49500,
                54000,
                90000,
            )  # 01:00 13:45 15:00 (01:00-13:45可能跨天)


def _ctpCrossTimes(timeperiod, interval):  # 可能跨天的时间段
    if timeperiod[-1][1] == 82800:  # 23:00
        if interval == 3:
            return 122400
        elif interval == 4:
            return 126900
    elif timeperiod[-1][1] == 3600:  # 01:00
        if interval == 3:
            return 40500  # (00:00-11:15可能跨天)
    elif timeperiod[-1][1] == 9000:  # 02:30
        if interval == 4:
            return 49500
        else:
            return 34200
    return 0


def time_until_openday(ticktime):
    count = 0
    while not _is_trading_day(ticktime):
        ticktime = ticktime + datetime.timedelta(days=1)
        count += 1
        if count > 15:
            ticktime = ticktime - datetime.timedelta(days=15)
            logging.error(
                f"bartime_generator: 往后推15天也没有交易日，交易日历没更新，请及时更新"
            )
            break
    return ticktime
