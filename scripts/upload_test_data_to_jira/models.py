from dataclasses import dataclass


@dataclass
class Project:
    project_id: str
    name: str
    key: str
    link: str


@dataclass
class ProjectType:
    key: str
    formatted_key: str


@dataclass
class Issue:
    issue_id: str
    key: str
    link: str
    project_id: str


@dataclass
class Comment:
    comment_id: str
    body: str
    link: str
    issue_id_or_key: str


@dataclass
class Attachment:
    attachment_id: str
    filename: str
    link: str
    size: int
    mimetype: str
