from dataclasses import dataclass


@dataclass
class Attachment:
    id: int
    filename: str
    issue_num: int
    project_id: int
    processed: bool = False
