from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from untils.select_code import *
router = APIRouter(prefix="/api/untils", tags=["功能工具"])

@router.get("/get_code")
def get_select_code(db:Session = Depends(get_db)):
    res = {
        "code" : 200,
        "data": {}
    }
    return res