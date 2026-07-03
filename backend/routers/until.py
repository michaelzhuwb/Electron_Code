from fastapi import APIRouter, Query, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal, get_db
from untils.until import get_margin_flow,get_major_flow,format_money,judge, get_indexflash
from untils.trading_time import get_T

router = APIRouter(prefix="/api/untils", tags=["功能工具"])


def save_market_overview_snapshot(
    ztzs: int, dtzs: int, znum: int, dnum: int, zdfb: list, suggestion: str
):
    """后台任务：保存市场概况快照到数据库"""
    db = SessionLocal()
    from models.stock import MarketOverview
    try:
        record = MarketOverview(
            snapshot_time=datetime.now(),
            ztzs=ztzs, dtzs=dtzs, znum=znum, dnum=dnum,
            zdfb_0=zdfb[0] if len(zdfb) > 0 else 0,
            zdfb_1=zdfb[1] if len(zdfb) > 1 else 0,
            zdfb_2=zdfb[2] if len(zdfb) > 2 else 0,
            zdfb_3=zdfb[3] if len(zdfb) > 3 else 0,
            zdfb_4=zdfb[4] if len(zdfb) > 4 else 0,
            zdfb_5=zdfb[5] if len(zdfb) > 5 else 0,
            zdfb_6=zdfb[6] if len(zdfb) > 6 else 0,
            zdfb_7=zdfb[7] if len(zdfb) > 7 else 0,
            zdfb_8=zdfb[8] if len(zdfb) > 8 else 0,
            zdfb_9=zdfb[9] if len(zdfb) > 9 else 0,
            suggestion=suggestion,
        )
        db.add(record)
        db.commit()
    except Exception as e:
        print(f"保存市场概况快照失败: {e}")
        db.rollback()
    finally:
        db.close()

@router.get("/get_code_margin")
def get_code_margin(
    code:   str= Query("60000", description = '代码'),
    code_date: str = Query("", description="按日期筛选，空则取最新日期"),
    major_cookie:   str = Query("",description="主力资金净流入查询的cookie"),
    db:Session = Depends(get_db)):
    if not code_date:
        code_date = get_T(-1)
        print('查询日期未设置，使用默认日期:',code_date)
    code_date = code_date.replace('-','')
    print('参数',code,code_date)
    df_margin = get_margin_flow(code,code_date)
    df_major = get_major_flow(code,code_date,major_cookie)   
    if type(df_margin) == str:
        margin_flow = {
            "股票名称":df_margin,
            'des':f'{code} 非两融标的',
            '融资净买入':f'非两融标的'
        }
    else:
        margin_flow = df_margin.to_dict()

    major_flow = df_major.to_dict()
    for _ in major_flow:
        if '净额' in _:
            major_flow[_] = format_money(major_flow[_])

    # 合并 margin_flow 和 major_flow 数据用于 judge 判断标签
    merged = {}
    merged.update(margin_flow)
    merged.update(major_flow)
    tag = judge(merged)

    # 处理标签

    res = {
        "code" : 200,
        "data": {
            'margin_flow':margin_flow,
            'major_flow':major_flow,
            'tag': tag
        }
    }
    return res


@router.get("/market_overview")
def market_overview(background_tasks: BackgroundTasks):
    """获取市场概况：涨跌停统计 + 涨跌幅分布"""
    import json
    raw = get_indexflash()
    # print('raw############',raw)
    data = json.loads(raw)

    # 涨跌停统计
    last_zdt = data.get('zdt_data', {}).get('last_zdt', {})
    ztzs = last_zdt.get('ztzs', 0)   # 涨停家数
    dtzs = last_zdt.get('dtzs', 0)   # 跌停家数

    # 涨跌幅分布（10个区间）
    zdfb_info = data.get('zdfb_data', {})
    zdfb = zdfb_info.get('zdfb', [])

    _num = zdfb[1] # -6 - -8 跌幅榜
    op_syx = True   # 上影线
    op_dx = True    # 低吸
    op_fb = True    # 反包追涨
    op_tp = True    # 突破
    if zdfb_info.get('znum', 0) < 1800:
        op_syx = op_fb = False
    suggestion = "当前可用策略："
    if _num >60:
        op_fb = op_tp = op_syx = False  # 只能低吸
        suggestion = '当前只能允许：低吸'
    else:
        open_list = []
        if op_syx:
            open_list.append("上影线")
        if op_dx:
            open_list.append("低吸")
        if op_fb:
            open_list.append("反包追涨")
        if op_tp:
            open_list.append("突破")
        suggestion += "、".join(open_list)

    # 后台异步保存快照（不阻塞响应）
    background_tasks.add_task(
        save_market_overview_snapshot,
        ztzs, dtzs, zdfb_info.get('znum', 0), zdfb_info.get('dnum', 0), zdfb, suggestion
    )

    return {
        "code": 200,
        "data": {
            "zdt_data": {
                "ztzs": ztzs,
                "dtzs": dtzs,
                "znum": zdfb_info.get('znum', 0),
                "dnum": zdfb_info.get('dnum', 0),
            },
            "zdfb_data": zdfb,
            "suggestion":suggestion
        }
    }


@router.get("/market_overview_history")
def get_market_overview_history(
    date: str = Query(None, description="筛选日期，格式 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """查询市场概况历史快照"""
    from models.stock import MarketOverview
    from sqlalchemy import cast, String
    query = db.query(MarketOverview)
    if date:
        query = query.filter(
            cast(MarketOverview.snapshot_time, String).startswith(date)
        )
    total = query.count()
    skip = (page - 1) * size
    records = query.order_by(MarketOverview.snapshot_time.desc()).offset(skip).limit(size).all()

    result = []
    for r in records:
        result.append({
            "id": r.id,
            "snapshot_time": r.snapshot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "ztzs": r.ztzs,
            "dtzs": r.dtzs,
            "znum": r.znum,
            "dnum": r.dnum,
            "zdfb": [r.zdfb_0, r.zdfb_1, r.zdfb_2, r.zdfb_3, r.zdfb_4,
                     r.zdfb_5, r.zdfb_6, r.zdfb_7, r.zdfb_8, r.zdfb_9],
            "suggestion": r.suggestion,
        })

    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "size": size,
            "data": result,
        },
        "msg": "查询成功",
    }