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
    """查询个股两融 + 主力资金数据，优先查数据库"""
    code = params.get("code", "")
    code_date = params.get("code_date", "")

    from untils.until import get_margin_flow, get_major_flow, format_money, judge
    from untils.trading_time import get_T
    from database import SessionLocal
    from models.stock import Stock_M

    if not code_date:
        code_date = get_T(-1)
        code_date = f'{code_date[:4]}-{code_date[4:6]}-{code_date[6:]}'

    # ---- 1. 优先查数据库 ----
    db = SessionLocal()
    try:
        row = db.query(Stock_M).filter(
            Stock_M.code_date == code_date,
            Stock_M.code == code,
        ).first()
        if row:
            return {
                "status": "success",
                "code": row.code,
                "name": row.name,
                "trade_date": row.code_date,
                "close_price": "",
                "change_rate": row.change_rate,
                "major_flow": row.major_flow,
                "extra_large_flow": row.extra_large_flow,
                "large_flow": row.large_flow,
                "margin_net_buy": row.rq_margin_trading,
                "tag": row.flag,
                "source": "数据库",
            }
    finally:
        db.close()

    # ---- 2. 数据库没有，再调 API 实时抓取 ----
    code_date_flat = code_date.replace('-', '')

    margin_dict = {}
    major_dict = {}

    try:
        margin_df = get_margin_flow(code, code_date_flat)

        # 处理非两融标的
        if isinstance(margin_df, str):
            return {
                "status": "warning",
                "message": f"{code} 不是两融标的，{margin_df}",
            }

        if margin_df is not None:
            margin_dict = margin_df.to_dict()

        # 校验日期是否匹配
        margin_date_api = str(margin_dict.get('交易时间') or margin_dict.get('日期') or '').replace('-', '')
        if margin_date_api and margin_date_api != code_date_flat:
            print(f"[query_margin_data] margin date mismatch: {margin_date_api} != {code_date_flat}")
            margin_dict = {}
    except Exception as e:
        print(f"[query_margin_data] margin API error: {e}")
        margin_dict = {}

    try:
        major_df = get_major_flow(code, code_date_flat, "")

        if major_df is not None:
            major_dict = major_df.to_dict()

        # 校验日期是否匹配
        major_date_api = str(major_dict.get('日期') or '').replace('-', '')
        if major_date_api and major_date_api != code_date_flat:
            print(f"[query_margin_data] major date mismatch: {major_date_api} != {code_date_flat}")
            major_dict = {}
    except Exception as e:
        print(f"[query_margin_data] major API error: {e}")
        major_dict = {}

    # 日期校验后仍然没有数据，说明当天停牌或数据源异常
    if not margin_dict and not major_dict:
        return {
            "status": "warning",
            "message": f"{code} 在 {code_date} 没有可用数据（可能停牌或数据源未更新）",
            "code": code,
            "trade_date": code_date,
        }

    # 格式化资金数据
    for k in major_dict:
        if '净额' in k:
            major_dict[k] = format_money(major_dict[k])

    # 合并并生成标签
    merged = {**margin_dict, **major_dict}
    tag = judge(merged)

    result = {
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
        "source": "实时抓取",
    }
    return result


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
    # 支持单标签或标签列表
    flags = params.get("flag", "")
    if isinstance(flags, str) and flags:
        flag_list = [f.strip() for f in flags.split(",") if f.strip()]
    elif isinstance(flags, list):
        flag_list = [str(f).strip() for f in flags if str(f).strip()]
    else:
        flag_list = []

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

        # 支持多标签筛选（OR 关系）
        if flag_list:
            query = query.filter(Stock_M.flag.in_(flag_list))
        if code:
            query = query.filter(Stock_M.code.like(f"%{code}%"))

        # 如果指定日期无数据，回退到最新日期
        if not query.count():
            latest = db.query(func.max(Stock_M.code_date)).scalar()
            if latest:
                query = db.query(Stock_M)
                query = query.filter(Stock_M.code_date == latest)
                if flag_list:
                    query = query.filter(Stock_M.flag.in_(flag_list))
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


def _analyze_stock_m(params: dict) -> dict:
    """
    智能选股分析：综合分析备选标的数据
    返回所有备选标的 + 市场概况 + 个股两融数据，供 LLM 排序推荐
    """
    flag = params.get("flag", "")
    code_date = params.get("code_date", "")

    from database import SessionLocal
    from models.stock import Stock_M
    from sqlalchemy import func
    from untils.until import get_indexflash

    import json

    # ---- 1. 获取备选标的列表 ----
    db = SessionLocal()
    try:
        query = db.query(Stock_M)

        # 默认取最新日期
        if not code_date:
            latest = db.query(func.max(Stock_M.code_date)).scalar()
            if latest:
                code_date = latest
                query = query.filter(Stock_M.code_date == latest)
        else:
            query = query.filter(Stock_M.code_date == code_date)

        if flag:
            query = query.filter(Stock_M.flag == flag)

        # 如果无数据，回退到最新日期
        if not query.count():
            latest = db.query(func.max(Stock_M.code_date)).scalar()
            if latest:
                code_date = latest
                query = db.query(Stock_M)
                query = query.filter(Stock_M.code_date == latest)
                if flag:
                    query = query.filter(Stock_M.flag == flag)

        rows = query.order_by(Stock_M.code_date.desc()).limit(30).all()

        stocks = [
            {
                "code": r.code,
                "name": r.name,
                "change_rate": r.change_rate,
                "major_flow": r.major_flow,
                "extra_large_flow": r.extra_large_flow,
                "large_flow": r.large_flow,
                "margin_net_buy": r.rq_margin_trading,
                "flag": r.flag,
                "code_type": r.code_type,
            }
            for r in rows
        ]

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

    # ---- 2. 获取市场概况 ----
    market = {}
    try:
        raw = get_indexflash()
        data = json.loads(raw)
        last_zdt = data.get('zdt_data', {}).get('last_zdt', {})
        zdfb_info = data.get('zdfb_data', {})

        market = {
            "ztzs": last_zdt.get('ztzs', 0),
            "dtzs": last_zdt.get('dtzs', 0),
            "zdfb": zdfb_info.get('zdfb', []),
        }
    except Exception:
        pass

    return {
        "status": "success",
        "date": code_date,
        "total": len(stocks),
        "stocks": stocks,
        "market": market,
    }


def _query_code_recent(params: dict) -> dict:
    """
    查询个股最近N天的两融数据，数据库没有则实时抓取并存入。
    适用于用户要求查某只股票最近几天的数据（如"300620 最近三天"）。
    返回的数据可以直接让 LLM 分析，也可以让 LLM 指导用户入库。
    """
    code = params.get("code", "").upper()
    days = int(params.get("days", 3))  # 默认查最近3天

    if not code:
        return {"status": "error", "message": "请提供股票代码"}

    from untils.until import get_margin_flow, get_major_flow, format_money, judge
    from untils.trading_time import get_T
    from database import SessionLocal
    from models.stock import Stock_M

    # ---- 1. 获取最近 N 个交易日 ----
    trading_dates = []
    for i in range(1, days + 1):
        t = get_T(-i)
        trading_dates.append(f'{t[:4]}-{t[4:6]}-{t[6:]}')

    # ---- 2. 查数据库已有数据（code_date + code 联合唯一） ----
    db = SessionLocal()
    try:
        existing = db.query(Stock_M).filter(
            Stock_M.code_date.in_(trading_dates),
            Stock_M.code == code,
        ).all()
        existing_keys = {(r.code_date, r.code) for r in existing}

        result = [
            {
                "code_date": r.code_date,
                "code": r.code,
                "name": r.name,
                "change_rate": r.change_rate,
                "major_flow": r.major_flow,
                "extra_large_flow": r.extra_large_flow,
                "large_flow": r.large_flow,
                "margin_net_buy": r.rq_margin_trading,
                "flag": r.flag,
                "code_type": r.code_type,
                "source": "数据库",
            }
            for r in existing
        ]
    finally:
        db.close()

    # ---- 3. 缺失的日期实时抓取 ----
    for td in trading_dates:
        if (td, code) in existing_keys:
            continue

        td_flat = td.replace('-', '')
        try:
            margin_df = get_margin_flow(code, td_flat)

            # 非两融标的
            if isinstance(margin_df, str):
                result.append({
                    "code_date": td,
                    "code": code,
                    "name": margin_df,
                    "change_rate": "-",
                    "major_flow": "-",
                    "extra_large_flow": "-",
                    "large_flow": "-",
                    "margin_net_buy": "-",
                    "flag": "-",
                    "code_type": "-",
                    "source": "实时抓取（非两融标的）",
                })
                existing_keys.add((td, code))
                continue

            major_df = get_major_flow(code, td_flat, "")
            margin_dict = margin_df.to_dict() if margin_df is not None else {}
            major_dict = major_df.to_dict() if major_df is not None else {}

            # 校验日期是否匹配，避免数据源返回错误日期（如停牌日、节假日）
            margin_date = str(margin_dict.get('交易时间') or margin_dict.get('日期') or '').replace('-', '')
            major_date = str(major_dict.get('日期') or '').replace('-', '')
            if margin_date and margin_date != td_flat:
                margin_dict = {}
            if major_date and major_date != td_flat:
                major_dict = {}

            # 格式化资金数据
            for k in major_dict:
                if '净额' in k:
                    major_dict[k] = format_money(major_dict[k])

            merged = {**margin_dict, **major_dict}
            tag = judge(merged)

            def get_val(d, key):
                v = d.get(key, None) if isinstance(d, dict) else getattr(d, key, None)
                if v is None:
                    return '-'
                import math
                if isinstance(v, float) and math.isnan(v):
                    return '-'
                return str(v).strip()

            stock_data = {
                "code_date": td,
                "code": code,
                "name": get_val(margin_dict, '股票名称'),
                "change_rate": get_val(major_dict, '涨跌幅'),
                "major_flow": get_val(major_dict, '主力净流入-净额'),
                "extra_large_flow": get_val(major_dict, '超大单净流入-净额'),
                "large_flow": get_val(major_dict, '大单净流入-净额'),
                "margin_net_buy": get_val(margin_dict, '融资净买入'),
                "flag": tag,
                "code_type": "其他",
                "source": "实时抓取",
            }
            result.append(stock_data)

            # 自动入库
            db2 = SessionLocal()
            try:
                existing_row = db2.query(Stock_M).filter(
                    Stock_M.code_date == td,
                    Stock_M.code == code,
                ).first()
                if existing_row:
                    for key, value in stock_data.items():
                        if key != 'source':
                            setattr(existing_row, key, value)
                else:
                    db2.add(Stock_M(
                        code_date=stock_data["code_date"],
                        code=stock_data["code"],
                        name=stock_data["name"],
                        change_rate=stock_data["change_rate"],
                        major_flow=stock_data["major_flow"],
                        extra_large_flow=stock_data["extra_large_flow"],
                        large_flow=stock_data["large_flow"],
                        rq_margin_trading=stock_data["margin_net_buy"],
                        flag=stock_data["flag"],
                        code_type=stock_data["code_type"],
                    ))
                db2.commit()
            except Exception as e:
                db2.rollback()
                print(f"入库失败 {code} {td}: {e}")
            finally:
                db2.close()

        except Exception as e:
            result.append({
                "code_date": td,
                "code": code,
                "name": "查询失败",
                "change_rate": "-",
                "major_flow": "-",
                "extra_large_flow": "-",
                "large_flow": "-",
                "margin_net_buy": "-",
                "flag": "-",
                "code_type": "-",
                "source": f"抓取失败: {str(e)[:50]}",
            })

    # 按日期倒序排列
    result.sort(key=lambda x: x["code_date"], reverse=True)

    # 为每条数据添加中文映射说明，帮助 LLM 正确展示
    data_with_labels = []
    for d in result:
        data_with_labels.append({
            "日期": d["code_date"],
            "股票代码": d["code"],
            "股票名称": d["name"],
            "涨跌幅": d["change_rate"] + "%" if d["change_rate"] != "-" else "-",
            "主力净流入-净额": d["major_flow"],
            "超大单净流入-净额": d["extra_large_flow"],
            "大单净流入-净额": d["large_flow"],
            "融资净买入": d["margin_net_buy"],
            "标签": d["flag"],
            "代码类型": d["code_type"],
            "数据来源": d.get("source", "-"),
        })

    # 生成中文摘要，让 LLM 直接引用，防止 LLM 展示时日期错乱
    summary_lines = []
    for d in result:
        dt = d["code_date"]
        month = int(dt[5:7])
        day = int(dt[8:10])
        date_str = f'{month}月{day}日'
        source = d.get("source", "-")
        summary_lines.append(f"- {date_str}: 涨跌幅={d['change_rate']}%, 主力净流入={d['major_flow']}, 超大单={d['extra_large_flow']}, 大单={d['large_flow']}, 融资净买入={d['margin_net_buy']}, 标签={d['flag']}（来源：{source}）")
    summary = f"{code}最近{days}个交易日数据：\n" + "\n".join(summary_lines)

    # 生成 Markdown 表格，LLM 直接复制即可，避免 LLM 自己造表时改数字
    md_table = "| 日期 | 涨跌幅 | 主力净流入 | 超大单净流入 | 大单净流入 | 融资净买入 | 标签 | 来源 |\n"
    md_table += "|------|--------|-----------|-------------|-----------|-----------|------|------|\n"
    for d in result:
        dt = d["code_date"]
        month = int(dt[5:7])
        day = int(dt[8:10])
        date_str = f'{month}月{day}日'
        source = d.get("source", "-")
        md_table += f"| {date_str} | {d['change_rate']}% | {d['major_flow']} | {d['extra_large_flow']} | {d['large_flow']} | {d['margin_net_buy']} | {d['flag']} | {source} |\n"

    return {
        "status": "success",
        "code": code,
        "dates_queried": trading_dates,
        "total": len(data_with_labels),
        "中文摘要": summary,
        "markdown_table": md_table,
        "data": data_with_labels,
    }


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
        description="查询备选标的池中的股票列表。支持按标签、股票代码筛选。当用户想查看自己收藏/备选的股票时使用。flag 支持多个标签，逗号分隔，如 '好+,好,中+'",
        parameters={
            "type": "object",
            "properties": {
                "flag": {
                    "type": "string",
                    "description": "按标签筛选，如 '好' 或 '好+,好,中+'。多个标签用逗号分隔。留空则不限制。",
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
    ToolDefinition(
        name="analyze_stock_m",
        description="智能选股分析。当用户要求推荐、排序、分析备选标的时使用此工具。它会返回所有备选股票列表（带涨跌幅、资金流向、标签等数据）+ 当前市场概况，让 LLM 综合判断并给出推荐排序和理由。",
        parameters={
            "type": "object",
            "properties": {
                "flag": {
                    "type": "string",
                    "description": "按标签筛选，如 好、中、差 等。留空则不限制。",
                },
                "code_date": {
                    "type": "string",
                    "description": "选股日期，格式 YYYY-MM-DD。留空则取最新。",
                },
            },
        },
        execute_fn=_analyze_stock_m,
    ),
    ToolDefinition(
        name="query_code_recent",
        description="查询某只股票最近几天的两融和主力数据。当用户说「查300620最近三天」或「光库科技最近几天」时使用。此工具会先查数据库，缺失的日期自动实时抓取并存入备选标的库。注意：stock_m 里没有该股票数据时使用此工具，而不是 query_stock_m。",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "股票代码，如 300620、600519",
                },
                "days": {
                    "type": "integer",
                    "description": "查询最近多少天（默认3天）。",
                },
            },
            "required": ["code"],
        },
        execute_fn=_query_code_recent,
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
