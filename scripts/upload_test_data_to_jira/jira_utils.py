import json

from exceptions import ProjectException
from lorem_text import lorem
from models import Attachment, Comment, Issue, Project, ProjectType
from requests import Response, Session


class JiraSession(Session):
    def __init__(self, base_url: str = None):
        super().__init__()
        self._base_url: str = base_url

    def request(self, method, url, *args, **kwargs):
        joined_url: str = f'{self._base_url}{url}'
        return super().request(method, joined_url, *args, **kwargs)


class JiraAPIAdapter:
    def __init__(self, base_url: str, login: str, password: str):
        self._session: Session = JiraSession(base_url)
        self._session.auth = (login, password)

    def get_project_types(self) -> list[ProjectType]:
        r: Response = self._session.get('/project/type')
        self._check_response('get_project_types', r)
        types_json: list[dict] = json.loads(r.text)
        result: list[ProjectType] = []
        for t in types_json:
            result.append(ProjectType(t.get('key'), t.get('FormattedKey')))
        return result

    def get_all_projects(self) -> list[Project]:
        r: Response = self._session.get(f'/project')
        self._check_response('get_all_project', r)
        projects_json: list[dict] = json.loads(r.text)
        result: list[Project] = []
        for p in projects_json:
            result.append(Project(p.get('id'), p.get('name'), p.get('key'), p.get('self)')))
        return result

    def get_project(self, id_or_key: str) -> Project:
        r: Response = self._session.get(f'/project/{id_or_key}')
        self._check_response('get_project', r)
        project_json: dict = json.loads(r.text)
        return Project(
            project_json.get('id'),
            project_json.get('name'),
            project_json.get('key'),
            project_json.get('self'),
        )

    def get_issue(self, issue_name: str) -> Issue:
        r: Response = self._session.get(f'/issue/{issue_name}')
        self._check_response('get_issues', r)
        issue_json: dict = json.loads(r.text)
        return Issue(
            issue_json.get('id'),
            issue_json.get('key'),
            issue_json.get('self'),
            issue_json.get('fields').get('project').get('id'),
        )

    def create_project(self, project_name: str, project_type: str, project_lead: str) -> Project:
        data = {
            'key': project_name.upper(),
            'description': lorem.sentence(),
            'name': project_name,
            'projectTypeKey': project_type,
            'lead': project_lead,
        }
        r: Response = self._session.post('/project/', json=data)
        self._check_response('create_project', r)
        project_json: dict = json.loads(r.text)
        project = Project(project_json.get('id'), project_name, project_json.get('key'), project_json.get('self'))
        return project

    def delete_project(self, project_id_or_key: str):
        r: Response = self._session.delete(f'/project/{project_id_or_key}')
        if r.status_code != 204:
            print(f'Error deleting project {project_id_or_key}')
            return
        print(f'Project {project_id_or_key} deleted')

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
        r: Response = self._session.post('/issue', json=data)
        self._check_response('create_issue', r)
        issue_json = json.loads(r.text)
        return Issue(
            issue_json.get('id'),
            issue_json.get('key'),
            issue_json.get('self'),
            self.get_project(project_key).project_id,
        )

    def add_comment_to_issue(self, issue_id_or_key: str, comment: str) -> Comment:
        data = {'body': comment}
        r: Response = self._session.post(f'/issue/{issue_id_or_key}/comment', json=data)
        self._check_response('add_comment_to_issue', r)
        connet_json: dict = json.loads(r.text)
        return Comment(
            connet_json.get('id'),
            connet_json.get('body'),
            connet_json.get('self'),
            issue_id_or_key,
        )

    def add_attachment(self, issue_id_or_key: str, attachment: bytes, filename: str) -> Attachment:
        data = {'file': (filename, attachment, 'image/png')}
        headers = {'X-Atlassian-Token': 'no-check'}
        r: Response = self._session.post(
            f'/issue/{issue_id_or_key}/attachments',
            headers=headers,
            files=data,
        )
        self._check_response('add_attachment', r)
        attachment_json: dict = json.loads(r.text)[0]
        return Attachment(
            attachment_json.get('id'),
            attachment_json.get('filename'),
            attachment_json.get('content'),
            attachment_json.get('size'),
            attachment_json.get('mimeType'),
        )

    def get_all_issues(self, start_at, batch_size) -> list[Issue]:
        issues: list[Issue] = []
        print(start_at)
        data = {'jql': '', 'fields': 'project', 'startAt': start_at, 'maxResults': batch_size}
        r = self._session.get('/search', params=data)
        self._check_response('get_all_issues', r)

        issues_list = json.loads(r.text).get('issues', [])
        if not issues_list:
            return issues
        for i in issues_list:
            fields = i.get('fields')
            issue_project = fields.get('project')
            if not issue_project:
                raise ValueError('no project got from issue')
            issues.append(Issue(i.get('id'), i.get('key'), i.get('self'), issue_project.get('id')))
        start_at += batch_size
        return issues

    @staticmethod
    def _check_response(method_name: str, response: Response):
        if not response.status_code // 100 == 2:
            try:
                error_json = json.loads(response.text)
                messages = [f'{error_json.get("errorMessages")}\n']
                messages.extend([f'{k}:{v}' for k, v in error_json.get('errors').items()])
                message = '\n'.join(messages)
            except json.decoder.JSONDecodeError:
                message = response.text
            raise ProjectException(f'Error during method {method_name}\n{message}')
