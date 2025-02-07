import json
import time
from abc import ABC, abstractmethod

import requests


class AbstractImageManager(ABC):
    def __init__(self, timeout: int = 3):
        self._timeout: int = timeout
        self.session = requests.session()
        self.last_run: int | None = None

    @abstractmethod
    def get_random_image(self, width: int, height: int):
        pass


class LoremFlickrManager(AbstractImageManager):
    def get_random_image(self, width: int, height: int) -> bytes:
        while (time.time() - self.last_run) < self._timeout:
            time.sleep(1)
        r = self.session.get(f'https://loremflickr.com/json/{width}/{height}')
        self.last_run = time.time()
        d = json.loads(r.text)
        img_url = d['rawFileUrl']
        img_r = self.session.get(img_url)
        return img_r.content
