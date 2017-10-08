import markdown2 as md
import smtplib as smtp
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import time

categories = {
    'Положительное': 'Что получилось хорошо.',
    'Отрицательное': 'Что могли сделать лучше.',
}

user = os.environ.get('SMTP_USER', '')
password = os.environ.get('SMTP_PASS', '')
server = os.environ.get('SMTP_SERVER', '')
port = int(os.environ.get('SMTP_PORT', '465'))

srv = None


def init():
    global srv
    srv = smtp.SMTP_SSL(server, str(port))
    srv.ehlo()
    srv.login(user, password)


def report(desc):
    dic = {}
    result = ""
    for sent, cat in desc:
        if cat not in dic:
            dic[cat] = []
        dic[cat].append(sent)
    for cat, sents in dic.items():
        result += "\n"
        result += "## " + categories[cat] + "\n"
        for sent in sents:
            result += "* " + sent + "\n"
    return result, md.markdown(result)


def send(markdown, html, mail):
    message = MIMEMultipart()
    message.attach(MIMEText(html, 'html'))
    message.attach(MIMEApplication(markdown, 'octet-stream',
                                   Name='report-' + time.strftime("%d_%m_%Y") + '.md'))
    message['From'] = user
    message['To'] = mail
    message['Subject'] = 'Ретроспектива'
    srv.sendmail(user, mail, message.as_string())


if '__main__' == __name__:
    init()
    send(*report([('positive', 'Положительное'), ('negative', 'Отрицательное'), ('positive2', 'Положительное')]), user)
