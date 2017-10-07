import markdown2 as md
import smtplib as smtp

categories = {
    'Положительное': 'Что получилось хорошо.',
    'Отрицательное': 'Что могли сделать лучше.',
}

def report(desc, mail):
    result = ""
    dic = {}
    for sent, cat in desc:
        if cat not in desc:
            dic[cat] = []
        dic[cat].append(sent)
    for cat, sents in dic.items():
        result += "## " + categories[cat] + "\n"
