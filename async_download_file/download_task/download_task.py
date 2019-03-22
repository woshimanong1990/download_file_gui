# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import concurrent.futures
import copy
import functools
import os
import re
import logging
import asyncio
import threading
from urllib.parse import urlparse
import time
import random

import aiohttp
import requests

from async_download_file.download_task import variables
from async_download_file.download_task import utils

logger = logging.getLogger()


class DownloadPreviewException(Exception):
    pass


class DownloadPreviewExecutor(object):
    def __init__(self, session, url, custom_headers=None, loop=None, executor=None):
        self.session = session
        self._download_url = url
        self._custom_headers = custom_headers
        self._file_info = {}
        self.loop = loop
        self.executor = executor

    async def _get_file_info_request(self, url, request_method="head", custom_headers=None):
        if request_method not in ["head", "get"]:
            raise ValueError("request_method error")
        try:
            filename = None
            accept_ranges = False
            headers = {} if request_method == "head" else {"Range": "bytes=0-0"}
            headers.update(variables.COMMON_HEADS)
            if custom_headers is not None and isinstance(custom_headers, dict):
                headers.update(custom_headers)
            request_obj = getattr(self.session, request_method)
            response = await self.loop.run_in_executor(self.executor, functools.partial(request_obj, url,
                                                                                        headers=headers,
                                                                                        allow_redirects=False,
                                                                                        timeout=30))
            if response.status_code // 100 == 4:
                raise Exception("url:{} get error status_code:{} method:{}".format(url, response.status_code, request_method))
            if response.status_code // 100 == 3:

                headers_content = response.headers
                for key in headers_content:
                    match = re.search("^location$", key, re.IGNORECASE)
                    if not match:
                        continue
                    location_key = match.group()
                    return await self._get_file_info_request(headers_content[location_key],
                                                             request_method=request_method,
                                                             custom_headers=custom_headers
                                                             )
                else:
                    raise Exception(
                        "get file name error, status_code is wrong, status_code:{}".format(response.status))

            headers_content = response.headers
            if "Content-Length" not in headers_content:
                raise Exception("can't get file size")
            if "Accept-Ranges" in headers_content:
                accept_ranges = True
            if 'Content-Disposition' in headers_content:
                encode_format = response.encoding or response.apparent_encoding
                # print('==============', response.encoding, response.apparent_encoding)
                tmp_file_name = utils.get_file_name_from_disposition(utils.get_utf8_code(encode_format, headers_content["Content-Disposition"]))
                if tmp_file_name:
                    filename = tmp_file_name
            if "Content-Length" not in headers_content:
                raise Exception("can't get file size!")
            if request_method == "head":
                file_size = int(headers_content["Content-Length"])
            else:
                if 'Content-Range' not in headers_content:
                    raise ValueError("can't get Content-Range")
                file_size = int(headers_content["Content-Range"].split("/")[1])
            return filename, file_size, accept_ranges, url
        except:
            logger.error("_get_file_info_request", exc_info=True)
            raise

    async def request_file_info(self):
        try:
            request_future = asyncio.gather(*[
                self._get_file_info_request(self._download_url, custom_headers=self._custom_headers),
                self._get_file_info_request(self._download_url, request_method='get',
                                            custom_headers=self._custom_headers),
            ], return_exceptions=True)
            await request_future
            head_result, get_result = request_future.result()
            filename_head, file_size_head, accept_ranges_head, url_head = None, 0, False, None
            filename_get, file_size_get, accept_ranges_get, url_get = None, 0, False, None

            if isinstance(head_result, Exception) and isinstance(get_result, Exception):
                raise DownloadPreviewException("get file info error")

            if not isinstance(head_result, Exception):
                filename_head, file_size_head, accept_ranges_head, url_head = head_result
            if not isinstance(get_result, Exception):
                filename_get, file_size_get, accept_ranges_get, url_get = get_result
            file_name = filename_head or filename_get
            file_size = file_size_head or file_size_get
            accept_ranges = accept_ranges_head or accept_ranges_get
            if url_head and url_head != self._download_url:
                self._download_url = url_head
            if url_get and url_get != self._download_url:
                self._download_url = url_get
            if file_name is None:
                urlobj = urlparse(self._download_url)
                file_name = utils.get_file_name_by_pattern(urlobj.path)
            self._file_info = {
                "file_size": file_size,
                "file_name": file_name,
                "accept_ranges": accept_ranges,
                "url": self._download_url
            }
            print(self._file_info)
        except DownloadPreviewException as e:
            raise
        except:
            logger.error("request_file_info error", exc_info=True)

    @property
    def download_url(self):
        return self._download_url

    @property
    def file_info(self):
        return self._file_info


class DownloadFileInfo(object):
    def __init__(self):
        pass

    @property
    def file_size(self):
        return

    @property
    def download_file_size(self):
        return

    @property
    def save_path(self):
        return


class DownloadSegment(object):
    def __init__(self, session, loop, executor, lock, url, file_fd, start_position, end_position, headers=None):
        self.loop = loop
        self.executor = executor
        self.lock = lock
        self.url = url
        self._custom_headers = headers
        self.fd = file_fd
        self.session = session

        self._current_position = self._start_position = start_position
        self._end_position = end_position
        self._task = None
        self._task_status = variables.TaskStatus.CREATED

    @property
    def status(self):
        return self._task_status.name

    def start(self):
        origin_url = urlparse(self.url).hostname
        if self._task is None:
            self._task = asyncio.run_coroutine_threadsafe(self.fetch(origin_url), self.loop)
            # self._task.add_done_callback(self.done_callback)
            self._task_status = variables.TaskStatus.WORKING

    def done_callback(self, _):
        if self._task_status != variables.TaskStatus.ERROR:
            self._update_status(variables.TaskStatus.DONE)

    def pause(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def done(self):
        pass

    def update_download_info(self, new_download_file_length):
        self._current_position += new_download_file_length

    def get_request_content_and_write_file(self, headers):
        res = self.session.get(self.url, headers=headers, stream=True, timeout=60*60*5)
        start_position = self._current_position
        with os.fdopen(self.fd, "rb+") as f:
            for chunk in res.iter_content(1024):
                self.lock.acquire()
                utils.write_to_file(f, start_position, chunk)
                self.lock.release()
                self.update_download_info(len(chunk))
                start_position += len(chunk)

    async def fetch(self, origin_url):
        headers = copy.deepcopy(variables.COMMON_HEADS)
        headers["Range"] = "bytes=%s-%s" % (self._current_position, self._end_position)
        headers["connection"] = "keep-alive"
        # headers["host"] = origin_url

        if isinstance(self._custom_headers, dict) and self._custom_headers:
            headers.update(self._custom_headers)
        try:
            await self.loop.run_in_executor(self.executor, functools.partial(self.get_request_content_and_write_file, headers))
        except Exception as e:
            logger.error("get error when downloading:%s", e, exc_info=True)
            self._update_status(variables.TaskStatus.ERROR)
        else:
            self._update_status(variables.TaskStatus.DONE)

    @property
    def start_position(self):
        return self._start_position

    @property
    def end_position(self):
        return self._end_position

    @property
    def current_position(self):
        return self._current_position

    def _update_status(self, status):
        self._task_status = status


class DownloadTask(object):
    def __init__(self, loop, url, save_dir, segment_number=64, custom_headers=None, executor=None, session=None,
                 overwrite=False, file_name=None):
        self.loop = loop
        self.url = url
        self.save_dir = save_dir
        self.segment_number = segment_number
        self.custom_headers = custom_headers
        self.executor = executor
        self.request_session = session
        self.file_info_request_executor = None
        self._error = None
        self.overwrite = overwrite
        self._file_path = file_name
        self._download_objects = []
        self.main_fd = None
        self._file_size = 0
        self.lock = threading.Lock()
        self._status = variables.TaskStatus.CREATED
        self._task = None
        self.init_env()

    def init_env(self):
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.segment_number)
        if self.request_session is None:
            self.request_session = requests.Session()
        if self.file_info_request_executor is None:
            self.file_info_request_executor = DownloadPreviewExecutor(self.request_session, self.url,
                                                                      self.custom_headers, loop=self.loop,
                                                                      executor=self.executor)

    def create_file(self, file_path):

        if not self.overwrite:
            while os.path.exists(file_path):
                root, ext = os.path.splitext(file_path)
                file_path = "{}_1{}".format(root, ext)
        with open(file_path, "w")as f:
            return file_path

    @property
    def error_reason(self):
        return self._error

    def update_status(self, status, message=None):
        self._status = status
        self._error = message

    async def get_file_fd(self, file_path):
        try:
            f = await self.loop.run_in_executor(None, functools.partial(open, file_path, "rb+"))
            self.main_fd = f.fileno()
            return self.main_fd, f
        except Exception as e:
            logger.exception("open file error, %s", e)

    def create_segment_list(self, main_fd):
        end = -1
        file_size = self.file_size - 1
        step = self.file_size // self.segment_number
        step = step if step else file_size

        start = -step
        while end < file_size:
            start = start + step
            end = end + step
            if end > file_size:
                end = file_size
            if end < 0:
                end = 0
            fd = os.dup(main_fd)
            download_obj = DownloadSegment(self.request_session, self.loop, self.executor, self.lock,
                                           self.url, fd, start, end,
                                           headers=self.custom_headers)
            self._download_objects.append(download_obj)

    def _start_task(self, task):
        task.start()
        time.sleep(1)

    async def _start_task_async(self):
        for t in self._download_objects:
            t.start()
            await asyncio.sleep(random.randint(1, 5))

    def start_task_one_by_one(self):
        # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        #     start_sequence = [executor.submit(self._start_task, t) for t in self._download_objects]
        #     for _ in concurrent.futures.as_completed(start_sequence):
        #         pass
        asyncio.ensure_future(self._start_task_async(), loop=self.loop)

        # for t in self._download_objects:
        #     t.start()
        #     time.sleep(1)

    def start(self):
        if self._status == variables.TaskStatus.DELETE:
            return
        if self._status == variables.TaskStatus.PAUSE:
            self.update_status(variables.TaskStatus.WORKING)
            self.start_task_one_by_one()
            return
        self.update_status(variables.TaskStatus.WORKING)
        if self._task is None:
            self._task = asyncio.run_coroutine_threadsafe(self.create_task(), self.loop)

    async def create_task(self):
        file_obj = None
        try:
            await self.file_info_request_executor.request_file_info()
            file_info = self.file_info_request_executor.file_info
            file_name = file_info.get("file_name", None)
            file_size = file_info.get("file_size", None)
            allow_ranges = file_info.get("accept_ranges", False)
            self.url = file_info.get("url", self.url)
            if file_name is None and self._file_path is None:
                self.update_status(variables.TaskStatus.ERROR, "获取不到文件名")
                return
            if not file_size:
                self.update_status(variables.TaskStatus.ERROR, "获取不到文件大小")
                return
            if not allow_ranges:
                self.segment_number = 1
            file_name = file_name if not self._file_path else self._file_path
            self._file_path = self.create_file(os.path.join(self.save_dir, file_name))
            self._file_size = file_size
            fd, file_obj = await self.get_file_fd(self._file_path)
            if fd == -1:
                self.update_status(variables.TaskStatus.ERROR, "创建文件失败")
                return
            self.create_segment_list(fd)
            self.start_task_one_by_one()
        except DownloadPreviewException as e:
            logger.error("download error", exc_info=True)
            self.update_status(variables.TaskStatus.ERROR, "获取文件信息失败")
        except:
            logger.error("unknown error", exc_info=True)
            self.update_status(variables.TaskStatus.ERROR, "未知错误")
        finally:
            if file_obj is None:
                return
            await self.loop.run_in_executor(self.executor, functools.partial(file_obj.close))

    @property
    def status(self):
        if not self._download_objects:
            return self._status.name
        if self._status == variables.TaskStatus.PAUSE:
            return self._status.name

        status = list(set([_.status for _ in self._download_objects]))
        if len(status) == 1 and status[0] == variables.TaskStatus.DONE.name:
            return variables.TaskStatus.DONE.name

        if variables.TaskStatus.ERROR.name in status:
            self.update_status(variables.TaskStatus.ERROR, "下载文件时出错，文件可能无法使用")
            return variables.TaskStatus.ERROR.name
        return variables.TaskStatus.WORKING.name

    @property
    def file_size(self):
        return self._file_size

    @property
    def file_path(self):
        return self._file_path

    def pause(self):
        if self._task is not None:
            self._task.cancel()
        [_.pause() for _ in self._download_objects]
        self.update_status(variables.TaskStatus.PAUSE)

    def delete(self):
        self.pause()
        self.update_status(variables.TaskStatus.DELETE)

    @property
    def current_download_file_size(self):
        return sum([_.current_position - _.start_position for _ in self._download_objects])
