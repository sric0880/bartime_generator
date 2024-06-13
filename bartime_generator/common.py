import datetime
from enum import Enum


class IntervalType(Enum):
    SECOND = "s"
    MINUTE = "m"
    HOUR = "H"
    DAILY = "D"
    WEEKLY = "W"
    MONTH = "M"
    YEAR = "Y"


def get_next_second_bartime(ticktime, interval):
    if ticktime.microsecond == 0:
        ticktime = ticktime - datetime.timedelta(seconds=1)
    else:
        ticktime = ticktime.replace(microsecond=0)
    while True:
        ticktime = ticktime + datetime.timedelta(seconds=1)
        if ticktime.second % interval != 0:
            return ticktime


def get_next_minute_bartime(ticktime, interval):
    if ticktime.second == 0 and ticktime.microsecond == 0:
        ticktime = ticktime - datetime.timedelta(minutes=1)
    else:
        ticktime = ticktime.replace(second=0, microsecond=0)
    while True:
        ticktime = ticktime + datetime.timedelta(minutes=1)
        if ticktime.minute % interval == 0:
            return ticktime
