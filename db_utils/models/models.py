from dataclasses import dataclass, field


@dataclass
class Attachment:
    id: int
    filename: str
    file_size: int
    file_mime_type: str
    issue_num: int
    issue_name: str = field(init=False)
    project_id: int
    project_name: str
    path: str
    processed: bool = False

    def __post_init__(self):
        self.processed = True if self.processed else False
        self.issue_name = f'{self.project_name}-{self.issue_num}'
