from lorem_text import lorem

from jira_api_util.jira_utils import JiraAPIHelper
from jira_api_util.utils import LoremFlickrManager, ImageManager


def main(helper: JiraAPIHelper, image_manager: ImageManager):
    project_num = 3
    issues_per_project = 5
    attachments_per_issue = 5
    projects = []
    for i in range(project_num):
        projects.append(helper.create_project(f'TESTPR{i}',
                                              'software',
                                              'admin'))
    issues = []
    for project in projects:
        for i in range(issues_per_project):
            issues.append(helper.create_issue(project.key,
                                              lorem.words(2),
                                              lorem.words(5),
                                              'Task'))
    for issue in issues:
        attachments = []
        for i in range(attachments_per_issue):
            img_bytes = image_manager.get_random_image(300, 300)
            attachments.append(helper.add_attachment(issue.id,
                                                     img_bytes,
                                                     f'{lorem.words(1)}.png'))
        for attachment in attachments:
            helper.add_comment_to_issue(issue.id,
                                        f'{lorem.sentence()} !{attachment.filename}!')


if __name__ == '__main__':
    h = JiraAPIHelper('http://127.0.0.1:8080/rest/api/latest', 'admin', 'Qwerty123')
    im = LoremFlickrManager()
    main(h, im)
