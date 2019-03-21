# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import uuid

from async_download_file.download_task.download_task import DownloadTask


class TaskManger(object):
    def __init__(self, loop=None, executor=None, session=None):
        self._tasks = {}
        self.loop = loop
        self.executor = executor
        self.session = session
        self._task_info = {}

    @property
    def tasks(self):
        return self._tasks

    def update_task_info(self, task_info):
        self._task_info = task_info

    def generate_task_id(self):
        task_id = uuid.uuid1().hex
        while task_id in self._tasks:
            task_id = uuid.uuid1().hex
        return task_id
            
    def add_task(self, url, save_dir, segment_number=64, custom_headers=None, overwrite=False, file_name=None):
        task_id = self.generate_task_id()
        self._tasks[task_id] = DownloadTask(self.loop, url, save_dir, segment_number=segment_number, 
                                            custom_headers=custom_headers, executor=self.executor,
                                            overwrite=overwrite, file_name=file_name)
        self._tasks[task_id].start()
        self._task_info[task_id] = {}
        return task_id
    
    def task_action(self, action, task_id=None):
        if task_id not in self._tasks:
            return
        if action not in ["delete", "pause", "start"]:
            raise ValueError("action not allow")
        if task_id is None:
            for v in self._tasks.values():
                getattr(v, action)()
        else:
            getattr(self._tasks[task_id], action)()
        if action == "delete":
            if task_id is not None:
                del self._tasks[task_id]
                del self._task_info[task_id]
            else:
                self._tasks = {}
                self._task_info = {}

    @property
    def task_info(self):
        return self._task_info

