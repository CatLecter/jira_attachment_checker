import json
from abc import ABC, abstractmethod

import requests


class ImageManager(ABC):
    def __init__(self, timeout: int = 3):
        self._timeout = timeout
        self.session = requests.session()

    @abstractmethod
    def get_random_image(self, width: int, height: int):
        pass


class LoremFlickrManager(ImageManager):
    def get_random_image(self, width: int, height: int) -> bytes:
        r = self.session.get(f'https://loremflickr.com/json/{width}/{height}')
        d = json.loads(r.text)
        img_url = d['rawFileUrl']
        img_r = self.session.get(img_url)
        return img_r.content
