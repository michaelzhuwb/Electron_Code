import datetime
import chinese_calendar
import calendar
import  pandas as pd


# 交易日历
def trading_days(year=None):
    # 默认当前年交易日历
    if not year:
        year = datetime.datetime.now().year
    year = int(year)
    start_time = datetime.date(year, 1, 1)  # 指定开始时间
    endDays = calendar.monthrange(year,12)[-1]
    end_time = datetime.date(year, 12, endDays)   # 指定结束时间
    workdays = pd.DataFrame(chinese_calendar.get_workdays(start_time,end_time)) # 工作日
    workdays = list(map(lambda x:x.strftime("%Y%m%d"),workdays.loc[:,0]))
    trading_days = [_ for _ in  workdays if datetime.date(int(_[:4]), 
                            int(_[4:6]), int(_[6:8])).weekday()<5] 
    return trading_days
# 获取 T+N交易日
def get_T(times=0,date=None):
    # date = datetime.date(2026, 6, 24)

  # 获取t+times t+1 交易日期
    _days = 1 if times>0 else -1
    flag = abs(times)
    if times == 0:
        return datetime.datetime.now().strftime("%Y%m%d")
        raise ValueError("T+N 日不等于0 !")
    if not date:
        date = datetime.datetime.now()
    while flag:
        date += datetime.timedelta(days=_days)
        if date.weekday() < 5:# 属于周一到周五
            workdays = trading_days(date.year)
            if date.strftime("%Y%m%d") in workdays:# 属于工作日
                flag = flag -1
    return date.strftime("%Y%m%d")
