"""备选标的路由模块，提供筛选、排序、分页接口"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, get_db
from models.stock import Stock_M
from schemas.stock_m import StockMResponse

router = APIRouter(prefix="/api/stock-m", tags=["备选标的"])


def init_mock_data():
    """初始化示例数据，仅数据库为空时执行"""
    db = SessionLocal()
    try:
        if db.query(Stock_M).count() == 0:
            mock_data = [
                Stock_M(
                    code_date="2026-06-22",
                    code="600519",
                    name="贵州茅台",
                    change_rate="+3.25%",
                    rq_margin_trading="1250.36万",
                    major_flow="2.8亿",
                    extra_large_flow="3.1亿",
                    large_flow="-0.3亿",
                    code_type="突破",
                    flag="价值成长",
                ),
                Stock_M(
                    code_date="2026-06-22",
                    code="601318",
                    name="中国平安",
                    change_rate="+1.80%",
                    rq_margin_trading="850.20万",
                    major_flow="1.5亿",
                    extra_large_flow="1.8亿",
                    large_flow="-0.3亿",
                    code_type="低吸",
                    flag="低估值蓝筹",
                ),
                Stock_M(
                    code_date="2026-06-22",
                    code="000858",
                    name="五粮液",
                    change_rate="-0.50%",
                    rq_margin_trading="-230.15万",
                    major_flow="-0.6亿",
                    extra_large_flow="-0.8亿",
                    large_flow="0.2亿",
                    code_type="上影线",
                    flag="消费龙头",
                ),
                Stock_M(
                    code_date="2026-06-21",
                    code="600036",
                    name="招商银行",
                    change_rate="+2.10%",
                    rq_margin_trading="680.90万",
                    major_flow="1.2亿",
                    extra_large_flow="1.5亿",
                    large_flow="-0.3亿",
                    code_type="突破",
                    flag="低估值蓝筹",
                ),
                Stock_M(
                    code_date="2026-06-21",
                    code="601888",
                    name="中国中免",
                    change_rate="+3.20%",
                    rq_margin_trading="420.80万",
                    major_flow="0.9亿",
                    extra_large_flow="1.1亿",
                    large_flow="-0.2亿",
                    code_type="低吸",
                    flag="消费龙头",
                ),
            ]
            db.add_all(mock_data)
            db.commit()
    finally:
        db.close()


# GET /api/stock-m/dates - 获取所有可选的选股日期
@router.get("/dates", summary="可选日期列表")
def get_dates(db: Session = Depends(get_db)):
    """返回所有不重复的选股日期，降序排列"""
    dates = (
        db.query(Stock_M.code_date)
        .distinct()
        .order_by(Stock_M.code_date.desc())
        .all()
    )
    return {"code": 200, "data": [d[0] for d in dates], "msg": "ok"}


# GET /api/stock-m/tags - 获取所有可选的标签
@router.get("/tags", summary="可选标签列表")
def get_tags(db: Session = Depends(get_db)):
    """返回所有不重复的标签，按字母排序"""
    tags = (
        db.query(Stock_M.flag)
        .distinct()
        .filter(Stock_M.flag != "", Stock_M.flag.isnot(None))
        .order_by(Stock_M.flag)
        .all()
    )
    return {"code": 200, "data": [t[0] for t in tags], "msg": "ok"}


# GET /api/stock-m - 备选标的列表（支持分页、筛选、排序）
@router.get("", summary="备选标的列表（分页+筛选+排序）")
def get_stock_m(
    code_date: str = Query("", description="按日期筛选，空则取最新日期"),
    flag: str = Query("", description="按标签筛选"),
    code: str = Query("", description="按股票代码搜索"),
    sort_by: str = Query("date", description="排序字段: date|flag"),
    sort_order: str = Query("desc", description="排序方向: asc|desc"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    查询备选标的列表，默认显示最新日期的数据。
    支持按日期、标签、股票代码筛选，按日期或标签排序。
    """
    query = db.query(Stock_M)

    # 未指定日期时取最新日期，否则按指定日期筛选
    if not code_date:
        latest = db.query(func.max(Stock_M.code_date)).scalar()
        if latest:
            query = query.filter(Stock_M.code_date == latest)
    else:
        query = query.filter(Stock_M.code_date == code_date)

    if flag:
        query = query.filter(Stock_M.flag == flag)
    if code:
        query = query.filter(Stock_M.code.like(f"%{code}%"))

    # 动态排序：支持按日期或标签升/降序
    sort_field = {
        "date": Stock_M.code_date,
        "flag": Stock_M.flag,
    }.get(sort_by, Stock_M.code_date)

    query = query.order_by(
        sort_field.desc() if sort_order == "desc" else sort_field.asc()
    )

    total = query.count()
    skip = (page - 1) * size
    rows = query.offset(skip).limit(size).all()

    result = [
        {
            "code_date": r.code_date,
            "code": r.code,
            "name": r.name,
            "change_rate": r.change_rate,
            "rq_margin_trading": r.rq_margin_trading,
            "major_flow": r.major_flow,
            "extra_large_flow": r.extra_large_flow,
            "large_flow": r.large_flow,
            "code_type": r.code_type,
            "flag": r.flag,
        }
        for r in rows
    ]

    return {
        "code": 200,
        "data": {"total": total, "page": page, "size": size, "data": result},
        "msg": "查询成功",
    }
