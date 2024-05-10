import os

from os import path

from sys import exit
from sys import argv

from argparse import ArgumentParser
from argparse import ArgumentError

from PyQt6.QtWidgets import (
    QWidget, QPushButton,
    QLineEdit, QScrollArea,
    QVBoxLayout, QHBoxLayout,
    QApplication, QLabel,
    QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal

from collector import Collector


class WebDomainCollector(QWidget):
    class ButtonController(QThread):
        access = pyqtSignal(bool)

        def __init__(self, f):
            QThread.__init__(self, None)
            self.f = f
            self.blocked = False
            self.running = 0
        
        def run(self):
            while self.running:
                in_process = self.f() > 0
                if in_process and not self.blocked:
                    self.access.emit(False)
                    self.blocked = True
                elif not in_process and self.blocked:
                    self.access.emit(True)
                    self.blocked = False

    def __init__(self):
        QWidget.__init__(self, None)

        self.resize(420, 600)

        self.add_task = QPushButton("&Add")
        self.add_task.clicked.connect(self.on_add)
        self.start_all_tasks = QPushButton("&Start all")
        self.start_all_tasks.clicked.connect(self.on_start_all)
        self.delete_all_tasks = QPushButton("&Delete all")
        self.delete_all_tasks.clicked.connect(self.on_delete_all)
        self.collect_all_tasks = QPushButton("&Collect all")
        self.collect_all_tasks.clicked.connect(self.on_collect_all)
    
        general_box = QVBoxLayout()
        control_box = QHBoxLayout()
        scroll_box = QVBoxLayout()
        general_box.addLayout(control_box)
        general_box.addLayout(scroll_box)

        self.content_widget = QWidget()
        self.content_box = QVBoxLayout(self.content_widget)
        self.content_box.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        control_box.addWidget(self.add_task)
        control_box.addWidget(self.start_all_tasks)
        control_box.addWidget(self.delete_all_tasks)
        control_box.addWidget(self.collect_all_tasks)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.content_widget)
        self.scroll.setWidgetResizable(True)

        scroll_box.addWidget(self.scroll)

        self.setLayout(general_box)

        self.slots = [None for _ in range(8)]
        self.in_progress = 0

        self.locker = WebDomainCollector.ButtonController(self.locker)
        self.locker.start()

    def locker(self, lock):
        self.collect_all_tasks.setEnabled(lock)
        self.delete_all_tasks.setEnabled(lock)
        self.start_all_tasks.setEnabled(lock)

    def on_start(self):
        self.in_progress += 1
    
    def on_finish(self):
        self.in_progress -= 1

    def on_add(self):
        for i, val in enumerate(self.slots):
            if val is None:
                task = TaskPanel(i)
                task.deleted.connect(self.on_delete)
                task.started.connect(self.on_start)
                task.finished.connect(self.on_finish)
                task.collect_pressed.connect(self.on_collect)
                self.slots[i] = task
                self.content_box.addWidget(task)
                return

    def on_start_all(self):
        for slot in self.slots:
            if slot:
                slot.on_run()

    def on_delete_all(self):
        for slot in self.slots:
            if slot:
                slot.on_delete()

    def on_delete(self, slot):
        self.content_box.removeWidget(self.slots[slot])
        self.slots[slot].deleteLater()
        self.slots[slot] = None

    def on_collect(self, slot):
        if self.slots[slot].collector:
            domains = self.slots[slot].collector.domains
            
            if domains:
                if path.exists("domains.txt"):
                    with open("domains.txt", "r") as domain_file:
                        saved_domains = domain_file.read().split("\n")
                        domains = list(
                            filter(
                                lambda x: x not in saved_domains,
                                domains
                            )
                        )

                with open("domains.txt", "a") as domain_files:
                    domain_files.write("\n".join(domains) + ("\n" if len(domains) != 0 else ""))

    def on_collect_all(self):
        for i, slot in enumerate(self.slots):
            if slot:
                self.slots[i].on_collect()


class TaskPanel(QWidget):
    deleted = pyqtSignal(int)
    collect_pressed = pyqtSignal(int)
    started = pyqtSignal()
    finished = pyqtSignal()
    
    def __init__(self, id):
        QWidget.__init__(self, None)

        self.resize(400, 200)

        self.id = id

        self.urls_found = 0
        self.url_checked = 0

        # Создание блока с параметрами
        parameters_layout = QVBoxLayout()
        url_line_layout = QHBoxLayout()
        options_line_layout = QHBoxLayout()
        control_buttons_layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        control_layout.addLayout(parameters_layout)
        control_layout.addLayout(control_buttons_layout)
        parameters_layout.addLayout(url_line_layout)
        parameters_layout.addLayout(options_line_layout)

        self.url_line = QLineEdit()
        self.url_line.setPlaceholderText("Starting URL")
        url_line_layout.addWidget(self.url_line)

        self.domain_limit = QLineEdit()
        self.domain_limit.setPlaceholderText("Domains amount limit")
        options_line_layout.addWidget(self.domain_limit)

        self.indention_limit = QLineEdit()
        self.indention_limit.setPlaceholderText("Indention limit")
        options_line_layout.addWidget(self.indention_limit)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.on_run)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete)
        self.collect_button = QPushButton("Save")
        self.collect_button.clicked.connect(self.on_collect)
        self.collect_button.setEnabled(False)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop)
        self.stop_button.setEnabled(False)

        control_buttons_layout.addWidget(self.start_button)
        control_buttons_layout.addWidget(self.delete_button)
        control_buttons_layout.addWidget(self.collect_button)
        control_buttons_layout.addWidget(self.stop_button)

        # Создание информирующего дисплея

        info_layout = QVBoxLayout()
        self.progress_label = QLabel("No process")
        self.scroll = QScrollArea()

        self.info_widget = QWidget()
        self.info_box = QVBoxLayout()
        self.info_box.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        self.info_widget.setLayout(self.info_box)
        self.scroll.setWidget(self.info_widget)
        self.scroll.setWidgetResizable(True)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)

        info_layout.addWidget(separator)
        info_layout.addWidget(self.progress_label)
        info_layout.addWidget(self.scroll)
        

        general_layout = QVBoxLayout()
        general_layout.addLayout(control_layout)
        general_layout.addLayout(info_layout)

        self.setLayout(general_layout)

        self.collector = None
    
    def add_message(self, message):
        self.info_box.addWidget(QLabel(message))

    def on_stop(self):
        if self.collector:
            self.collector.executing = False
            self.collector.terminate()
            self.collector.wait()

    def on_collect(self):
        self.collect_pressed.emit(self.id)
        self.add_message("Saved")

    def on_delete(self):
        self.extra_close()
        self.deleted.emit(self.id)

    def extra_close(self):
        if self.collector:
            self.collector.executing = False
            self.collector.wait()

    def progress(self):
        return f"{self.url_checked}/{self.urls_found}"

    def on_run(self):     
        self.url_checked = 0
        self.urls_found = 0

        url = self.url_line.text().strip()
        if url == "":
            self.add_message("No url")
            return
        
        domain_limit_str = self.domain_limit.text().strip()
        if domain_limit_str == "":
            domain_limit = 10
        else:
            try:
                domain_limit = int(domain_limit_str)
            except ValueError:
                self.add_message("Incorrect domain limit. It should be integer")
                return
        
        indention_limit_str = self.indention_limit.text()
        if indention_limit_str == "":
            indention_limit = 5
        else:
            try:
                indention_limit = int(indention_limit_str)
            except ValueError:
                self.add_message("Incorrect indention limit. It should be integer")
                return

        self.collector = Collector(
            start_from=url,
            indention_limit=indention_limit,
            domain_limit=domain_limit
        )

        self.collector.got_domain.connect(self.on_got_domain)
        self.collector.checked_url.connect(self.on_checked_url)
        self.collector.found_urls.connect(self.on_found_urls)
        self.collector.error_occured.connect(self.on_error_occured)
        self.collector.started.connect(self.on_start)
        self.collector.finished.connect(self.on_finish)

        self.collector.start()
        self.collect_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.add_message("==== START ====")

    def on_got_domain(self, domain):
        self.add_message(f"Found: {domain}")

    def on_checked_url(self, url):
        self.url_checked += 1
        self.progress_label.setText(self.progress())

    def on_found_urls(self, found):
        self.urls_found += found

    def on_error_occured(self, err):
        self.add_message("Error: {}".format(err))

    def on_start(self):
        self.started.emit()
        self.start_button.setEnabled(False)

    def on_finish(self):
        self.finished.emit()
        self.add_message("====== END ======")
        self.start_button.setEnabled(True)
        self.collect_button.setEnabled(True)
        self.stop_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(argv)

    tp = WebDomainCollector()
    tp.show()

    exit(app.exec())
