from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
from datetime import datetime


# 股票实时行情模型
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String, index=True, comment="股票代码")
    name = Column(String, comment="股票名称")
    price = Column(Float, comment="当前价格")
    change_rate = Column(Float, comment="涨跌幅(%)")
    volume = Column(Integer, comment="成交量")
    turnover = Column(Float, comment="成交额(万)")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    update_time = Column(DateTime, default=datetime.now, comment="更新时间")


# 备选标的模型，存储选股分析后的候选股票
class Stock_M(Base):
    __tablename__ = 'stock_m'

    code_date = Column(String(20), primary_key=True, comment="选股日期")
    code = Column(String(20), primary_key=True, comment="股票代码")
    name = Column(String(50), comment="股票名称")
    change_rate = Column(String(30), comment="涨跌幅")
    rq_margin_trading = Column(String(30), comment="融资净买入额")
    major_flow = Column(String(30), comment="主力净流入-净额")
    extra_large_flow = Column(String(30), comment="超大单净流入-净额")
    large_flow = Column(String(30), comment="大单净流入-净额")
    code_type = Column(String(30), default="其他", comment="上影线/低吸/突破/其他")
    flag = Column(String(20), comment="标签")
