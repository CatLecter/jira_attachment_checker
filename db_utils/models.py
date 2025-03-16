from dataclasses import dataclass, field
from datetime import datetime

from settings import settings


@dataclass
class Attachment:
    id: int
    filename: str
    file_size: int
    file_mime_type: str
    issue_num: int
    issue_name: str = field(init=False)
    created: datetime
    updated: datetime
    project_id: int
    project_name: str
    path: str
    processed: bool = False

    def __post_init__(self):
        self.processed = True if self.processed else False
        self.issue_name = f'{self.project_name}-{self.issue_num}'
        if isinstance(self.created, str):
            self.created = datetime.strptime(self.created, settings.time_format)
        if isinstance(self.updated, str):
            self.updated = datetime.strptime(self.updated, settings.time_format)
