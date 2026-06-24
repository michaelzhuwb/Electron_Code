"""股票路由模块，提供股票列表查询和统计接口"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from models.stock import Stock
from schemas.stock import StockResponse

router = APIRouter(prefix="/api/stocks", tags=["股票"])


def init_mock_data():
    """初始化示例数据，仅数据库为空时执行"""
    db = SessionLocal()
    try:
        if db.query(Stock).count() == 0:
            mock_stocks = [
                Stock(code="600000", name="浦发银行", price=10.5, change_rate=1.2, volume=1200000, turnover=12600.0, high=10.8, low=10.3),
                Stock(code="600036", name="招商银行", price=35.6, change_rate=-0.8, volume=3500000, turnover=124600.0, high=36.2, low=35.1),
                Stock(code="000001", name="平安银行", price=12.3, change_rate=2.5, volume=2100000, turnover=25830.0, high=12.5, low=12.0),
                Stock(code="000002", name="万科A", price=8.9, change_rate=-1.5, volume=890000, turnover=7921.0, high=9.1, low=8.8),
                Stock(code="600519", name="贵州茅台", price=1680.0, change_rate=0.3, volume=120000, turnover=201600.0, high=1690.0, low=1675.0),
                Stock(code="601318", name="中国平安", price=45.2, change_rate=1.8, volume=4200000, turnover=189840.0, high=46.0, low=44.8),
                Stock(code="000858", name="五粮液", price=145.0, change_rate=-0.5, volume=680000, turnover=98600.0, high=147.0, low=144.5),
                Stock(code="600887", name="伊利股份", price=28.5, change_rate=0.7, volume=920000, turnover=26220.0, high=29.0, low=28.2),
                Stock(code="601888", name="中国中免", price=68.0, change_rate=3.2, volume=1500000, turnover=102000.0, high=69.5, low=67.2),
                Stock(code="002475", name="立讯精密", price=32.1, change_rate=-0.9, volume=2300000, turnover=73830.0, high=32.8, low=31.9),
            ]
            db.add_all(mock_stocks)
            db.commit()
    finally:
        db.close()


# GET /api/stocks - 股票列表（分页+模糊搜索）
@router.get("", summary="股票列表（分页）")
def get_stocks(
    code: str = Query("", description="股票代码（模糊搜索）"),
    name: str = Query("", description="股票名称（模糊搜索）"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db)
):
    """查询股票列表，支持按代码和名称模糊搜索，返回分页数据"""
    query = db.query(Stock)
    if code:
        query = query.filter(Stock.code.like(f"%{code}%"))
    if name:
        query = query.filter(Stock.name.like(f"%{name}%"))

    total = query.count()
    skip = (page - 1) * size
    stocks = query.order_by(Stock.id).offset(skip).limit(size).all()

    # StockResponse.model_validate(s)   # .parse_obj()
    result = [
        StockResponse(
            id=s.id,
            code=s.code,
            name=s.name,
            price=round(s.price, 2),
            change_rate=round(s.change_rate, 2),
            volume=s.volume,
            turnover=round(s.turnover, 2),
            high=round(s.high, 2),
            low=round(s.low, 2),
            update_time=s.update_time.strftime("%Y-%m-%d %H:%M:%S") if s.update_time else "",
        )
        for s in stocks
    ]

    return {
        "code": 200,
        "data": {"total": total, "page": page, "size": size, "data": result},
        "msg": "查询成功"
    }


# GET /api/stocks/stats - 股票涨跌统计
@router.get("/stats", summary="股票统计")
def get_stock_stats(db: Session = Depends(get_db)):
    """统计上涨/下跌/平盘数量，以及平均涨跌幅"""
    stocks = db.query(Stock).all()
    if not stocks:
        return {"code": 200, "data": {"total": 0, "rising": 0, "falling": 0, "avgChange": 0}, "msg": "暂无数据"}

    rising = sum(1 for s in stocks if s.change_rate > 0)
    falling = sum(1 for s in stocks if s.change_rate < 0)
    avg = sum(s.change_rate for s in stocks) / len(stocks) if stocks else 0

    return {
        "code": 200,
        "data": {
            "total": len(stocks),
            "rising": rising,
            "falling": falling,
            "avgChange": round(avg, 2),
        },
        "msg": "统计成功"
    }
