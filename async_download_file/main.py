# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import asyncio
import time
import sys
import threading


from PyQt5.QtCore import QMutex

from PyQt5.QtWidgets import QApplication

from async_download_file.task_manager.custom_thread import UpdateTaskInfoThread, CustomThread
from async_download_file.task_manager.task_manager import TaskManger
from async_download_file.logger_config.logger_config import setup_logging_config
from async_download_file.download_task.variables import TaskStatus
from async_download_file.download_gui.mainWindow import CustomMainWindow
from async_download_file.variables import RUN_TIME_INTERVAL


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s/s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s/s" % (num, 'Yi', suffix)


def update_task_info(task_manager):
    current_time = time.time()
    tasks = task_manager.tasks
    task_infos = task_manager.task_info

    for task_id, task_obj in tasks.items():
        if task_obj.status != TaskStatus.WORKING.name and task_obj.status != TaskStatus.DONE.name:
            task_infos[task_id]["status"] = task_obj.status
            continue
        last_update_time = task_infos[task_id].get("last_update_time", None)
        last_file_size = task_infos[task_id].get("last_file_size", 0)
        file_size = task_obj.file_size
        current_file_size = task_obj.current_download_file_size
        status = task_obj.status
        file_path = task_obj.file_path
        if not file_size:
            continue
        if file_size and last_file_size and last_file_size == file_size:
            continue
        if last_update_time is None:
            task_infos[task_id] = {
                "speed": 0,
                "last_update_time": current_time,
                "file_size": file_size,
                "file_path": file_path,
                "last_file_size": current_file_size,
                "status": status,
            }
            continue
        gap_time = current_time - last_update_time
        if gap_time < RUN_TIME_INTERVAL:
            continue
        speed_raw = (current_file_size - last_file_size) / gap_time
        task_infos[task_id] = {
            "speed": sizeof_fmt(speed_raw),
            "last_update_time": current_time,
            "file_size": file_size,
            "file_path": file_path,
            "last_file_size": current_file_size,
            "status": status,
        }


def run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def main():
    lock = QMutex()
    setup_logging_config()
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    task_manager = TaskManger(loop=loop)
    thread = UpdateTaskInfoThread(lock, target=update_task_info, args=(task_manager,), run_interval=RUN_TIME_INTERVAL)
    thread.start()

    app = QApplication(sys.argv)
    main_window = CustomMainWindow(lock, task_manager, loop)
    main_window.show()
    t = threading.Thread(target=run_loop, args=(loop,))
    t.daemon = True
    t.start()
    app.exec_()


if __name__ == '__main__':
    main()
