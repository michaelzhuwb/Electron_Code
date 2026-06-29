import os

# DeepSeek API 配置
# 从环境变量读取，未设置时抛出明确提示，不硬编码
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    DEEPSEEK_API_KEY = 'xskk-67170386e5b54df5942329f151bad26f'
    # raise RuntimeError("请设置环境变量 DEEPSEEK_API_KEY")
# DeepSeek API 地址（兼容 OpenAI 协议）
DEEPSEEK_API_BASE = "https://api.deepseek.com"
# 默认使用的模型名称
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
