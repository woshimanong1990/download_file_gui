# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import requests


def main(url, file_path):
    headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
               'accept-encoding': 'gzip, deflate, br', 'accept-language': 'zh-CN,zh;q=0.9',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36',
               'Range': 'bytes=0-1',
               'connection': 'keep-alive',

               }

    res = requests.get(url, headers=headers)
    if res.history:
        for resp in res.history:
            print("==========")
            print(resp.request.headers)
            print(resp.status_code, resp.url)
            print(resp.headers)
            print(resp.content)
    if res.status_code != 200:
        print("error", res.reason, res.status_code)
        return
    # with open(file_path, "wb") as f:
    #     f.write(res.content)


if __name__ == '__main__':
    url = "https://github.com/woshimanong1990/image_to_pdf/releases/download/0.0.1/image_to_pdf.zip"
    file_path = r""
    main(url, file_path)
