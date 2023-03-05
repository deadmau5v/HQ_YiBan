# 湖汽易班自动打卡
- 环境 Python36
    -  requests
    -  BeautifulSoup
    -  Crypto
# 特点
- 用 requests 请求 速度很快
- 打卡日志发到邮箱
- 记录报错步骤
- 多线程
- 自动获取上次打卡信息
- 通过湖汽官网`CAS统一登录` `*不需要易班手机号和密码*`
- 只需要学号和身份证后六位
# 如何使用
- 下载此库压缩包 解压到某目录
- 安装 python3.6 + 
- 安装 Crypto 模块
- 安装 requests 模块
- 安装 bs4 模块
- 安装 pandas 模块
- 将学号身份证填入到data.csv里
- python3 /your/path/main2.py
- 用各种方法定时执行 例如云函数 宝塔定时任务等
