# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import logging
import time
import threading

from PyQt5.QtCore import QThread

logger = logging.getLogger()


class UpdateTaskInfoThread(QThread):
    def __init__(self, lock, run_interval=1, target=None, args=(), kwargs=None):
        super().__init__()
        self.run_interval = run_interval
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs else {}
        self.lock = lock

    def run(self):
        while True:
            try:
                self.lock.lock()
                self.run_once()
                self.lock.unlock()
                time.sleep(self.run_interval)
            except:
                logger.error("run error", exc_info=True)
                break

    def run_once(self):
        if self.target:
            self.target(*self.args, **self.kwargs)


class CustomThread(threading.Thread):
    def __init__(self, target=None, args=(), kwargs=None):
        super().__init__()
        self.target= target
        self.args = args
        self.kwargs = kwargs if kwargs else {}

    def run(self):
        if self.target:
            self.target(*self.args, **self.kwargs)
        while True:
            time.sleep(1)


