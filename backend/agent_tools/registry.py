"""
AI 助手工具注册模块
================================
每个工具包含：
  - name: 工具名称（LLM 用来识别调用哪个工具）
  - description: 工具描述（LLM 根据此判断何时调用）
  - parameters: 参数定义（JSON Schema 格式，LLM 从中提取参数）

执行函数通过 TOOLS_REGISTRY 的 execute_fn 关联到具体的后端调用。
"""

from typing import Callable, Any, Dict


class ToolDefinition:
    """单个工具的完整定义"""
    def __init__(self, name: str, description: str, parameters: dict, execute_fn: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.execute_fn = execute_fn

    def to_openai_format(self) -> dict:
        """转换为 OpenAI/DeepSeek 的 tool 定义格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ============================================================
# 工具实现函数
# 每个函数接收 LLM 提取的参数，返回字典（会被序列化为 JSON 返回给 LLM）
# ============================================================

def _query_margin_data(params: dict) -> dict:
    """查询个股两融 + 主力资金数据"""
    code = params.get("code", "")
    code_date = params.get("code_date", "")

    from untils.until import get_margin_flow, get_major_flow, format_money, judge
    from untils.trading_time import get_T

    if not code_date:
        code_date = get_T(-1)
        code_date = f'{code_date[:4]}-{code_date[4:6]}-{code_date[6:]}'

    code_date_flat = code_date.replace('-', '')
    margin_df = get_margin_flow(code, code_date_flat)
    major_df = get_major_flow(code, code_date_flat, "")

    # 处理非两融标的
    if isinstance(margin_df, str):
        return {
            "status": "warning",
            "message": f"{code} 不是两融标的，{margin_df}",
        }

    margin_dict = margin_df.to_dict() if margin_df is not None else {}
    major_dict = major_df.to_dict() if major_df is not None else {}

    # 格式化资金数据
    for k in major_dict:
        if '净额' in k:
            major_dict[k] = format_money(major_dict[k])

    # 合并并生成标签
    merged = {**margin_dict, **major_dict}
    tag = judge(merged)

    return {
        "status": "success",
        "code": merged.get("代码", code),
        "name": merged.get("股票名称", ""),
        "trade_date": merged.get("交易时间") or merged.get("日期", code_date),
        "close_price": major_dict.get("收盘价", ""),
        "change_rate": major_dict.get("涨跌幅", ""),
        "major_flow": major_dict.get("主力净流入-净额", ""),
        "extra_large_flow": major_dict.get("超大单净流入-净额", ""),
        "large_flow": major_dict.get("大单净流入-净额", ""),
        "margin_net_buy": margin_dict.get("融资净买入", ""),
        "tag": tag,
    }


def _get_market_overview(params: dict) -> dict:
    """获取当前市场概况（涨跌停统计 + 涨跌幅分布 + 策略建议）"""
    import json
    from untils.until import get_indexflash

    try:
        raw = get_indexflash()
        data = json.loads(raw)

        # 涨跌停统计
        last_zdt = data.get('zdt_data', {}).get('last_zdt', {})
        ztzs = last_zdt.get('ztzs', 0)
        dtzs = last_zdt.get('dtzs', 0)

        # 涨跌幅分布（10个区间）
        zdfb_info = data.get('zdfb_data', {})
        zdfb = zdfb_info.get('zdfb', [])

        return {
            "status": "success",
            "zdt_data": {"ztzs": ztzs, "dtzs": dtzs},
            "zdfb_data": zdfb,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _query_stock_m(params: dict) -> dict:
    """查询备选标的列表"""
    flag = params.get("flag", "")
    code = params.get("code", "")

    from database import SessionLocal
    from models.stock import Stock_M
    from sqlalchemy import func

    db = SessionLocal()
    try:
        query = db.query(Stock_M)

        # 默认取最新日期
        if not params.get("code_date"):
            latest = db.query(func.max(Stock_M.code_date)).scalar()
            if latest:
                query = query.filter(Stock_M.code_date == latest)
        else:
            query = query.filter(Stock_M.code_date == params["code_date"])

        if flag:
            query = query.filter(Stock_M.flag == flag)
        if code:
            query = query.filter(Stock_M.code.like(f"%{code}%"))

        # 如果指定日期无数据，回退到最新日期
        if not query.count():
            latest = db.query(func.max(Stock_M.code_date)).scalar()
            if latest:
                query = db.query(Stock_M)
                query = query.filter(Stock_M.code_date == latest)
                if flag:
                    query = query.filter(Stock_M.flag == flag)
                if code:
                    query = query.filter(Stock_M.code.like(f"%{code}%"))

        # 最多返回20条
        rows = query.order_by(Stock_M.code_date.desc()).limit(20).all()
        total = len(rows)

        result = [
            {
                "code_date": r.code_date,
                "code": r.code,
                "name": r.name,
                "change_rate": r.change_rate,
                "major_flow": r.major_flow,
                "margin_net_buy": r.rq_margin_trading,
                "flag": r.flag,
                "code_type": r.code_type,
            }
            for r in rows
        ]

        return {
            "status": "success",
            "total": total,
            "data": result,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _search_web(params: dict) -> dict:
    """
    联网搜索：使用 Tavily API 搜索网络信息
    返回搜索结果列表，每个结果包含标题、内容和 URL
    """
    import requests
    import os

    query = params.get("query", "")
    api_key = os.environ.get("TAVILY_API_KEY", "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")

    try:
        # Tavily 搜索 API，只返回纯文本结果（不包含内容摘要）
        # max_results: 最多返回5条结果
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "query": query,
                "max_results": 5,
                "include_answer": True,  # 返回 AI 生成的摘要
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        data = res.json()

        if data.get("results"):
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:300],  # 截断过长内容
                }
                for r in data["results"]
            ]
            # Tavily 会返回一个 AI 生成的直接回答
            answer = data.get("answer", "")
            return {
                "status": "success",
                "answer": answer,
                "results": results,
            }
        return {"status": "error", "message": "未找到搜索结果"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# 工具注册表：所有可用工具在此注册
# LLM 只能看到在这里注册的工具
# ============================================================

TOOLS_REGISTRY: list[ToolDefinition] = [
    ToolDefinition(
        name="query_margin_data",
        description="查询个股的两融和主力资金数据。当用户想了解某只股票的资金流向、融资买入、主力净流入等情况时使用。",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "股票代码，如 600519、000858",
                },
                "code_date": {
                    "type": "string",
                    "description": "查询日期，格式 YYYY-MM-DD。留空则取上一个交易日。",
                },
            },
            "required": ["code"],
        },
        execute_fn=_query_margin_data,
    ),
    ToolDefinition(
        name="get_market_overview",
        description="获取当前A股市场概况，包括涨跌停统计、涨跌幅分布和策略建议。当用户想了解大盘走势、市场情绪时使用。",
        parameters={
            "type": "object",
            "properties": {},
        },
        execute_fn=_get_market_overview,
    ),
    ToolDefinition(
        name="query_stock_m",
        description="查询备选标的池中的股票列表。支持按标签、股票代码筛选。当用户想查看自己收藏/备选的股票时使用。",
        parameters={
            "type": "object",
            "properties": {
                "flag": {
                    "type": "string",
                    "description": "按标签筛选，如 好、中、差 等",
                },
                "code": {
                    "type": "string",
                    "description": "按股票代码模糊搜索",
                },
                "code_date": {
                    "type": "string",
                    "description": "选股日期，格式 YYYY-MM-DD。留空则取最新。",
                },
            },
        },
        execute_fn=_query_stock_m,
    ),
    ToolDefinition(
        name="search_web",
        description="联网搜索网络信息。当用户询问的新闻、公告、实时数据、市场动态等无法通过本地工具获取时使用此工具。所有股票相关最新消息都用这个。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如「贵州茅台 最新公告」「今日A股 行情分析」",
                },
            },
            "required": ["query"],
        },
        execute_fn=_search_web,
    ),
]


def get_tools_definitions() -> list[dict]:
    """获取所有工具的 OpenAI 格式定义，用于发送给 LLM"""
    return [tool.to_openai_format() for tool in TOOLS_REGISTRY]


def execute_tool(name: str, params: dict) -> dict:
    """
    根据工具名称执行对应的函数。
    如果工具不存在，返回错误信息。
    """
    for tool in TOOLS_REGISTRY:
        if tool.name == name:
            return tool.execute_fn(params)
    return {"status": "error", "message": f"未知工具: {name}"}
