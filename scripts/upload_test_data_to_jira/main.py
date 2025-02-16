import argparse

from jira_utils import JiraAPIAdapter
from lorem_text import lorem
from utils import AbstractImageManager, LoremFlickrManager


def main(
    adapter: JiraAPIAdapter,
    image_manager: AbstractImageManager,
    project_num: int,
    issues_per_project: int,
    attachments_per_issue: int,
    project_name: str,
):
    projects = []
    for i in range(project_num):
        projects.append(adapter.create_project(f'{project_name}{i}', 'software', 'admin'))
    issues = []
    for project in projects:
        for i in range(issues_per_project):
            issues.append(adapter.create_issue(project.key, lorem.words(2), lorem.words(5), 'Task'))
    for issue in issues:
        attachments = []
        for i in range(attachments_per_issue):
            img_bytes = image_manager.get_random_image(300, 300)
            attachments.append(adapter.add_attachment(issue.issue_id, img_bytes, f'{lorem.words(1)}.png'))
        for attachment in attachments:
            adapter.add_comment_to_issue(issue.issue_id, f'{lorem.sentence()} !{attachment.filename}!')


def get_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Скрипт для наполнения Jira тестовыми данными через RESP API')
    p.add_argument(
        '-b',
        '--base-url',
        dest='base_url',
        help='URL Jira REST API, пример: http://127.0.0.1:8080/rest/api/latest',
        required=True,
    )
    p.add_argument(
        '-U',
        '--user',
        dest='jira_admin',
        help='Имя пользователя Jira',
        required=True,
    )
    p.add_argument(
        '-P',
        '--password',
        dest='jira_password',
        help='Пароль пользователя Jira',
        required=True,
    )
    p.add_argument(
        '--project-prefix',
        dest='jira_test_project_name',
        help='Префикс для новых проектов',
        default='testproject',
    )
    p.add_argument(
        '--projects-num',
        dest='project_num',
        help='Количество создаваемых проектов',
        type=int,
        required=True,
    )
    p.add_argument(
        '--issues-per-project',
        dest='issues_per_project',
        help='Количество issue на проект',
        type=int,
        required=True,
    )
    p.add_argument(
        '--attachments-per-issue',
        dest='attachments_per_issue',
        help='Количество вложений и комментариев с их упоминанием',
        type=int,
        required=True,
    )
    p.add_argument(
        '--image-download-timeout',
        dest='image_download_timeout',
        help='Пауза между загрузками изображений из стороннего сервиса',
        type=int,
        default=3,
    )

    return p


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    h = JiraAPIAdapter(args.base_url, args.jira_admin, args.jira_password)
    im = LoremFlickrManager(args.image_download_timeout)

    main(
        h,
        im,
        args.project_num,
        args.issues_per_project,
        args.attachments_per_issue,
        args.jira_test_project_name,
    )
