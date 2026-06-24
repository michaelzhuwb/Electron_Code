from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings


# 创建数据库引擎，SQLite 需要 check_same_thread=False 允许多线程访问
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
# 创建会话工厂，关闭自动提交和自动刷新
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# ORM 基类，所有模型继承此类
Base = declarative_base()


def get_db():
    """获取数据库会话，退出时自动关闭。用于 FastAPI 依赖注入。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
