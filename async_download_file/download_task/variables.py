# coding:utf-8
from enum import IntEnum

STATUS = {
    10001: "OPENFILE ERROR",
    10002: "GET FILE INFO ERROR",
    10003: "FIRST GET ERROR",
    10004: "TIME OUT",
    10005: "REMOTE FORBIDDEN"
}

COMMON_HEADS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
}

PROGRESS_ERROR = "PROGRESS ERROR, REASON: {}"

TASK_STATUS = {
    1: "created",
    2: "working",
    3: "done",
    4: "cancel",
    5: "error"
}


class TaskStatus(IntEnum):
    CREATED = 1
    WORKING = 2
    DONE = 3
    PAUSE = 4
    ERROR = 5
    DELETE = 6

