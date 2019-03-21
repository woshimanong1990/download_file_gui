# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import asyncio


async def test():
    await asyncio.sleep(1)
    print("sleep done")


def main():

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    asyncio.ensure_future(test(), loop=loop)
    loop.run_forever()


if __name__ == '__main__':

    main()
    print("===done===")