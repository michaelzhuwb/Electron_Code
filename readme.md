使用 electron实现客户端，配合python作为后台提供api，数据库使用sqlite
git config --global --unset http.proxy
git config --global --unset https.proxy

git config --global http.proxy http://127.0.0.1:10809
# https 仓库也要配套设置
git config --global https.proxy http://127.0.0.1:10809

netstat -ano | findstr :18000
taskkill /F /PID 13104
# taskkill /F /IM python.exe