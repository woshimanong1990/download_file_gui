# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import threading
import asyncio
import time


async def test(n):
    print(n)
    await asyncio.sleep(3)


def test2(n):
    print(n)
    # time.sleep(3)


def thread_fun(loop):
    asyncio.set_event_loop(loop)
    for i in range(3):
        asyncio.run_coroutine_threadsafe(test(i), loop)
        # time.sleep(1)


def main():
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    t = threading.Thread(target=thread_fun, args=(loop,))
    t.start()
    asyncio.run_coroutine_threadsafe(test(100), loop)
    loop.run_forever()


if __name__ == '__main__':
    main()