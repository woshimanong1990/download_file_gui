# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function


def func(_file_size, segment_number):
    end = -1
    file_size = _file_size - 1
    step = _file_size // segment_number
    step = step if step else file_size

    start = -step
    while end < file_size:
        start = start + step
        end = end + step
        # print("start:end:", start,end)
        if end > file_size:
            end = file_size
        if end < 0:
            end = 0
        print(start, end)


def main(file_size, segment_number):
    func(file_size, segment_number)


if __name__ == '__main__':
    file_size = 1
    segment_number = 10
    main(file_size, segment_number)