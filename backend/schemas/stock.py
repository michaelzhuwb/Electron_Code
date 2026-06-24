from pydantic import BaseModel
from datetime import datetime


# 股票数据响应模型，用于 API 返回时序列化
class StockResponse(BaseModel):
    id: int
    code: str
    name: str
    price: float
    change_rate: float
    volume: int
    turnover: float
    high: float
    low: float
    update_time: str

    class Config:
        from_attributes = True


# 股票查询参数模型
class StockQuery(BaseModel):
    code: str = ""
    name: str = ""
    page: int = 1
    size: int = 10
