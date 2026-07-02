from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from untils.until import get_margin_flow,get_major_flow,format_money,judge, get_indexflash
from untils.trading_time import get_T

router = APIRouter(prefix="/api/untils", tags=["功能工具"])

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
def market_overview():
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