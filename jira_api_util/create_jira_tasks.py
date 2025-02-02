from jira_api_util.jira_utils import JiraAPIHelper
from jira_api_util.utils import LoremFlickrManager, ImageManager


def main(helper: JiraAPIHelper, im: ImageManager):
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
    # helper.create_issue()
    print(helper.add_comment_to_issue('TEST-24', 'test comment'))


if __name__ == '__main__':
    h = JiraAPIHelper('http://127.0.0.1:8080/rest/api/latest', 'admin', 'Qwerty123')
    im = LoremFlickrManager()
    main(h, im)
