from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from untils.until import get_margin_flow,get_major_flow,format_money
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
    if df_margin is None:
        margin_flow = {
            'des':f'{code} 非两融标的'
        }
    else:
        margin_flow = df_margin.to_dict()

    major_flow = df_major.to_dict()
    for _ in major_flow:
        if '净额' in _:
            major_flow[_] = format_money(major_flow[_])
    res = {
        "code" : 200,
        "data": {
            'margin_flow':margin_flow,
            'major_flow':major_flow
        }
    }
    return res