import json

import requests
from requests import Session
from lorem_text import lorem


class JiraSession(Session):
    def __init__(self, base_url: str = None):
        super().__init__()
        self._base_url = base_url

    def request(self, method, url, *args, **kwargs):
        joined_url = f'{self._base_url}{url}'
        return super().request(method, joined_url, *args, **kwargs)


class JiraAPIHelper:
    def __init__(self, session: JiraSession):
        self._session = session

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


def get_random_image(width: int, height: int) -> bytes:
    r = requests.get(f'https://loremflickr.com/json/{width}/{height}')
    d = json.loads(r.text)
    img_url = d['rawFileUrl']
    img_r = requests.get(img_url)
    return img_r.content


def main(helper: JiraAPIHelper):
    # for i in range(10):
    #     helper.create_project(f'TEST-PROJECT{i}')
    # print(helper.get_project('TEST'))
    # print(helper.get_issue('TEST-24'))
    # img_data = get_random_image(300, 300)
    # issue = helper.get_issue('TEST-24')
    # helper.add_attachment('TEST-24', img_data)
    # print(helper.get_all_projects())
    # helper.create_project('test2', 'software', 'admin')
    # print(helper.get_project_types())
    helper.create_issue()


if __name__ == '__main__':
    s = JiraSession(base_url='http://127.0.0.1:8080/rest/api/latest')
    s.auth = ('admin', 'Qwerty123')
    h = JiraAPIHelper(s)
    main(h)
