# 导入发邮件的模块
import smtplib
from email.mime.text import MIMEText
from email.header import Header


# 定义一个名为 send_mail 的函数，参数为发件人、密码、收件人列表、主题和正文
def send_mail(sender, password, receivers, subject, content):
    # 创建邮件对象
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header(sender)
    msg['To'] = Header(','.join(receivers))
    msg['Subject'] = Header(subject)

    # 连接服务器并发送邮件
    server = smtplib.SMTP_SSL('smtp.qq.com', 465)  # QQ邮箱的服务器和端口号
    server.login(sender, password)  # 登录发件人邮箱
    server.sendmail(sender, receivers, msg.as_string())  # 发送邮件
    server.quit()  # 退出服务器

    print('Email sent successfully.')
