import requests as r
import sys
import os
import base64
import json
import gevent as g
import pymorphy2


def encode(text):
    return base64.encodebytes(text.encode()).decode('utf-8')


user = os.environ.get('COMPRENO_USER', '')
password = os.environ.get('COMPRENO_PASS', '')
auth = user + ':' + password
compreno_url = os.environ.get('COMPRENO_URL', 'http://comprenoproducts.abbyy.com')

headers = {
    'Authorization':
        'Basic ' + encode(auth)[:-1],
    'Content-Type': 'application/json'
}


def process(text):
    analyzer = pymorphy2.MorphAnalyzer()
    sentences = []
    for word in text.split():
        parsed = analyzer.parse(word)
        name = ['Name', 'Surn', 'Orgn', 'Patr', 'Trad', 'Geox']
        is_name = len(parsed) == 0
        if not is_name:
            for n in name:
                if n in parsed[0].tag:
                    is_name = is_name or n in parsed[0].tag
        if len(sentences) == 0 or (word[0].isupper() and not is_name):
            sentences.append(word)
        else:
            sentences[-1] += (' ' + word)
    greenlets = [g.spawn(make_request, sent) for sent in sentences]
    g.joinall(greenlets)
    return [(sent, gl.value[0])
            for sent, gl in zip(sentences, greenlets)
            if gl.value is not None]


def make_request(text):
    content = {
        "sourceFiles": [
            {
                "extension": "txt",
                "content": encode(text)
            }
        ],
        "operations": {
            "classification": {
                "modelName": "Retrospectiva",
                "resultFormat": "json"
            }
        }
    }
    for i in range(5):
        if i > 0:
            g.sleep(5 * 2 ** i)
        resp = r.post(compreno_url + '/api/tasks?async=false', headers=headers, data=json.dumps(content))
        if resp.ok:
            res = json.loads(resp.content.decode('utf-8'))[0]
            if not res['isSuccessful']:
                return
            else:
                res = res['fileResult']["classificationResult"]["resultList"][0]["categoryList"]
                for item in res:
                    return item["categoryName"], item["probability"]
                return
        else:
            print("error", resp.content, file=sys.stderr)


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()
    txt = """
    Здравствуйте меня зовут Светлана я
     сотрудник банка Тинькофф я вас прошу 
     могу предположить чтобы мог звонить
      специалист банка с целью озвучить
       предложения по кредитной карте 
    Скажите пожалуйста как я могу к вам обращаться
    """
    s = g.spawn(process, txt)
    s.join()
    print(s.value)
