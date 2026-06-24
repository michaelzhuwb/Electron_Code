"""
FastAPI 主入口
- 注册各业务路由
- 启动时自动创建所有数据库表
- 配置 CORS 允许跨域
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine

# 导入所有模型类，确保 Base.metadata 注册了所有表（建表时需要）
from models.stock import Stock, Stock_M  # noqa: F401

app = FastAPI(
    title="Client App API",
    version="0.1.0",
)

# CORS 中间件，允许所有来源跨域访问（开发环境使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各业务路由
from routers.stock import router as stock_router
from routers.stock import init_mock_data as init_mock_data_stock
from routers.stock_m import router as stock_m_router
from routers.stock_m import init_mock_data as init_mock_data_stock_m
from routers.chat import router as chat_router
from routers.until import router as until_router

app.include_router(stock_router)      # /api/stocks/*  股票查询
app.include_router(stock_m_router)    # /api/stock-m/* 备选标的
app.include_router(chat_router)         # /api/chat/*    AI 助手
app.include_router(until_router)    # 功能工具

# 启动时执行：创建数据库表 + 插入示例数据
@app.on_event("startup")
def startup():
    # 根据所有模型的定义，在数据库中创建对应的表（如不存在）
    Base.metadata.create_all(bind=engine)
    # 插入演示数据
    init_mock_data_stock()
    init_mock_data_stock_m()


# 健康检查接口，用于前端检测后端是否在线
@app.get("/api/health")
def health_check():
    _urls = {
        'major_flow':'https://data.eastmoney.com/zjlx/detail.html', 
        'thx_margin':'https://data.10jqka.com.cn/market/rzrqgg/code/601211/',
        'margin_sh_jys':'https://www.sse.com.cn/market/othersdata/margin/detail/',
        'margin_sz_jys':'https://www.szse.cn/disclosure/margin/margin/index.html',
    }
    return {"code": 200, "data": {"status": "ok","msg": "健康检查成功","urls":_urls}}
