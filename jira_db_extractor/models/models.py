from dataclasses import dataclass


@dataclass
class Attachment:
    id: int
    filename: str
    file_size: int
    file_mime_type: str
    issue_num: int
    project_id: int
    path: str
    processed: bool = False
