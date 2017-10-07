import requests as r
import sys
import os
import base64
import json
import gevent as g

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
    txt = """
    Мы начали добавлять новые фичи, заказчик доволен.
    """
    print(process(txt))
