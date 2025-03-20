import glob
import json
import os.path
import time
from abc import ABC, abstractmethod

import requests


class AbstractImageManager(ABC):
    @abstractmethod
    def get_random_image(self, width: int, height: int):
        pass


class LoremFlickrManager(AbstractImageManager):
    def __init__(self, timeout: int = 3):
        self._timeout: int = timeout
        self.session = requests.session()
        self.last_run: float | None = None

    def get_random_image(self, width: int, height: int) -> bytes:
        if self.last_run:
            while (time.time() - self.last_run) < self._timeout:
                time.sleep(1)
        r = self.session.get(f'https://loremflickr.com/json/{width}/{height}')
        self.last_run = time.time()
        d = json.loads(r.text)
        img_url = d['file']
        img_r = self.session.get(img_url)
        return img_r.content


class FSImageManager(AbstractImageManager):
    def __init__(self, path: str):
        self._files: list[str] = glob.glob(os.path.join(path, '*.jpg'))
        self.index = 0

    def get_random_image(self, width: int, height: int):
        self._increment_index()
        with open(self._files[self.index], 'rb') as img_file:
            return img_file.read()

    def _increment_index(self):
        self.index += 1
        if self.index >= len(self._files):
            self.index = 0
