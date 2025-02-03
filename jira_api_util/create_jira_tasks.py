from jira_api_util.jira_utils import JiraAPIHelper
from jira_api_util.utils import LoremFlickrManager, ImageManager


def main(helper: JiraAPIHelper, image_manager: ImageManager):
    project_num = 3
    issues_per_project = 5
    comments_per_project = 5
    project_dicts = []
    for i in range(project_num):
        project_dicts.append(helper.create_project(f'TEST-PROJECT{i}',
                                                   'software',
                                                   'admin'))
    issue_dicts = []
    for pd in project_dicts:
        for i in range(issues_per_project):
            pass  # add issue to project

    for issue in issue_dicts:
        for i in range(comments_per_project):
            pass  # add attachment and comment with link to attachment (optional)


if __name__ == '__main__':
    h = JiraAPIHelper('http://127.0.0.1:8080/rest/api/latest', 'admin', 'Qwerty123')
    im = LoremFlickrManager()
    main(h, im)
