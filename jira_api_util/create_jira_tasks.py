import os.path

from dotenv import load_dotenv
from lorem_text import lorem

from jira_api_util.jira_utils import JiraAPIHelper
from jira_api_util.utils import LoremFlickrManager, AbstractImageManager


def main(helper: JiraAPIHelper,
         image_manager: AbstractImageManager,
         project_num: int,
         issues_per_project: int,
         attachments_per_issue: int):
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
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    base_url = os.environ.get('BASE_URL')
    jira_admin = os.environ.get('JIRA_ADMIN')
    jira_password = os.environ.get('JIRA_PASSWORD')
    try:
        image_download_timeout = int(os.environ.get('IMAGE_DOWNLOAD_TIMEOUT'))
        project_num = int(os.environ.get('PROJECTS_NUM'))
        issues_per_project = int(os.environ.get('ISSUES_PER_PROJECT'))
        attachments_per_project = int(os.environ.get('COMMENTS_WITH_ATTACHMENTS_PER_ISSUE'))
    except (ValueError, TypeError):
        print('Значение таймаута, номера проектов, задач и вложений должно быть числовым!')
        exit(1)
    if not all((base_url,
                jira_admin,
                jira_password,
                image_download_timeout,
                project_num,
                issues_per_project,
                attachments_per_project)):
        print("Проверьте значения параметров!")
        exit(1)

    h = JiraAPIHelper(base_url,
                      jira_admin,
                      jira_password)
    im = LoremFlickrManager(image_download_timeout)

    main(h,
         im,
         project_num,
         issues_per_project,
         attachments_per_project)
