# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import asyncio


async def factorial(name, number):
    f = 1
    if number > 5:
        raise Exception("too big number")
    for i in range(2, number + 1):
        print("Task %s: Compute factorial(%s)..." % (name, i))
        await asyncio.sleep(1)
        f *= i
    return f


async def test():
    future_results = asyncio.gather(
        factorial("A", 2),
        factorial("B", 3),
        factorial("C", 7),
        return_exceptions=True
    )
    await future_results
    print([type(i) for i in future_results.result()])


def main():

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()


if __name__ == '__main__':
    main()