from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from untils.select_code import *
router = APIRouter(prefix="/api/untils", tags=["功能工具"])

@router.get("/get_code")
def get_select_code(
    code_date: str = Query("", description="按日期筛选，空则取最新日期"),
    db:Session = Depends(get_db)):
    res = {
        "code" : 200,
        "data": {}
    }
    return res