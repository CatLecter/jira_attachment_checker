import json
import time
from abc import ABC, abstractmethod

import requests


class AbstractImageManager(ABC):
    def __init__(self, timeout: int = 3):
        self._timeout: int = timeout
        self.session = requests.session()
        self.last_run: float | None = None

    @abstractmethod
    def get_random_image(self, width: int, height: int):
        pass


class LoremFlickrManager(AbstractImageManager):
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
