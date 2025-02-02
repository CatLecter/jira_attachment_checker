import json

from lorem_text import lorem
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

    def get_project_types(self) -> dict:
        r = self._session.get('/project/type')
        result = json.loads(r.text)
        return result

    def get_all_projects(self) -> dict:
        r = self._session.get(f'/project')
        result = json.loads(r.text)
        return result

    def get_issue(self, issue_name: str) -> dict:
        r = self._session.get(f'/issue/{issue_name}')
        result = json.loads(r.text)
        return result

    def create_project(self, project_name: str, project_type: str, project_lead: str) -> None:
        data = {
            'key': project_name.upper(),
            'description': lorem.sentence(),
            'name': project_name,
            'projectTypeKey': project_type,
            'lead': project_lead
        }
        r = self._session.post('/project/', json=data)
        print(r.text)
        print(r.status_code)

    def create_issue(self):
        data = {
            "fields": {
                "project":
                    {
                        "key": "TEST"
                    },
                "summary": "REST EXAMPLE",
                "description": "Creating an issue via REST API",
                "issuetype": {
                    "name": "Task"
                }
            }
        }
        r = self._session.post('/issue', json=data)
        print(r.status_code)
        # print(r.text)
        d = json.loads(r.text)
        print(d)

    def add_attachment(self, issue_id_or_key: str, attachment: bytes):
        data = {'file': ('image.png', attachment, 'image/png')}
        headers = {"X-Atlassian-Token": "no-check"}
        r = self._session.post(f'/issue/{issue_id_or_key}/attachments', headers=headers, files=data)
