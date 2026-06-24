import os

class Settings:
    """全局配置类，集中管理后端启动参数和数据库路径"""
    PORT: int = 18000          # 服务端口
    HOST: str = "127.0.0.1"     # 绑定地址（仅本地）
    DEBUG: bool = True          # 调试模式

    # 数据库路径：SQLite 数据库文件存放在 backend/app.db
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"


settings = Settings()
