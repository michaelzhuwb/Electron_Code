import akshare as ak
import pandas as pd
from .trading_time import get_T
import time
import requests
import re
from lxml import etree
global ZJJE

def read_stock_list(filepath: str = r"C:\Users\lenovo\Desktop\Table.xls"):
    """
    从 Table.xls 读取股票列表。

    返回:
        DataFrame, 至少包含 股票代码, 股票名称
    """
    df = pd.read_csv(filepath, sep="\t", encoding="gb2312")
    result = pd.DataFrame()
    result["股票代码"] = df.iloc[:, 0].astype(str).str.strip().str[2:].str.zfill(6)
    result["股票名称"] = df.iloc[:, 1].astype(str).str.strip()
    return result


def get_margin_and_flow(date: str, prev_date: str):
    """
    获取两市融资数据，计算融资净买入额。

    参数:
        date:      查询日期，格式 YYYYMMDD
        prev_date: 前一个交易日日期，格式 YYYYMMDD

    返回:
        DataFrame, 列: 股票代码, 股票名称, 融资净买入额, 融资买入额(今日),
                       融资余额(今日), 融资余额(昨日)
    """
    print(f"获取上交所 {date} 两融数据...")
    sse_today = ak.stock_margin_detail_sse(date=date)
    print(f"获取上交所 {prev_date} 两融数据...")
    sse_prev = ak.stock_margin_detail_sse(date=prev_date)

    print(f"获取深交所 {date} 两融数据...")
    sz_today = ak.stock_margin_detail_szse(date=date)
    print(f"获取深交所 {prev_date} 两融数据...")
    sz_prev = ak.stock_margin_detail_szse(date=prev_date)
    
    # 统一列名
    for df in [sse_today, sse_prev, sz_today, sz_prev]:
        if "标的证券代码" in df.columns:
            df.rename(columns={"标的证券代码": "证券代码", "标的证券简称": "证券简称"}, inplace=True)

    # 合并沪深
    today = pd.concat([sse_today, sz_today], ignore_index=True)
    prev = pd.concat([sse_prev, sz_prev], ignore_index=True)

    today = today[["证券代码", "证券简称", "融资买入额", "融资余额"]].copy()
    today.rename(columns={"融资余额": "融资余额(今日)", "融资买入额": "融资买入额(今日)"}, inplace=True)

    prev_balance = prev[["证券代码", "融资余额"]].copy()
    prev_balance.rename(columns={"融资余额": "融资余额(昨日)"}, inplace=True)

    result = today.merge(prev_balance, on="证券代码", how="left")
    result["融资净买入额"] = round((result["融资余额(今日)"] - result["融资余额(昨日)"]) / 10000, 2)
    result["融资买入额(今日)"] = round(result["融资买入额(今日)"] / 10000, 2)
    result["融资余额(今日)"] = round(result["融资余额(今日)"] / 10000, 2)
    result["融资余额(昨日)"] = round(result["融资余额(昨日)"] / 10000, 2)
    result.rename(columns={"证券代码": "股票代码", "证券简称": "股票名称"}, inplace=True)
    result["股票代码"] = result["股票代码"].astype(str).str.zfill(6)

    return result


def get_stock_hist_price(symbol: str, date: str, prev_date: str, market: str = None):
    """
    获取单只股票在指定日期的涨跌幅（使用新浪数据源 stock_zh_a_daily）。
    新浪接口不直接返回涨跌幅，用 (收盘价 - 前收盘价) / 前收盘价 计算。

    参数:
        symbol:    股票代码，如 "002015"
        date:      查询日期，格式 YYYYMMDD
        prev_date: 前一交易日日期，格式 YYYYMMDD
        market:    市场代码，"sh" 或 "sz"，None 则自动判断

    返回:
        dict: {"股票代码": str, "涨跌幅": float}
    """
    if market is None:
        market = "sh" if symbol.startswith(("5", "6")) else "sz"
    sina_symbol = f"{market}{symbol}"

    try:
        # start = (int(prev_date) - 1)  # 多取一天确保有前一交易日数据
        # start_date = str(start).zfill(8)
        start_date = prev_date 
        end_date = date

        df = ak.stock_zh_a_daily(symbol=sina_symbol, start_date=start_date, end_date=end_date, adjust="")
        if df is not None and len(df) >= 2:
            close_today = float(df.iloc[-1]["close"])
            close_prev = float(df.iloc[-2]["close"])
            change_pct = round((close_today - close_prev) / close_prev * 100, 2)
            return {"股票代码": symbol, "涨跌幅": change_pct}
        elif df is not None and len(df) == 1:
            close_today = float(df.iloc[-1]["close"])
            close_prev = float(df.iloc[-1]["open"])
            change_pct = round((close_today - close_prev) / close_prev * 100, 2)
            return {"股票代码": symbol, "涨跌幅": change_pct}
    except Exception as e:
        print(f"  [警告] {symbol} 获取历史数据失败: {e}")
    return {"股票代码": symbol, "涨跌幅": None}

# ak.stock_individual_fund_flow(stock="600094", market="sh")
def stock_individual_fund_flow(
    stock: str = "600094", market: str = "sh"
) -> pd.DataFrame:
    """
    东方财富网-数据中心-资金流向-个股
    https://data.eastmoney.com/zjlx/detail.html
    :param stock: 股票代码
    :type stock: str
    :param market: 股票市场; 上海证券交易所: sh, 深证证券交易所: sz, 北京证券交易所: bj;
    :type market: str
    :return: 近期个股的资金流数据
    :rtype: pandas.DataFrame
    """
    market_map = {"sh": 1, "sz": 0, "bj": 0}
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "lmt": "0",
        "klt": "101",
        "secid": f"{market_map[market]}.{stock}",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "ut": "b2884a393a59ad64002292a3e90d46a5",
        "_": int(time.time() * 1000),
    }
    url = f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=0&klt=101&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf62%2Cf63%2Cf64%2Cf65&ut=b2884a393a59ad64002292a3e90d46a5&secid={params['secid']}&_={params['_']}"


    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    #     "(KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
    #     'Referer': 'https://data.eastmoney.com/',
    #     'Accept': 'application/json, text/plain, */*',
    # }
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://data.eastmoney.com/zjlx/300496.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Cookie': 'qgqp_b_id=910350466b7339e1fdb836fe87548892; st_nvi=4fwQ29fF9Bl17gHnrOaYs6ac2; nid18=0f7cefb64d36a33db2e914d8df66b3d1; nid18_create_time=1777182029600; gviem=Hc3DJD7PMqu3PhJWwDImm5571; gviem_create_time=1777182029600; qRecords=%5B%7B%22name%22%3A%22%u4F0A%u6CF0%uFF22%u80A1%22%2C%22code%22%3A%22SH900948%22%7D%5D; fullscreengg=1; fullscreengg2=1; st_si=91138196802787; st_pvi=68778873072756; st_sp=2026-01-26%2013%3A21%3A10; st_inirUrl=https%3A%2F%2Fguba.eastmoney.com%2F; st_sn=4; st_psi=20260622090033174-113300300815-0791551395; st_asi=delete'
    }

    r = requests.get(url, headers=headers,data={},timeout=10)
    data_json = r.json()
    content_list = data_json["data"]["klines"]
    temp_df = pd.DataFrame([item.split(",") for item in content_list])
    temp_df.columns = [
        "日期",
        "主力净流入-净额",
        "小单净流入-净额",
        "中单净流入-净额",
        "大单净流入-净额",
        "超大单净流入-净额",
        "主力净流入-净占比",
        "小单净流入-净占比",
        "中单净流入-净占比",
        "大单净流入-净占比",
        "超大单净流入-净占比",
        "收盘价",
        "涨跌幅",
        "-",
        "-",
    ]
    temp_df = temp_df[
        [
            "日期",
            "收盘价",
            "涨跌幅",
            "主力净流入-净额",
            "主力净流入-净占比",
            "超大单净流入-净额",
            "超大单净流入-净占比",
            "大单净流入-净额",
            "大单净流入-净占比",
            "中单净流入-净额",
            "中单净流入-净占比",
            "小单净流入-净额",
            "小单净流入-净占比",
        ]
    ]
    temp_df["日期"] = pd.to_datetime(temp_df["日期"], errors="coerce").dt.date
    temp_df["主力净流入-净额"] = pd.to_numeric(
        temp_df["主力净流入-净额"], errors="coerce"
    )
    temp_df["小单净流入-净额"] = pd.to_numeric(
        temp_df["小单净流入-净额"], errors="coerce"
    )
    temp_df["中单净流入-净额"] = pd.to_numeric(
        temp_df["中单净流入-净额"], errors="coerce"
    )
    temp_df["大单净流入-净额"] = pd.to_numeric(
        temp_df["大单净流入-净额"], errors="coerce"
    )
    temp_df["超大单净流入-净额"] = pd.to_numeric(
        temp_df["超大单净流入-净额"], errors="coerce"
    )
    temp_df["主力净流入-净占比"] = pd.to_numeric(
        temp_df["主力净流入-净占比"], errors="coerce"
    )
    temp_df["小单净流入-净占比"] = pd.to_numeric(
        temp_df["小单净流入-净占比"], errors="coerce"
    )
    temp_df["中单净流入-净占比"] = pd.to_numeric(
        temp_df["中单净流入-净占比"], errors="coerce"
    )
    temp_df["大单净流入-净占比"] = pd.to_numeric(
        temp_df["大单净流入-净占比"], errors="coerce"
    )
    temp_df["超大单净流入-净占比"] = pd.to_numeric(
        temp_df["超大单净流入-净占比"], errors="coerce"
    )
    temp_df["收盘价"] = pd.to_numeric(temp_df["收盘价"], errors="coerce")
    temp_df["涨跌幅"] = pd.to_numeric(temp_df["涨跌幅"], errors="coerce")
    return temp_df


def get_main_force_flow_max(stock_code: str, market: str = None):
    # strock_code = re.findall(r'\d+', stock_code)[0]
    # url = f"https://data.eastmoney.com/zjlx/{stock_code}.html"
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    #     "Referer": "https://data.eastmoney.com/",
    #     "Accept": "application/json, text/plain, */*",
    # }
    # res = requests.get(url, headers=headers, timeout=10)
    # content = res.content
    # root = etree.HTML(content)
    # table = root.xpath('//div[@id="table_ls" and @class="dataview"]')[0]
    for _ in range(1,3):
        time.sleep(_*5)
        try:
            # df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
            df = stock_individual_fund_flow(stock=stock_code, market=market)
            break
        except Exception as e:
            pass
            # print(f"  [警告] {stock_code} 获取主力净流入数据失败: {e} 重试 {_}次")
    else:
        print(f"  [错误] {stock_code} 获取主力净流入数据失败，已重试3次，放弃")
        return None

    df['日期'] = df['日期'].apply(lambda x: x.strftime("%Y%m%d"))
    df.index = df['日期']

    _value = df.loc[get_T(-1), '主力净流入-净额'] if not df.empty else None
    _value1 = df.loc[get_T(-1), '超大单净流入-净额'] if not df.empty else None
    _value2 = df.loc[get_T(-1), '大单净流入-净额'] if not df.empty else None


    if _value is not None:
        _value = str(_value)
        _value = round(float(_value.replace("万", "").replace("亿", ""))/10000, 2)  # 转数字并保留两位小数  
    if _value1 is not None:
        _value1 = str(_value1)
        _value1 = round(float(_value1.replace("万", "").replace("亿", ""))/10000, 2)  # 转数字并保留两位小数  
    if _value2 is not None:
        _value2 = str(_value2)
        _value2 = round(float(_value2.replace("万", "").replace("亿", ""))/10000, 2)  # 转数字并保留两位小数  
    return _value,_value1,_value2
    df = df.sort_values(by="日期", ascending=False).reset_index(drop=True)



def combine_all(
    excel_path: str,
    date: str,
    prev_date: str,
    get_flow: bool = False,
):
    """
    从 Excel 读取股票列表，逐只获取涨跌幅、融资数据、主力净流入。

    参数:
        excel_path: 股票列表文件路径
        date:       查询日期，格式 YYYYMMDD
        prev_date:  前一交易日日期，格式 YYYYMMDD
        get_flow:   是否获取主力净流入（逐只查询，较慢）

    返回:
        DataFrame
    """
    global ZJJE
    # df = ak.stock_individual_fund_flow

    # ZJJE = ak.stock_fund_flow_individual(symbol="即时")
    # ZJJE['股票代码'] =  ZJJE['股票代码'].map(lambda x:str(x).zfill(6))
    # 1. 读取股票列表
    print(f"从 {excel_path} 读取股票列表...")
    stock_df = read_stock_list(excel_path)
    print(f"共 {len(stock_df)} 只股票")
    # stock_df = pd.DataFrame()
    # stock_df['股票代码'] = ['600001','301013']
    # stock_df['股票名称'] = ['测试2','测试1']+['测试3']*(len(stock_df)-2)


    # 2. 获取融资数据（沪深全部）
    margin_df = get_margin_and_flow(date, prev_date)

    # 3. 逐只获取指定日期的涨跌幅
    print(f"逐只获取 {date} 涨跌幅...")
    price_records = []
    for _, row in stock_df.iterrows():
        code = row["股票代码"]
        market = "sh" if code.startswith(("5", "6")) else "sz"
        print(f"  查询 {code}...")
        record = get_stock_hist_price(code, date, prev_date, market)
        price_records.append(record)
    price_df = pd.DataFrame(price_records)

    # 4. 合并
    result = stock_df.merge(price_df[["股票代码", "涨跌幅"]], on="股票代码", how="left")
    result = result.merge(
        margin_df[["股票代码", "融资净买入额", "融资买入额(今日)", "融资余额(今日)", "融资余额(昨日)"]],
        on="股票代码",
        how="left",
    )

    # 5. 标签：涨幅 vs 融资净买入额 背离判断
    def judge(row):
        """
            好+	优	✅ 优先加入	涨跌幅>0，融资净买入<-500万，主力净流入>1000万，且放量（量比>1.2）
            好	良	✅ 可以加入	涨跌幅<0，融资净买入>500万，主力净流入>1000万，且跌幅<-3%（明显下跌中的吸筹）


        --- 股价上涨，主力资金净流入大，但融资余额下降，大概率是机构主动买入；
        --- 股价下跌，主力资金净流出大，但融资余额上升，大概率是被套资金被动补仓；
        判断逻辑：
        - 如果涨跌幅 < 0 且 融资净买入额 > 0，主力净流入 > 0 好-    # 融资加仓，主力流入 可能是逢低吸筹，健康
        - 如果涨跌幅 < 0 且 融资净买入额  > 0 ,主力净流入 < 0  差   # 融资加仓但主力流出，可能是主力在抛售但散户在接盘，被动补仓
        - 涨跌幅 < 0 且 融资净买入额 < 0 ，主力净流入 > 0 好+ # 股价跌但融资客在卖出，主力在流入，可能是逢低吸筹 好
        - 涨跌幅 < 0 且 融资净买入额 < 0 且主力净流入 < 0 中 # 股价跌且融资客在卖出，主力在流出，可能是主力在抛售但散户在接盘，健康下跌 中性

        - 涨跌幅 > 0 且 融资净买入额 < 0   主力净流入 > 0 好+ # 股价涨且融资客在撤出，主力在流入，健康上涨
        - 涨跌幅 > 0 且 融资净买入额 < 0   主力净流入 < 0 差 # 股价涨但融资客在撤出，主力在流出，差
        - 涨跌幅 > 0 且 融资净买入额 > 0   主力净流入 > 0 中+ # 股价涨且融资客在加仓，主力在流入，健康上涨 中性偏好
        - 涨跌幅 > 0 且 融资净买入额 > 0   主力净流入 < 0 中- # 股价涨且融资客在加仓，主力在流出，可能是主力在吸筹但散户在卖出，中性偏差
        """

        """
            不存在融资情况：
                A: 主力资金净流入，B：融资净买入额 C：涨跌幅
                C < 0:
                    A > 0 好-    # 股价跌但主力在流入，可能是逢低吸筹，健康
                    A < 0 中     # 股价跌且主力在流出，可能是主力在抛售但散户在接盘，健康下跌 中性
                C > 0:
                    A > 0 中+ # 股价涨且主力在流入，健康上涨 中性偏好
                    A < 0 中- # 股价涨但主力在流出，可能是主力在吸筹但散户在卖出，中性偏差
            不在主力净流入情况：
                C < 0:
                    B < 0 中    # 股价跌但融资客在卖出，中性
                    B > 0 差     # 股价跌但融资客在加仓，可能是被套资金被动补仓，差
                C > 0:
                    B < 0 好     # 股价涨但融资客在撤出
                    B > 0 中    # 股价涨且融资客在加仓，可能是主力在流入，健康上涨 中性
        """


        chg = row.get("涨跌幅")
        if chg is None:
            return "中"
        
        net_buy = row.get("融资净买入额")
        if pd.isna(net_buy):
            net_buy = None
        zjjll = row.get("主力净流入-净额")
        zjmaxll = row.get("超大单净流入-净额")
        zjdell = row.get("大单净流入-净额")

        is_down = chg < 0   # 下跌
        is_up = chg > 0     # 上涨


        if zjjll is not None:
            # zjjll = float(zjjll.replace("万", "").replace("亿", ""))  # 转数字

            # 判断主力方向
            main_buy = zjjll > 0   # 主力净流入
            main_sell = zjjll < 0  # 主力净流出
            # 好+：全仓  
            # 好：正常三分钟内的2/3，横盘时间超过三分钟的---好+ 满仓
            # 好-：1/2仓 横盘时间三分钟内的---1/3，超过3分钟的1/2，超过10分钟的满仓
            # 中+：1/3仓，属于试错 横盘时间要大于等于三分钟才能买入， 正常情况1/3，横盘时间超过等于10分钟的 1/2仓
            # 中：观望，横盘时间要大于等于三分钟才能买入1/4仓，横盘时间大于等于8分钟才可以买入1/3仓， 拉升好的幅度完美的 1/3仓，(一般是，拉升完美的 倾斜度不会过高，)
            # 其他空仓等待 仓位考虑横盘时间？
            if net_buy is not None:
                # 判断融资方向
                financing_buy = net_buy > 0   # 融资净买入
                financing_sell = net_buy < 0  # 融资净卖出
                ## 观察到一种情况胜率较高，股价上涨，融资、主力都是流出的+（缩量？待观察）
                    #这种情况是一般做中线t,资金大起来可以深究
                # 下跌情况
                if is_down:
                    if financing_buy and main_buy:
                        if zjmaxll >0 and zjdell <0:
                            return "好"
                        elif zjmaxll <0 and zjdell >0:
                            return '差'
                        elif zjmaxll >0 and zjdell >0:
                            return "中+"    # 诱多陷阱？ 暂时不确定，得重点观察
                    elif financing_buy and main_sell:
                        if zjmaxll >0 and zjdell <0:
                            return '中+'
                        else:
                            return "差" # 绝对定义 +
                    elif financing_sell and main_buy:
                        if zjmaxll >0 and zjdell >0:
                            return '好' # 同方向
                        elif zjmaxll >0 and zjdell <0:
                            return  '好+'
                        elif zjmaxll <0:
                            return '差'
                    elif financing_sell and main_sell:
                        if zjmaxll >0 and zjdell <0:
                            return '中+'
                        return "中"     # 对于反包的标的应该是中+，突破和上影线标的是中，观察
                        # 上涨情况
                    else:
                        return "中" # 其他情况 归为"中"
                elif is_up:
                    if financing_sell and main_buy:
                        if zjmaxll >0 and zjdell <0:
                            return '好+'
                        elif zjmaxll < 0 and zjdell >0:
                            return '差' # 诱多
                        elif zjmaxll >0 and zjdell >0:
                            return '好'
                        return "好"    # 暂认为是对的，那股票下跌时？ +
                    elif financing_sell and main_sell:
                        # return '中+' # 观察得出的结论，继续测试   # 外围大跌很差，此情况失效
                        if zjmaxll >0 and zjdell <0:
                            if abs(zjmaxll) / abs(zjdell) > 0.62:
                                if abs(zjmaxll) / abs(zjdell)  > 0.68:
                                    return '好+'
                                return '好' # >d 0.65 是好+
                            return "中+"    # 
                        elif zjmaxll <0 and zjdell >0:
                            return '差'
                        return '差'
                    elif financing_buy and main_buy:
                        if zjmaxll >0 and zjdell <0:
                            return '好-'
                        if zjmaxll >0 and zjdell >0:
                            return '中+'    # 同方向
                        if zjmaxll <0 and zjdell  >0:
                            return '差' # 诱多
                        # 针对突破或者上影线反包情况可以, 巨量变为差    # 明牌合力
                        # 低位启动：长期下跌低位企稳 或者横盘突破可以定义为好+，量能巨大定位为差，
                        return "中"    
                    elif financing_buy and main_sell:
                        if zjmaxll >0 and zjdell <0:
                            return '中+'
                        return "差" # +
                else:
                    return "中" # 涨跌幅为0的边界情况，归为"中"
            else:
                # 没有融资数据，单看主力
                if is_down:
                    if main_buy:
                        if zjmaxll >0 and zjdell <0:
                            return "好+"    # 股价跌但主力在流入，可能是逢低吸筹，健康
                        if zjmaxll <0 and  zjdell >0:
                            return '差' # 诱多
                        if zjdell>0 and zjmaxll >0:
                            return '好'    # 同方向
                        return "中+"
                    elif main_sell:
                        if zjmaxll >0 and zjdell <0:
                            return "中+"
                        if zjmaxll <0 and zjdell >0 :
                            return '差'
                        return '中'
                elif is_up:
                    if main_buy:
                        if zjmaxll >0 and zjdell <0:
                            return '好'
                        if zjmaxll <0 and zjdell>0:
                            return '差' # 诱多
                        return "中" # 同方向
                    elif main_sell:
                        if zjmaxll >0 and zjdell <0:
                            return '中+'
                        if zjmaxll <0 and zjdell>0:
                            return '差'
                        return "差" # 都是净流出方向
                else:
                    return "中" # 涨跌幅为0的边界情况，归为"中"
        else:
            # print(f"  [提示] {row['股票代码']} 主力净流入数据缺失，默认视为0")
            if chg is None or net_buy is None:
                return "中"
            if chg < 0 and net_buy > 0:
                return "差"  # 股价跌但融资客在加杠杆买
            elif chg > 0 and net_buy < 0:
                return "中+"  # 股价涨且融资客在撤出 健康上涨
            else:
                return "中"

    # 6. 可选：获取主力净流入（使用 Session 复用连接）
    if get_flow:
        print("获取主力净流入数据（逐只查询，可能需要较长时间）...")
        # flows = []
        # for _, row in result.iterrows():
        #     code = row["股票代码"]
        #     market = "sh" if code.startswith(("5", "6")) else "sz"
        #     flows.append(get_main_force_flow(code, market))
        # result["主力净流入-净额"] = flows
        def get_flow_for_stock(row):
            """为单只股票获取资金流向"""
            code = row["股票代码"]
            market = "sh" if code.startswith(("5", "6")) else "sz"
            try:
                # return get_main_force_flow(code, market)
                return get_main_force_flow_max(code, market)
            except Exception as e:
                print(f"  [错误] 获取 {code} 的主力净流入数据时出错: {e}")
                return None
        result[["主力净流入-净额","超大单净流入-净额","大单净流入-净额"]] = result.apply(get_flow_for_stock, axis=1,result_type="expand")

    else:
        result["主力净流入-净额"] = None
        result["超大单净流入-净额"] = None
        result["大单净流入-净额"] = None

    result["标签"] = result.apply(judge, axis=1)
    # 按标签排序：好 → 中 → 差
    sort_order = {"好+": 0, "好": 0.5, "好-": 1, "中+": 2, "中": 2.5, "中-": 3, "差": 4}
    result["排序"] = result["标签"].map(sort_order)
    result = result.sort_values("排序", ascending=True).drop(columns=["排序"]).reset_index(drop=True)

    cols = ["股票代码", "股票名称", "涨跌幅", "融资净买入额", "主力净流入-净额","超大单净流入-净额","大单净流入-净额"]
    result = result[cols + ["标签"]]
    return result


if __name__ == "__main__":
    df = combine_all(
        excel_path=r"C:\Users\lenovo\Desktop\Table.xls",
        date=get_T(-1),       # 查询日期（融资数据对应的交易日）
        prev_date=get_T(-2),  # 前一交易日
        get_flow=True,        # 设为 True 会逐只查询主力净流入
    )
    print(df.to_string(index=True))
    print(f"\n共 {len(df)} 只股票")
