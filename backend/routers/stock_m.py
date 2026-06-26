"""备选标的路由模块，提供筛选、排序、分页接口"""
from fastapi import APIRouter, Query, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from database import SessionLocal, get_db
from models.stock import Stock_M
from schemas.stock_m import StockMResponse
import pandas as pd
from datetime import datetime
from io import BytesIO
from untils.until import get_margin_flow, get_major_flow, format_money, judge
from untils.trading_time import get_T
from task_manager import create_task, get_task, TaskStatus

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

    # 标签优先级映射：好+→1，好→2，好-→3，中+→4，中→5，中-→6，差→7
    flag_priority = case(
        (Stock_M.flag == '好+', 1),
        (Stock_M.flag == '好',  2),
        (Stock_M.flag == '好-', 3),
        (Stock_M.flag == '中+', 4),
        (Stock_M.flag == '中',  5),
        (Stock_M.flag == '中-', 6),
        (Stock_M.flag == '差',  7),
        else_=99,
    )

    # 动态排序：按日期或按标签优先级
    if sort_by == 'flag':
        # 按标签优先级排序（asc=从优到劣，desc=从劣到优）
        order_col = flag_priority
        query = query.order_by(order_col.asc() if sort_order == 'asc' else order_col.desc())
    elif sort_by == 'date':
        query = query.order_by(
            Stock_M.code_date.desc() if sort_order == 'desc' else Stock_M.code_date.asc()
        )
    else:
        query = query.order_by(Stock_M.code_date.desc())

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


# POST /api/stock-m/upload - 上传 Excel 批量导入备选标的（异步）
@router.post("/upload", summary="上传Excel导入备选标的（异步）")
async def upload_excel(
    file: UploadFile = File(..., description="Excel文件"),
    code_date: str = Query("", description="选股日期，空则用上一个交易日"),
):
    """
    读取 Excel 文件，第一列为股票代码。
    其他列数据通过 get_margin_flow + get_major_flow + judge 自动获取并填充。
    同一条记录（code_date+code）已存在时更新，不存在时新增。
    """
    if not code_date:
        code_date = get_T(-1)
        code_date = f'{code_date[:4]}-{code_date[4:6]}-{code_date[6:]}'

    # 读取文件内容
    content = await file.read()

    try:
        df = pd.read_csv(BytesIO(content), sep="\t", encoding="gb2312")
    except Exception:
        try:
            df = pd.read_csv(BytesIO(content), sep="\t", encoding="utf-8")
        except Exception:
            try:
                df = pd.read_excel(BytesIO(content), engine="openpyxl")
            except Exception:
                df = pd.read_excel(BytesIO(content), engine="xlrd")
    df.columns = df.columns.str.strip()

    # 识别代码列
    code_col = None
    for col in df.columns:
        if col in ('代码', '股票代码', 'code'):
            code_col = col
            break
    if not code_col or code_col not in df.columns:
        return {"code": 400, "data": None, "msg": "Excel中未找到'代码'列"}

    codes = df[code_col].dropna().astype(str).str.strip().tolist()

    def normalize_code(s: str) -> str:
        return s.upper().replace('SH', '').replace('SZ', '').replace('BJ', '')

    # 创建任务并立即返回 task_id
    task = create_task(f"导入备选标的 ({len(codes)} 条)")
    task.update(status=TaskStatus.RUNNING, total=len(codes))
    task_id = task.id

    def do_import():
        """后台异步执行导入（运行在独立线程）"""
        from task_manager import TaskStatus
        db2 = SessionLocal()
        inserted = updated = failed = 0
        try:
            for i, raw_code in enumerate(codes):
                if not raw_code:
                    continue
                code = normalize_code(raw_code)
                if not code:
                    continue
                try:
                    m_date = code_date.replace('-', '')
                    df_margin = get_margin_flow(code, m_date)
                    df_major = get_major_flow(code, m_date, '')

                    if df_margin is None or isinstance(df_margin, str):
                        margin_dict = {}
                    else:
                        margin_dict = df_margin.to_dict()

                    major_dict = df_major.to_dict() if df_major is not None else {}
                    for k in major_dict:
                        if '净额' in k:
                            major_dict[k] = format_money(major_dict[k])

                    merged = {}
                    merged.update(margin_dict)
                    merged.update(major_dict)
                    tag = judge(merged)

                    def get_val(d, key):
                        v = d.get(key, None) if isinstance(d, dict) else getattr(d, key, None)
                        if v is None:
                            return ''
                        if isinstance(v, float) and pd.isna(v):
                            return ''
                        return str(v).strip()

                    name_val = get_val(margin_dict, '股票名称')
                    chg_val = get_val(major_dict, '涨跌幅')
                    major_val = get_val(major_dict, '主力净流入-净额')
                    extra_val = get_val(major_dict, '超大单净流入-净额')
                    large_val = get_val(major_dict, '大单净流入-净额')
                    rq_val = get_val(margin_dict, '融资净买入')

                    existing = db2.query(Stock_M).filter(
                        Stock_M.code_date == code_date,
                        Stock_M.code == code,
                    ).first()

                    data = {
                        'code_date': code_date,
                        'code': code,
                        'name': name_val,
                        'change_rate': chg_val,
                        'rq_margin_trading': rq_val,
                        'major_flow': major_val,
                        'extra_large_flow': extra_val,
                        'large_flow': large_val,
                        'code_type': '其他',
                        'flag': tag,
                    }

                    if existing:
                        for key, value in data.items():
                            setattr(existing, key, value)
                        updated += 1
                    else:
                        db2.add(Stock_M(**data))
                        inserted += 1
                except Exception as e:
                    print(f"处理代码 {code} 失败: {e}")
                    failed += 1

                # 更新进度
                task.update(
                    progress=int((i + 1) / len(codes) * 100),
                    current=i + 1,
                )

            db2.commit()
            task.update(
                status=TaskStatus.DONE,
                progress=100,
                result={"inserted": inserted, "updated": updated, "failed": failed,
                        "total": inserted + updated, "msg": f"新增 {inserted} 条，更新 {updated} 条，失败 {failed} 条"},
            )
        except Exception as e:
            db2.rollback()
            task.update(status=TaskStatus.FAILED, error=str(e))
        finally:
            db2.close()

    # 启动后台任务（独立线程，不随请求结束而取消）
    import threading
    threading.Thread(target=do_import, daemon=True).start()

    return {"code": 200, "data": {"task_id": task_id}, "msg": "任务已启动"}


# GET /api/stock-m/task/{task_id} - 查询任务状态
@router.get("/task/{task_id}", summary="查询导入任务状态")
def get_upload_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return {"code": 404, "data": None, "msg": "任务不存在"}
    return {"code": 200, "data": task.to_dict(), "msg": "ok"}


# PATCH /api/stock-m/update - 更新备选标的的标签和形态
@router.patch("/update", summary="更新标签/形态")
def update_stock_m(
    code_date: str = Query(..., description="选股日期"),
    code: str = Query(..., description="股票代码"),
    flag: str = Query("", description="标签，留空则不更新"),
    code_type: str = Query("", description="形态，留空则不更新"),
    db: Session = Depends(get_db),
):
    record = db.query(Stock_M).filter(
        Stock_M.code_date == code_date,
        Stock_M.code == code,
    ).first()
    if not record:
        return {"code": 404, "data": None, "msg": "记录不存在"}
    if flag is not None:
        record.flag = flag
    if code_type is not None:
        record.code_type = code_type
    db.commit()
    return {"code": 200, "data": {"flag": record.flag, "code_type": record.code_type}, "msg": "更新成功"}


# POST /api/stock-m/save - 保存单条数据到备选标的（用于查询历史入库）
@router.post("/save", summary="保存查询结果到备选标的")
def save_to_stock_m(
    code_date: str = Query(..., description="选股日期"),
    code: str = Query(..., description="股票代码"),
    name: str = Query("", description="股票名称"),
    change_rate: str = Query("", description="涨跌幅"),
    major_flow: str = Query("", description="主力净流入-净额"),
    extra_large_flow: str = Query("", description="超大单净流入-净额"),
    large_flow: str = Query("", description="大单净流入-净额"),
    rq_margin_trading: str = Query("", description="融资净买入"),
    flag: str = Query("", description="标签"),
    code_type: str = Query("其他", description="形态"),
    db: Session = Depends(get_db),
):
    existing = db.query(Stock_M).filter(
        Stock_M.code_date == code_date,
        Stock_M.code == code,
    ).first()
    if existing:
        for key, value in {
            'code_date': code_date, 'code': code, 'name': name,
            'change_rate': change_rate, 'rq_margin_trading': rq_margin_trading,
            'major_flow': major_flow, 'extra_large_flow': extra_large_flow,
            'large_flow': large_flow, 'code_type': code_type, 'flag': flag,
        }.items():
            setattr(existing, key, value)
        db.commit()
        return {"code": 200, "data": None, "msg": "已更新"}
    db.add(Stock_M(
        code_date=code_date, code=code, name=name,
        change_rate=change_rate, rq_margin_trading=rq_margin_trading,
        major_flow=major_flow, extra_large_flow=extra_large_flow,
        large_flow=large_flow, code_type=code_type, flag=flag,
    ))
    db.commit()
    return {"code": 200, "data": None, "msg": "已入库"}


# DELETE /api/stock-m/{code_date}/{code} - 删除备选标的记录
@router.delete("/{code_date}/{code}", summary="删除备选标的记录")
def delete_stock_m(code_date: str, code: str, db: Session = Depends(get_db)):
    record = db.query(Stock_M).filter(
        Stock_M.code_date == code_date,
        Stock_M.code == code,
    ).first()
    if not record:
        return {"code": 404, "data": None, "msg": "记录不存在"}
    db.delete(record)
    db.commit()
    return {"code": 200, "data": None, "msg": "删除成功"}
