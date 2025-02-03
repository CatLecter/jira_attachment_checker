from dataclasses import dataclass


@dataclass
class Project:
    id: str
    name: str
    key: str
    link: str


@dataclass
class ProjectType:
    key: str
    formatted_key: str


@dataclass
class Issue:
    id: str
    key: str
    link: str
    project_id: str


@dataclass
class Comment:
    id: str
    body: str
    link: str
    issue_id_or_key: str


@dataclass
class Attachment:
    id: str
    filename: str
    link: str
    size: int
    mimetype: str
