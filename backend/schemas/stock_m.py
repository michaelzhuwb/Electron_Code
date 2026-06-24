from pydantic import BaseModel


# 备选标的响应模型，用于 API 返回时序列化
class StockMResponse(BaseModel):
    code_date: str
    code: str
    name: str
    change_rate: str
    rq_margin_trading: str
    major_flow: str
    extra_large_flow: str
    large_flow: str
    code_type: str
    flag: str

    class Config:
        from_attributes = True
