import requests
from lxml import etree
import  pandas as pd
from datetime import datetime, timedelta
import time
from .trading_time import get_T



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
    df.index = df['交易时间'].str.replace('-','',regex=False)
    df['代码'] = code
    if df.empty:
        return None
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


def main():
    pass

if __name__ == '__main__':
    main()