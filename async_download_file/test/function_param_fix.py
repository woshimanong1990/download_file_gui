# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function


def wrapper(f):
    def wrapped(*args, **kwargs):
        print(args)
        f(*args, **kwargs)
    return wrapped


@wrapper
def fun(i: int):
    print()
    print(i)


def main():
    fun("d")


if __name__ == '__main__':
    main()
