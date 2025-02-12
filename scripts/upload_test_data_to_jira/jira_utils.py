import json

from lorem_text import lorem
from models import Attachment, Comment, Issue, Project, ProjectType
from requests import Session


class JiraSession(Session):
    def __init__(self, base_url: str = None):
        super().__init__()
        self._base_url = base_url

    def request(self, method, url, *args, **kwargs):
        joined_url = f'{self._base_url}{url}'
        return super().request(method, joined_url, *args, **kwargs)


class JiraAPIHelper:
    def __init__(self, base_url: str, login: str, password: str):
        self._session = JiraSession(base_url)
        self._session.auth = (login, password)

    def get_project_types(self) -> list[ProjectType]:
        r = self._session.get('/project/type')
        types = json.loads(r.text)
        result = []
        for t in types:
            result.append(ProjectType(t['key'], t['FormattedKey']))
        return result

    def get_all_projects(self) -> list[Project]:
        r = self._session.get(f'/project')
        response_dict = json.loads(r.text)
        result = []
        for p in response_dict:
            result.append(Project(p['id'], p['name'], p['key'], p['self']))
        return result

    def get_project(self, id_or_key: str) -> Project:
        r = self._session.get(f'/project/{id_or_key}')
        response_dict = json.loads(r.text)
        return Project(
            response_dict['id'],
            response_dict['name'],
            response_dict['key'],
            response_dict['self'],
        )

    def get_issue(self, issue_name: str) -> Issue:
        r = self._session.get(f'/issue/{issue_name}')
        response_dict = json.loads(r.text)
        return Issue(
            response_dict['id'],
            response_dict['key'],
            response_dict['self'],
            response_dict['fields']['project']['id'],
        )

    def create_project(self, project_name: str, project_type: str, project_lead: str) -> Project:
        data = {
            'key': project_name.upper(),
            'description': lorem.sentence(),
            'name': project_name,
            'projectTypeKey': project_type,
            'lead': project_lead,
        }
        r = self._session.post('/project/', json=data)
        d = json.loads(r.text)
        project = Project(d['id'], project_name, d['key'], d['self'])
        return project

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = 'Task',
    ) -> Issue:
        data = {
            'fields': {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
        }
        r = self._session.post('/issue', json=data)
        response_dict = json.loads(r.text)
        return Issue(
            response_dict['id'],
            response_dict['key'],
            response_dict['self'],
            self.get_project(project_key).id,
        )

    def add_comment_to_issue(self, issue_id_or_key: str, comment: str) -> Comment:
        data = {'body': comment}
        r = self._session.post(f'/issue/{issue_id_or_key}/comment', json=data)
        response_dict = json.loads(r.text)
        return Comment(
            response_dict['id'],
            response_dict['body'],
            response_dict['self'],
            issue_id_or_key,
        )

    def add_attachment(self, issue_id_or_key: str, attachment: bytes, filename: str) -> Attachment:
        data = {'file': (filename, attachment, 'image/png')}
        headers = {'X-Atlassian-Token': 'no-check'}
        r = self._session.post(
            f'/issue/{issue_id_or_key}/attachments',
            headers=headers,
            files=data,
        )
        response_dict = json.loads(r.text)[0]
        return Attachment(
            response_dict['id'],
            response_dict['filename'],
            response_dict['content'],
            response_dict['size'],
            response_dict['mimeType'],
        )
