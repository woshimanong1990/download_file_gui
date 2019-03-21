# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
import logging
import time
import queue
import asyncio

from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal

from async_download_file.download_gui.UI_main_window import Ui_MainWindow
from async_download_file.download_gui.utils import checkout_url
from async_download_file.download_gui.variables import DownloadStatus

logger = logging.getLogger()


class UpdateProgressBarThread(QThread):
    update_progress_signal = pyqtSignal(str, tuple)
    show_task_status_signal = pyqtSignal(str, str)

    def __init__(self, lock, task_queue, task_manager, run_interval=0.5):
        super().__init__()
        self.queue = task_queue
        self.task_manager = task_manager
        self.run_interval = run_interval
        self.should_pause = False
        self.current_task_id = None
        self.lock = lock

    def run(self):
        while True:
            try:
                self.lock.lock()
                self.run_once()
                self.lock.unlock()
            except:
                logger.error("update task progress bar error", exc_info=True)
            finally:
                time.sleep(self.run_interval)

    def run_once(self):
        task_id, action = None, None
        if not self.queue.empty():
            try:
                task_id, action = self.queue.get(block=False)
                # print("********@@@@@@@@@@@@@@@@", task_id, action)
            except queue.Empty as e:
                pass
        else:
            if self.current_task_id is None:
                return
        if task_id and self.current_task_id is None:
            self.current_task_id = task_id
        if action == "pause" and task_id == self.current_task_id:
            self.task_manager.task_action("pause", self.current_task_id)
            return
        if action == "delete" and task_id == self.current_task_id:
            self.task_manager.task_action("delete", self.current_task_id)
            self.current_task_id = None
            return
        if action == "restart" and task_id == self.current_task_id:
            self.task_manager.task_action("start", self.current_task_id)
        task_info = self.task_manager.task_info.get(self.current_task_id, {})
        # print("*********** task info", task_info)
        if not task_info:
            return
        speed = task_info.get("speed", '0')
        file_size = task_info.get("file_size", 1)
        if not file_size:
            file_size = 1
        last_file_size = task_info.get("last_file_size", 0)
        status = task_info.get("status", "None")
        download_pecent = int(last_file_size/file_size*100)
        self.update_progress_signal.emit(self.current_task_id, (download_pecent, speed))
        if status in [DownloadStatus.ERROR.name, DownloadStatus.DONE.name]:
            self.show_task_status_signal.emit(self.current_task_id, status)


class CustomMainWindow(QMainWindow):
    def __init__(self, lock, task_manager, loop, parent=None):
        super().__init__(parent=parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.file_path_dir = None
        self.url = None
        self.progress_value = 0
        self.speed_text = ""
        self.segment_number = 64
        self.task_manager = task_manager
        self.loop = loop
        self.cookie = None
        self.status = DownloadStatus.CREATED
        self.queue = queue.Queue()
        self.thread = UpdateProgressBarThread(lock, self.queue, self.task_manager)
        self.thread.update_progress_signal.connect(self.update_progress)
        self.thread.show_task_status_signal.connect(self.showTaskStatus)
        self.thread.start()
        self.current_task_id = None
        self.task_status_info = {}
        self.set_env()

    def set_env(self):
        # TODO：这个必须设置，不然会报错， 有时间查下原因
        asyncio.set_event_loop(self.loop)

    def selectFilePath(self):
        try:
            save_file_dir = QFileDialog.getExistingDirectory(self, "请选择保存路径")
            if not save_file_dir:
                QMessageBox.critical(self, "错误", "没有选择文件夹")
                return
            self.ui.filePathLineEdit.setText(save_file_dir)
            self.file_path_dir = save_file_dir
        except:
            logger.error("get save file dir error", exc_info=True)

    def check_input_value(self):
        self.url = self.ui.urlLineEdit.text()
        self.cookie = self.ui.cookieTextEdit.toPlainText()
        if not self.file_path_dir:
            QMessageBox.critical(self, '错误', '请选择保存文件的路径（文件夹）')
            return False
        if not self.url or not checkout_url(self.url):
            QMessageBox.critical(self, '错误', 'URL为空或者不正确')
            return False
        return True

    def reset_value(self):
        self.file_path_dir = None
        self.url = None
        self.progress_value = 0
        self.speed_text = ""
        self.segment_number = 64
        self.status = DownloadStatus.CREATED
        self.current_task_id = None
        self.task_status_info = {}

    def resetParam(self):
        task_id = self.current_task_id
        self.reset_value()
        self.ui.urlLineEdit.clear()
        self.ui.cookieTextEdit.clear()
        self.ui.progressBar.setValue(0)
        self.ui.speedLabel.setText("")
        index_ = self.ui.segmentComboBox.findText(str(self.segment_number))
        # print(index_)
        self.ui.segmentComboBox.setCurrentIndex(index_)
        self.ui.downloadButton.setText("下载")
        self.ui.filePathLineEdit.clear()
        self.queue.put_nowait((task_id, "delete"))

    def startDownload(self):
        try:
            result = self.check_input_value()
            if not result:
                return
            sender = self.sender()
            if sender.text() == "暂停":
                sender.setText("下载")
                self.status = DownloadStatus.PAUSE
                self.queue.put_nowait((self.current_task_id, "pause"))
                return
            else:
                sender.setText("暂停")
            if self.status == DownloadStatus.PAUSE:
                self.status = DownloadStatus.WORKING
                self.queue.put_nowait((self.current_task_id, "restart"))
                return
            if self.status == DownloadStatus.DONE or self.status == DownloadStatus.ERROR:
                self.ui.progressBar.setValue(0)
            self.status = DownloadStatus.WORKING

            headers = None
            if self.cookie:
                headers = {"cookie": self.cookie}

            self.current_task_id = self.task_manager.add_task(self.url, self.file_path_dir,
                                                              segment_number=self.segment_number,
                                                              custom_headers=headers)
            try:
                self.queue.put_nowait((self.current_task_id, "start"))
            except queue.Full as e:
                logger.error("queue is full", exc_info=True)
                QMessageBox.critical(self, "错误", '任务队列满了，遇到未知错误，请稍候重试')
        except:
            QMessageBox.critical(self, "错误", "下载出错了")
            logger.error("startDownload error", exc_info=True)

    def closeWindow(self):
        self.close()
        self.loop.call_soon_threadsafe(self.loop.stop)

    def changeUrlContent(self):
        self.url = self.ui.urlLineEdit.text()

    def segmentNumberChange(self, value):
        self.segment_number = int(value)

    def closeEvent(self, event):
        user_button = QMessageBox.question(self, "警告", "确定要关闭吗？", QMessageBox.Ok | QMessageBox.Cancel)
        if user_button == QMessageBox.Ok:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.terminate()
            event.accept()
        else:
            event.ignore()

    def update_progress(self, task_id, item):
        try:
            if task_id != self.current_task_id:
                return
            download_pecent, speed = item
            self.ui.progressBar.setValue(download_pecent)
            self.ui.speedLabel.setText(str(speed))
        except:
            logger.error("set progress bar error", exc_info=True)
            QMessageBox.critical(self, "错误", "设置进度条信息失败")

    def notice_user_task_status(self, task_id, status, message):
        self.task_status_info[task_id] = status
        QMessageBox.information(self, "信息提示", message)
        try:
            self.queue.put_nowait((task_id, "delete"))
        except queue.Full as e:
            logger.error("queue is full", exc_info=True)
            QMessageBox.critical(self, "错误", '任务队列满了，遇到未知错误，请稍候重试')

    def showTaskStatus(self, task_id, status):
        # print("TAG", self.task_status_info, task_id)
        try:
            message = "下载失败" if status == DownloadStatus.ERROR.name else "下载成功"
            task_status = getattr(DownloadStatus, status)
            # print("status", task_status)
            self.status = getattr(DownloadStatus, status)
            self.ui.downloadButton.setText("下载")
            if task_id != self.current_task_id:
                return
            if task_id not in self.task_status_info:
                self.notice_user_task_status(task_id, status, message)
                return
            old_status = self.task_status_info.get(task_id)
            if status != old_status:
                self.notice_user_task_status(task_id, status, message)
                return
        except:
            logger.error('showTaskStatus error', exc_info=True)


