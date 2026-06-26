import requests
from lxml import etree
import  pandas as pd
from datetime import datetime, timedelta
import time
from .trading_time import get_T
from selenium import webdriver

margin_headers = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'Accept-Language': 'zh-CN,zh;q=0.9',
  'Cache-Control': 'max-age=0',
  'Connection': 'keep-alive',
  'If-None-Match': '"6a3c7087-1b5e0"',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-User': '?1',
  'Upgrade-Insecure-Requests': '1',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
  'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"'
}

# 模块级全局 session，后端启动时创建一次，所有请求复用连接池
sess = requests.session()
sess.headers = margin_headers

def get_margin_flow(code='600000',m_date=None):
    # m_date=get_T()    # '%Y%m%d'
    url = f'https://data.10jqka.com.cn/market/rzrqgg/code/{code}/'
    res = sess.get(url=url)
    root = etree.HTML(res.text)
    _name = root.xpath('//h2[@class="icon-table"]/span')[0]
    name = _name.text.strip().split(f'({code})')[-1]
    table = root.xpath('//table[@class="m-table"]')[0]
    head_trs = table.xpath('./thead/tr')
    row_tr0,row_tr1 = head_trs
    ths = row_tr0.xpath('./th')
    def __get_attr_value(el,key):
        if key in el.attrib:
            return el.attrib[key]
        else:
            return ''

    head_titles = []
    row2_values = [_.text.strip() for _ in row_tr1.xpath('./th')]
    # 获取列名
    #  序号        交易时间      余额       买入额       偿还额     
    #  融资净买入      余量     卖出量    偿还量   融券净卖出  融资融券余额
    for _th in ths:
        if __get_attr_value(_th,'class') == 'th-col':
            _num = int(__get_attr_value(_th,'colspan'))
            head_titles +=row2_values[:_num]
            row2_values = row2_values[_num:]
        else:
            head_titles.append(_th.text)

    data_tr = table.xpath('./tbody/tr')
    result = [[_td.text.strip() for _td in _tr.xpath('./td')] 
              for _tr in data_tr]
    df = pd.DataFrame(data=result,columns=head_titles)
    df = df[(pd.notna(df['交易时间'])) & (df['交易时间'] != '')]
    if df.empty:
        return name
    df.index = df['交易时间'].str.replace('-','',regex=False)
    df['代码'] = code
    df['股票名称'] = name
    if m_date:
        return df.loc[m_date]
    return df


def get_major_flow(
    code: str = "600094", 
    m_date: str = None,
    cookie = '',
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
    stock = code
    market = "sh" if code.startswith(("5", "6")) else "sz"

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
    if cookie:
        print('### major-cookie',cookie)
        headers['Cookie'] = cookie

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
    temp_df['代码'] = code
    temp_df['日期'] = temp_df['日期'].astype(str)
    temp_df.index = temp_df['日期'].str.replace('-','',regex=False)

    if m_date:
        m_date = m_date.replace('-','')
        return temp_df.loc[m_date]
    return temp_df


def format_money(val):
    abs_val = abs(val)
    if abs_val >= 100000000:
        # 转亿元
        return f"{val / 100000000:.2f}亿"
    else:
        # 转万元
        return f"{val / 10000:.2f}万"

def parse_money(val) -> float:
    """将 '3.48亿'、'-9258.87万' 等字符串转为浮点数（单位：元）"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    try:
        if s.endswith('亿'):
            return float(s[:-1]) * 100000000
        elif s.endswith('万'):
            return float(s[:-1]) * 10000
        else:
            return float(s)
    except:
        return 0.0

    # 5. 标签：涨幅 vs 融资净买入额 背离判断

def judge(row):
    """
    好+	优	✅ 优先加入	涨跌幅>0，融资净买入<-500万，主力净流入>1000万，且放量（量比>1.2）
    好	良	✅ 可以加入	涨跌幅<0，融资净买入>500万，主力净流入>1000万，且跌幅<-3%（明显下跌中的吸筹）
    --- 股价上涨，主力资金净流入大，但融资余额下降，大概率是机构主动买入；
    --- 股价下跌，主力资金净流出大，但融资余额上升，大概率是被套资金被动补仓；

    """
    # 涨跌幅：float 类型
    chg = row.get("涨跌幅")
    if chg is None:
        return "中"
    chg = float(chg)

    # 融资净买入：可能是 float 或 '3.48亿'/'-9258.87万' 字符串，或 format_money 后的字符串
    net_buy_raw = row.get("融资净买入")
    net_buy = parse_money(net_buy_raw)

    # 主力净流入-净额：get_major_flow 返回 float，但经过 format_money 后变为字符串
    zjjll_raw = row.get("主力净流入-净额")
    zjjll = parse_money(zjjll_raw)

    # 超大单净流入-净额
    zjmaxll_raw = row.get("超大单净流入-净额")
    zjmaxll = parse_money(zjmaxll_raw)

    # 大单净流入-净额
    zjdell_raw = row.get("大单净流入-净额")
    zjdell = parse_money(zjdell_raw)

    is_down = chg < 0   # 下跌
    is_up = chg > 0     # 上涨


    if not pd.isna(zjjll) or zjjll_raw is not None:
        zjjll_valid = zjjll_raw is not None

        # 判断主力方向
        main_buy = zjjll > 0   # 主力净流入
        main_sell = zjjll < 0  # 主力净流出
        # 好+：全仓
        # 好：正常三分钟内的2/3，横盘时间超过三分钟的---好+ 满仓
        # 好-：1/2仓 横盘时间三分钟内的---1/3，超过3分钟的1/2，超过10分钟的满仓
        # 中+：1/3仓，属于试错 横盘时间要大于等于三分钟才能买入， 正常情况1/3，横盘时间超过等于10分钟的 1/2仓
        # 中：观望，横盘时间要大于等于三分钟才能买入1/4仓，横盘时间大于等于8分钟才可以买入1/3仓， 拉升好的幅度完美的 1/3仓，(一般是，拉升完美的 倾斜度不会过高，)
        # 其他空仓等待 仓位考虑横盘时间？
        if zjjll_valid:
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
                        return "中+"
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
        if chg is None or net_buy_raw is None:
            return "中"
        if chg < 0 and net_buy > 0:
            return "差"  # 股价跌但融资客在加杠杆买
        elif chg > 0 and net_buy < 0:
            return "中+"  # 股价涨且融资客在撤出 健康上涨
        else:
            return "中"



def get_indexflash_api():
    """获取同花顺市场概况数据：涨跌停统计 + 涨跌幅分布"""
    url = 'https://q.10jqka.com.cn/api.php?t=indexflash&'
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://q.10jqka.com.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    session = requests.Session()
    # 先访问首页种下Cookie，指纹放在get参数
    session.get("https://q.10jqka.com.cn", headers=headers)
    time.sleep(1)
    resp = session.get(url, headers=headers, timeout=10)
    return resp.text

def get_indexflash():
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--no-sandbox')
    # options.add_argument('--window-size=1,1')  # 最小尺寸
    options.add_argument('--window-position=-3000,-3000')  # 移出屏幕
    # options.add_argument('--headless')
    # 无头模式
    # options.add_argument('--headless=new')
    # options.add_argument('--window-size=1920,1080')
    # options.add_argument('--disable-gpu')

#     options.add_experimental_option('excludeSwitches', ['enable-automation'])
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument('--ignore-certificate-errors')
#     options.add_argument('--no-sandbox')
#       options.add_argument('--headless')
#     options.add_argument("window-size=1920x1080")

    # driver = webdriver.Chrome(options=options)
    from rpa_base_lib import driver_manager
    driver = driver_manager.build_chrome_driver_with_opions(options)
    url_api = 'https://q.10jqka.com.cn/api.php?t=indexflash&'
    url_home = 'https://q.10jqka.com.cn/'
    try:
        # 1. 先访问首页种下Cookie
        driver.get(url_home)
        time.sleep(0.5)

        # 2. 访问行情接口
        driver.get(url_api)
        time.sleep(0.5)
        res_text = driver.page_source
        # print('res_text',res_text)
        start = res_text.find('{')
        end = res_text.rfind('}') + 1
        json_raw = res_text[start:end]
        return json_raw
    finally:
        driver.quit()

def main():
    pass

if __name__ == '__main__':
    main()