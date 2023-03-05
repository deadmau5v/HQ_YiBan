# -*- coding: utf-8 -*-
# 重构版

# imports
# 网络模块
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
import requests as req
import pandas as pd

# 内建模块
from threading import Thread
from time import time
from time import sleep
import smtplib
import base64
import bs4

# 内建模块 邮件
import function_tools
import datetime

# configs
# 日志开关
log_switch = True
yiban_ua = "Mozilla/5.0 (Linux; Android 13; 22041216C Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, " \
           "like Gecko) " \
           "Version/4.0 Chrome/110.0.5481.65 Mobile Safari/537.36;webank/h5face;webank/1.0 yiban_android/5.0.15"


# classes


class Student:
    def __init__(self, SID, ID):
        # 可选参数
        self.name = ''

        # 登录信息
        self.SID = SID  # 学号
        self.ID = ID  # 身份证

        self.is_success = False  # 打卡是否成功
        self.msg = ''  # 结果

    def main(self):
        # 获取html内的初始cookie
        cas_html_datas = cas_datas_in_html(self)

        if cas_html_datas:
            html_data = cas_html_datas[0]
            html_cookie = cas_html_datas[1]
        else:
            return False

        # 登录
        cas_cookie = cas_login(self.SID, self.ID, html_cookie, html_data, self)
        if cas_cookie:
            cas_cookie = dict(**html_cookie, **cas_cookie)  # 合并cookies
        else:
            return False

        # 跳转授权
        xggl_url = cas_to_xggl(cas_cookie, self)
        if xggl_url:
            xggl_cookie = xggl_ssid(xggl_url, self)
        else:
            return False

        # 获取打卡界面zzdk_token
        zzdk_token = zzdk_token_get(xggl_cookie, self)
        if not zzdk_token:
            return False

        # 获取上次打卡信息
        last_data = get_last(xggl_cookie)
        if not last_data:
            return False

        zzdk_data = f"""dkdz: 湖南省株洲市天元区天台路60
                        dkdzZb: 113.134,27.8275
                        dkly: baidu
                        xcmTjd: 
                        zzdk_token: {zzdk_token}
                        dkd: 湖南省株洲市
                        jzdValue: 430000,430200,430202
                        jzdSheng.dm: 430000
                        jzdShi.dm: 430200
                        jzdXian.dm: 430202
                        jzdDz: 湖南汽车工程职业学院
                        jzdDz2: {last_data['jzdDz2']}
                        lxdh: {last_data['lxdh']}
                        sfzx: 1
                        sfzxText: 在校
                        twM.dm: 01
                        twMText: [35.0~37.2]正常
                        yczk.dm: 01
                        yczkText: 无症状
                        brStzk.dm: 03
                        brStzkText: 感染已康复
                        brJccry.dm: 01
                        brJccryText: 未接触传染源
                        jrStzk.dm: 01
                        jrStzkText: 尚未感染
                        jrJccry.dm: 01
                        jrJccryText: 未接触传染源
                        xgym: 3
                        xgymText: 已接种加强针
                        hsjc: 0
                        hsjcText: 否
                        zdy1: 0
                        zdy2: 
                        operationType: Create
                        dm: """
        zzdk_data = str2data(zzdk_data)
        if dk(data=zzdk_data, cookie=xggl_cookie, student=self):
            is_success = True
            print(f'{self.name}\t\t' + self.msg)
            return True


# tools
def LOG(*args, **kwargs):
    """详细日志开关"""
    if log_switch:
        print(*args, **kwargs)


def passwd_encode(passwd):
    """密码AES加密"""
    key = 'c6dda3852e2d4be2'.encode()  # 没错是常量 你没看错
    passwd = str(passwd).encode()
    passwd = pad(passwd, 16)
    aes = AES.new(
        key=key,
        mode=AES.MODE_ECB
    )
    encoded = base64.b64encode(aes.encrypt(passwd))
    return encoded


def get_ts():
    """获取时间戳"""
    return str(int(time() * 1000))


def cas_headers(referer: str):
    "cas定制防盗链headers"
    return {
        'User-Agent': yiban_ua,
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-CN;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Host': 'cas.hnqczy.com:8002',
        'Upgrade-Insecure-Requests': '1',
        'Referer': referer,
    }


def xggl_headers(referer: str):
    """xggl定制防盗链headers"""
    return {
        'User-Agent': yiban_ua,
        'Upgrade-Insecure-Requests': '1',
        'Referer': referer,
        'Origin': 'http://cas.hnqczy.com:8002',
        'Host': 'cas.hnqczy.com:8002',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
    }


def str2data(text: str):
    """字符串转data"""
    data = dict()
    text.strip()
    text = text.replace('\t', '').split('\n')
    for i in text:
        if not i:
            continue
        try:
            i = i.split(':')
            data[i[0].strip()] = i[1].strip()
        except:
            LOG(i)
            data[i[0].strip()] = ''
    return data


# requests functions


def cas_datas_in_html(student: Student) -> (dict, dict):
    """ 获取html内初始cookie """
    url = 'http://cas.hnqczy.com:8002/cas/login'
    try:
        r = req.get(url, headers=cas_headers(url))
    except:
        student.is_success = False
        student.msg = '网络错误'
        return False

    # 解析html内cookies
    soup = bs4.BeautifulSoup(r.text, 'html.parser').find_all(
        name='input', attrs={'type': 'hidden'})
    cas_datas = dict()

    # 提取cookies
    for i in soup:
        cas_datas[i['name']] = i['value']

    # 理论返回 lt 和 execution
    if 'execution' in cas_datas.keys() and 'lt' in cas_datas.keys():
        LOG('1、获取 execution lt 成功')
    else:
        LOG('1、获取 execution lt 失败')
        student.is_success = False
        student.msg = '1、获取 execution lt 失败'

    if 'route' in r.cookies and 'JSESSIONID' in r.cookies:
        LOG('2、获取 route JSESSIONID 成功 JSESSIONID =', r.cookies['JSESSIONID'])
    else:
        LOG('2、获取 route JSESSIONID 失败')
        student.msg = '1、获取 route JSESSIONID 失败'

    return cas_datas, {i[0]: i[1] for i in r.cookies.items()}
    # {i[0]: i[1] for i in r.cookies.items()} 手动转dict() 防止requests的劣根性


def cas_login(SID: str, ID: str, cookie: dict, html_data: dict, student: Student) -> dict:
    """登录授权cookie"""
    url = 'http://cas.hnqczy.com:8002/cas/login'

    cas_data = {
        'authType': '0',
        'username': SID,
        'password': passwd_encode(ID),
    }

    r = req.post(url=url,
                 data=dict(cas_data, **html_data),
                 cookies=cookie,
                 headers=cas_headers(url)
                 )
    if 'CASPRIVACY' in r.cookies.keys() and 'CASTGC' in r.cookies.keys():
        LOG('3、获取 CASPRIVACY CASTGC 成功')
    else:
        LOG('3、登录信息c')
        student.is_success = False
        student.msg = '3、获取 CASPRIVACY CASTGC 失败'

    return {i[0]: i[1] for i in r.cookies.items()}


def cas_to_xggl(cookie: dict, student: Student) -> str:
    """用已授权cookie跳转至xggl"""
    url = 'http://cas.hnqczy.com:8002/cas/login?service=http://xggl.hnqczy.com/cas'

    r = req.get(url=url,
                headers=cas_headers(url),
                cookies=cookie,
                allow_redirects=False
                )
    try:
        url = r.headers['Location']
        LOG('4、302跳转至' + url)
        return url
    except:
        student.is_success = False
        student.msg = '登录错误'
        LOG(f'{student.name}登录错误')
        return False


def xggl_ssid(url: str, student: Student) -> dict:
    """通过cas授权的链接获取xggl SSID"""
    # JSESSIONID Location
    r = req.get(url, allow_redirects=False)
    cookie = {i[0]: i[1] for i in r.cookies.items()}

    if 'JSESSIONID' in cookie.keys() and 'Location' in r.headers.keys():
        LOG('5、跳转xggl成功')
    else:
        LOG('5、跳转xggl失败')
        student.is_success = False
        student.msg = '5、跳转xggl失败'
        return False

    location = r.headers['Location']

    r = req.get(location, headers=xggl_headers(location),
                allow_redirects=False, cookies=cookie)
    if 'Location' in r.headers.keys():
        LOG('6、跳转到' + r.headers['Location'])
    else:
        LOG('6、跳转到' + r.headers['Location'] + '失败')
        student.is_success = False
        student.msg = '6、SSID跳转失败'
        return False
    location = r.headers['Location']

    # xggl welcome
    try:
        # 预览 http://xggl.hnqczy.com/wap/main/welcome;jsessionid=xxxxx?_t_s_=xxxxxxxxxxxx
        location = 'http://xggl.hnqczy.com' + location
        location = location.replace(
            '?', ';jsessionid=' + cookie['JSESSIONID'] + '?')
        r = req.get(location, xggl_headers(location),
                    allow_redirects=False, cookies=cookie)
        return cookie
    except:
        LOG('SSID获取失败')
        student.is_success = False
        student.msg = '6、SSID跳转失败'
        return False


def zzdk_token_get(cookie: dict, student: Student) -> str:
    """获取打卡界面里藏得zzdk_token"""
    try:
        url = "http://xggl.hnqczy.com/wap/menu/student/temp/zzdk/_child_/edit?_t_s_=" + get_ts()
        r = req.get(url, cookies=cookie, headers=xggl_headers(url))
        zzdk_token = bs4.BeautifulSoup(r.text, 'html.parser').find(
            attrs={'id': 'zzdk_token'}).attrs['value']
        LOG('7、获取zzdk_token成功')
        return zzdk_token
    except:
        LOG('获取打卡界面里藏得zzdk_token失败')
        student.is_success = False
        student.msg = '获取打卡界面里藏得zzdk_token失败'
        return False


def get_last(cookie):
    url = 'http://xggl.hnqczy.com/content/student/temp/zzdk/lastone?_t_s_=' + get_ts()
    headers = xggl_headers(url)
    r = req.get(url, headers=headers, cookies=cookie)
    try:
        return r.json()
    except:
        return False


def dk(data, cookie, student):
    """打卡发包"""
    url = 'http://xggl.hnqczy.com/content/student/temp/zzdk?_t_s_=' + get_ts()
    r = req.post(url, headers=xggl_headers(url), cookies=cookie, data=data)
    try:
        if r.json()['result']:
            student.msg = '打卡成功'
            return True
        else:
            student.msg = r.json()['errorInfoList'][0]['message']
            if '重复' in r.json()['errorInfoList'][0]['message']:
                return True
            else:
                return False
    except:
        student.msg = '打卡失败'
        return False


if __name__ == '__main__':
    # 日志关
    log_switch = False


    with open('/'.join(__file__.split('/')[:-1]) + '/data.csv', 'r', encoding='utf-8') as f:
        data = pd.read_csv(f)

    ts = []
    student_ls = []
    for i in data.iterrows():
        try:
            def start(i):
                global student_ls
                i = list(i[1])
                student = Student(SID=str(i[1]), ID=i[2][-6:])
                student.name = i[0]
                student.main()
                if not student.is_success:
                    student_ls.append(student)


            t = Thread(target=start, args=(i,))
            ts.append(t)
            t.start()
            sleep(0.5)
        except:
            pass

    for i in ts:
        i.join()

    
    # # 邮箱通知
    # function_tools.send_mail(
    #     sender='📧发送者',
    #     password='📧密码',
    #     receivers='发送至xxx@xx.com',
    #     subject=datetime.date.today().strftime("%m月%d日") + '打卡日志',
    #     content='\n'.join([i.name + i.msg for i in student_ls])
    # )
