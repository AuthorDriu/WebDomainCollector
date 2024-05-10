from typing import List

from pathlib import Path
from os import remove
from os import path

from PyQt6.QtCore import (
    QThread, pyqtSignal
)
from PyQt6 import QtCore

from requests import get
from bs4 import BeautifulSoup


class Collector(QThread):
    """Collector собирает ссылки со страниц HTML
    и выделяет домен из адреса."""
    got_domain: pyqtSignal = pyqtSignal(str)
    checked_url: pyqtSignal = pyqtSignal(str)
    found_urls: pyqtSignal = pyqtSignal(int)
    error_occured: pyqtSignal = pyqtSignal(str)

    def __init__(self, start_from:str=None, indention_limit:int=10, domain_limit:int=100):
        QThread.__init__(self, None)
        self._target = start_from
        self._indention_limit = indention_limit
        self._domain_limit = domain_limit

        self._collected_domains: List[str] = []
        self._checked_urls: List[str] = []

        self.executing = True

    @property
    def domains(self) -> List[str] | None:
        if self.executing:
            return None
        else:
            return self._collected_domains

    def extract_domain_from_url(self, url) -> str | None:
        splited = url.split("/")
        if len(splited) >= 3:
            return splited[2]
        else:
            return None

    def collect_urls(self, page: str) -> List[str]:
        soup = BeautifulSoup(page, "html.parser")
        return list(
            filter(
                lambda x: x not in self._checked_urls,
                [x.get("href") for x in soup.find_all("a")]
            )
        )

    def collect(self, indention:int=0):
        if not self.executing:
            return

        if indention >= self._indention_limit:
            return
        
        if len(self._collected_domains) >= self._domain_limit:
            self.executing = False
            return
        
        try:
            r = get(self._target)
            self._checked_urls.append(self._target)

            if r.status_code not in [200, 300, 301]:
                return

            self.checked_url.emit(self._target)

            domain = self.extract_domain_from_url(self._target)

            if domain not in self._collected_domains:
                self._collected_domains.append(domain)
                self.got_domain.emit(domain)

            urls = self.collect_urls(r.text)
            
            if len(urls) != 0:
                self.found_urls.emit(len(urls))

            while len(urls) != 0 and self.executing:
                self._target = urls.pop(0)
                self.collect(indention + 1)
            
        except Exception:
            return

    def run(self):
        """Точка входа потока"""
        if not self._target:
            self.error_occured.emit("No set starting url")
            return

        try:
            r = get(self._target)
            if r.status_code not in [200, 300, 301]:
                self.error_occured.emit("Can't load page")
                return
        except:
            self.error_occured.emit("Error")
            return

        while self.executing:
            try:
                self.collect()
            except RecursionError:
                pass
            except:
                self.error_occured.emit("Error")
                return
    

if __name__ == "__main__":
    collector = Collector(start_from="https://en.wikipedia.org/wiki/Saline_(medicine)")
    collector.got_domain.connect(lambda d: print(f"GOT DOMAIN: {d}"))
    collector.checked_url.connect(lambda r: print(f"CHECKED URL: {r}"))
    collector.found_urls.connect(lambda r: print(f"FOUND URL: {r}"))
    collector.error_occured.connect(lambda e: print(f"ERROR: {e}"))
    collector.run()
