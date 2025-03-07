from dataclasses import dataclass


@dataclass
class Attachment:
    id: int
    filename: str
    file_size: int
    file_mime_type: str
    issue_num: int
    project_id: int
    project_name: str
    path: str
    processed: bool = False

    def __post_init__(self):
        self.processed = True if self.processed else False
