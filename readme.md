使用 electron实现客户端，配合python作为后台提供api，数据库使用sqlite
git config --global --unset http.proxy
git config --global --unset https.proxy

# https 仓库也要配套设置
git config --global http.proxy http://127.0.0.1:10809
git config --global https.proxy http://127.0.0.1:10809

# 关闭代理
git config --global --unset http.proxy
git config --global --unset https.proxy

netstat -ano | findstr :18000
taskkill /F /PID 13104
# taskkill /F /IM python.exe

    # 好+：全仓  
    # 好：正常三分钟内的2/3，横盘时间超过三分钟的---好+ 满仓
    # 好-：1/2仓 横盘时间三分钟内的---1/3，超过3分钟的1/2，超过10分钟的满仓
    # 中+：1/3仓，属于试错 横盘时间要大于等于三分钟才能买入， 正常情况1/3，横盘时间超过等于10分钟的 1/2仓
    # 中：观望，横盘时间要大于等于三分钟才能买入1/4仓，横盘时间大于等于8分钟才可以买入1/3仓， 拉升好的幅度完美的 1/3仓，(一般是，拉升完美的 倾斜度不会过高，)
    # 其他空仓等待 仓位考虑横盘时间？