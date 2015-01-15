# pylint: disable=E1103

"""
Run these tests @ Devstack:
    rake fasttest_lms[common/djangoapps/api_manager/organizations/tests.py]
"""
import json
import uuid
import mock
from urllib import urlencode

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, Client
from django.test.utils import override_settings

from gradebook.models import StudentGradebook
from student.models import UserProfile
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
TEST_API_KEY = str(uuid.uuid4())


class SecureClient(Client):

    """ Django test client using a "secure" connection. """

    def __init__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        kwargs.update({'SERVER_PORT': 443, 'wsgi.url_scheme': 'https'})
        super(SecureClient, self).__init__(*args, **kwargs)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
@override_settings(EDX_API_KEY=TEST_API_KEY)
@mock.patch.dict("django.conf.settings.FEATURES", {'ENFORCE_PASSWORD_POLICY': False,
                                                   'ADVANCED_SECURITY': False,
                                                   'PREVENT_CONCURRENT_LOGINS': False
                                                   })
class OrganizationsApiTests(TestCase):

    """ Test suite for Users API views """

    def setUp(self):
        self.test_server_prefix = 'https://testserver'
        self.base_organizations_uri = '/api/server/organizations/'
        self.base_users_uri = '/api/server/users'
        self.base_groups_uri = '/api/server/groups'
        self.test_organization_name = str(uuid.uuid4())
        self.test_organization_display_name = 'Test Org'
        self.test_organization_contact_name = 'John Org'
        self.test_organization_contact_email = 'john@test.org'
        self.test_organization_contact_phone = '+1 332 232 24234'
        self.test_organization_logo_url = 'org_logo.jpg'

        self.test_user_email = str(uuid.uuid4())
        self.test_user_username = str(uuid.uuid4())
        self.test_user = User.objects.create(
            email=self.test_user_email,
            username=self.test_user_username
        )
        profile = UserProfile(user=self.test_user)
        profile.city = 'Boston'
        profile.save()

        self.test_user2 = User.objects.create(
            email=str(uuid.uuid4()),
            username=str(uuid.uuid4())
        )
        profile2 = UserProfile(user=self.test_user2)
        profile2.city = 'NYC'
        profile2.save()

        self.course = CourseFactory.create()
        self.second_course = CourseFactory.create(
            number="899"
        )

        self.client = SecureClient()
        cache.clear()

    def do_post(self, uri, data):
        """Submit an HTTP POST request"""
        headers = {
            'X-Edx-Api-Key': str(TEST_API_KEY),
        }
        json_data = json.dumps(data)

        response = self.client.post(
            uri, headers=headers, content_type='application/json', data=json_data)
        return response

    def do_get(self, uri):
        """Submit an HTTP GET request"""
        headers = {
            'Content-Type': 'application/json',
            'X-Edx-Api-Key': str(TEST_API_KEY),
        }
        response = self.client.get(uri, headers=headers)
        return response

    def do_delete(self, uri):
        """Submit an HTTP DELETE request"""
        headers = {
            'Content-Type': 'application/json',
            'X-Edx-Api-Key': str(TEST_API_KEY),
        }
        response = self.client.delete(uri, headers=headers)
        return response

    def test_organizations_list_post(self):
        users = []
        for i in xrange(1, 6):
            data = {
                'email': 'test{}@example.com'.format(i),
                'username': 'test_user{}'.format(i),
                'password': 'test_pass',
                'first_name': 'John{}'.format(i),
                'last_name': 'Doe{}'.format(i),
                'city': 'Boston',
            }
            response = self.do_post(self.base_users_uri, data)
            self.assertEqual(response.status_code, 201)
            users.append(response.data['id'])

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone,
            'logo_url': self.test_organization_logo_url,
            'users': users
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.data['id'], 0)
        confirm_uri = '{}{}{}/'.format(
            self.test_server_prefix,
            self.base_organizations_uri,
            str(response.data['id'])
        )
        self.assertEqual(response.data['url'], confirm_uri)
        self.assertGreater(response.data['id'], 0)
        self.assertEqual(response.data['name'], self.test_organization_name)
        self.assertEqual(response.data['display_name'], self.test_organization_display_name)
        self.assertEqual(response.data['contact_name'], self.test_organization_contact_name)
        self.assertEqual(response.data['contact_email'], self.test_organization_contact_email)
        self.assertEqual(response.data['contact_phone'], self.test_organization_contact_phone)
        self.assertEqual(response.data['logo_url'], self.test_organization_logo_url)
        self.assertIsNotNone(response.data['workgroups'])
        self.assertEqual(len(response.data['users']), len(users))
        self.assertIsNotNone(response.data['created'])
        self.assertIsNotNone(response.data['modified'])

    def test_organizations_detail_get(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        response = self.do_get(test_uri)
        self.assertEqual(response.status_code, 200)
        confirm_uri = self.test_server_prefix + test_uri
        self.assertEqual(response.data['url'], confirm_uri)
        self.assertGreater(response.data['id'], 0)
        self.assertEqual(response.data['name'], self.test_organization_name)
        self.assertEqual(response.data['display_name'], self.test_organization_display_name)
        self.assertEqual(response.data['contact_name'], self.test_organization_contact_name)
        self.assertEqual(response.data['contact_email'], self.test_organization_contact_email)
        self.assertEqual(response.data['contact_phone'], self.test_organization_contact_phone)
        self.assertIsNotNone(response.data['workgroups'])
        self.assertIsNotNone(response.data['users'])
        self.assertIsNotNone(response.data['created'])
        self.assertIsNotNone(response.data['modified'])

    def test_organizations_detail_get_undefined(self):
        test_uri = '{}123456789/'.format(self.base_organizations_uri)
        response = self.do_get(test_uri)
        self.assertEqual(response.status_code, 404)

    def test_organizations_detail_delete(self):
        data = {'name': self.test_organization_name}
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        response = self.do_get(test_uri)
        self.assertEqual(response.status_code, 200)
        response = self.do_delete(test_uri)
        self.assertEqual(response.status_code, 204)
        response = self.do_get(test_uri)
        self.assertEqual(response.status_code, 404)

    def test_organizations_list_post_invalid(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': 'testatme.com',
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 400)

    def test_organizations_list_post_with_groups(self):
        groups = []
        for i in xrange(1, 6):
            data = {
                'name': '{} {}'.format('Test Group', i),
                'type': 'series',
                'data': {'display_name': 'My first series'}
            }
            response = self.do_post(self.base_groups_uri, data)
            self.assertEqual(response.status_code, 201)
            groups.append(response.data['id'])

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'groups': groups
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['groups']), len(groups))

    def test_organizations_users_post(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        data = {"id": self.test_user.id}
        response = self.do_post(users_uri, data)
        self.assertEqual(response.status_code, 201)
        response = self.do_get(test_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users'][0], self.test_user.id)

    def test_organizations_users_post_invalid_user(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        data = {"id": 123456}
        response = self.do_post(users_uri, data)
        self.assertEqual(response.status_code, 400)

    def test_organizations_groups_get_post(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        org_id = response.data['id']

        # create groups
        max_groups, groups, contactgroup_count = 4, [], 2
        for i in xrange(1, max_groups + 1):
            grouptype = 'contactgroup' if i <= contactgroup_count else 'series'
            data = {
                'name': '{} {}'.format('Test Group', i),
                'type': grouptype,
                'data': {'display_name': 'organization contacts group'}
            }
            response = self.do_post(self.base_groups_uri, data)
            self.assertEqual(response.status_code, 201)
            groups.append(response.data['id'])

        test_uri = '{}{}/'.format(self.base_organizations_uri, org_id)
        groups_uri = '{}groups/'.format(test_uri)
        for group in groups:
            data = {"id": group}
            response = self.do_post(groups_uri, data)
            self.assertEqual(response.status_code, 201)
        response = self.do_get(groups_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), max_groups)

        # get organization groups with type filter
        response = self.do_get('{}?type=contactgroup'.format(groups_uri))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), contactgroup_count)

        # post an invalid group
        data = {"id": '45533333'}
        response = self.do_post(groups_uri, data)
        self.assertEqual(response.status_code, 400)

    def test_organizations_users_get(self):
        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        data = {"id": self.test_user.id}
        response = self.do_post(users_uri, data)
        self.assertEqual(response.status_code, 201)
        response = self.do_get(users_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], self.test_user.id)
        self.assertEqual(response.data[0]['username'], self.test_user.username)
        self.assertEqual(response.data[0]['email'], self.test_user.email)

    def test_organizations_users_get_with_course_count(self):
        CourseEnrollmentFactory.create(user=self.test_user, course_id=self.course.id)
        CourseEnrollmentFactory.create(user=self.test_user2, course_id=self.course.id)
        CourseEnrollmentFactory.create(user=self.test_user, course_id=self.second_course.id)

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        data = {"id": self.test_user.id}
        response = self.do_post(users_uri, data)
        self.assertEqual(response.status_code, 201)

        data = {"id": self.test_user2.id}
        response = self.do_post(users_uri, data)
        self.assertEqual(response.status_code, 201)
        response = self.do_get('{}{}'.format(users_uri, '?include_course_counts=True'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], self.test_user.id)
        self.assertEqual(response.data[0]['course_count'], 2)
        self.assertEqual(response.data[1]['id'], self.test_user2.id)
        self.assertEqual(response.data[1]['course_count'], 1)

    def test_organizations_users_get_with_grades(self):
        # Create 4 users
        user_course = 4
        users_completed = 2
        users = [UserFactory.create(username="testuser" + str(__), profile='test') for __ in xrange(user_course)]
        for i, user in enumerate(users):
            CourseEnrollmentFactory.create(user=user, course_id=self.course.id)
            grades = (0.75, 0.85)
            # mark 3 users as who completed course and 1 who did not
            if i < users_completed:
                grades = (0.90, 0.91)
            StudentGradebook.objects.create(user=user, course_id=self.course.id, grade=grades[0],
                                            proforma_grade=grades[1])

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone
        }
        response = self.do_post(self.base_organizations_uri, data)
        self.assertEqual(response.status_code, 201)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        for user in users:
            data = {"id": user.id}
            response = self.do_post(users_uri, data)
            self.assertEqual(response.status_code, 201)
        response = self.do_get('{}?{}&course_id={}'.format(users_uri, 'include_grades=True', self.course.id))
        self.assertEqual(response.status_code, 200)
        complete_count = len([user for user in response.data if user['complete_status']])
        self.assertEqual(complete_count, users_completed)
        grade_sum = sum([user['grade'] for user in response.data])
        proforma_grade_sum = sum([user['proforma_grade'] for user in response.data])
        self.assertEqual(grade_sum, 0.75 + 0.75 + 0.9 + 0.9)
        self.assertEqual(proforma_grade_sum, 0.85 + 0.85 + 0.91 + 0.91)

    def test_organizations_metrics_get(self):
        users = []
        for i in xrange(1, 6):
            data = {
                'email': 'test{}@example.com'.format(i),
                'username': 'test_user{}'.format(i),
                'password': 'test_pass',
                'first_name': 'John{}'.format(i),
                'last_name': 'Doe{}'.format(i),
                'city': 'Boston',
            }
            response = self.do_post(self.base_users_uri, data)
            self.assertEqual(response.status_code, 201)
            user_id = response.data['id']
            user = User.objects.get(pk=user_id)
            users.append(user_id)
            CourseEnrollmentFactory.create(user=user, course_id=self.course.id)
            if i < 2:
                StudentGradebook.objects.create(user=user, course_id=self.course.id, grade=0.75, proforma_grade=0.85)
            elif i < 4:
                StudentGradebook.objects.create(user=user, course_id=self.course.id, grade=0.82, proforma_grade=0.82)
            else:
                StudentGradebook.objects.create(user=user, course_id=self.course.id, grade=0.90, proforma_grade=0.91)

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone,
            'logo_url': self.test_organization_logo_url,
            'users': users
        }
        response = self.do_post(self.base_organizations_uri, data)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        metrics_uri = '{}metrics/'.format(test_uri)
        response = self.do_get(metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_average'], 0.838)
        self.assertEqual(response.data['users_grade_complete_count'], 4)

    def test_organizations_metrics_get_courses_filter(self):
        users = []
        for i in xrange(1, 12):
            data = {
                'email': 'test{}@example.com'.format(i),
                'username': 'test_user{}'.format(i),
                'password': 'test_pass',
                'first_name': 'John{}'.format(i),
                'last_name': 'Doe{}'.format(i),
                'city': 'Boston',
            }
            response = self.do_post(self.base_users_uri, data)
            self.assertEqual(response.status_code, 201)
            user_id = response.data['id']
            user = User.objects.get(pk=user_id)
            users.append(user_id)
            course1 = CourseFactory.create(display_name="COURSE1", org="CRS1", run="RUN1")
            course2 = CourseFactory.create(display_name="COURSE2", org="CRS2", run="RUN2")
            course3 = CourseFactory.create(display_name="COURSE3", org="CRS3", run="RUN3")
            if i < 3:
                CourseEnrollmentFactory.create(user=user, course_id=course1.id)
                StudentGradebook.objects.create(user=user, grade=0.75, proforma_grade=0.85, course_id=course1.id)
            elif i < 5:
                CourseEnrollmentFactory.create(user=user, course_id=course2.id)
                StudentGradebook.objects.create(user=user, grade=0.82, proforma_grade=0.82, course_id=course2.id)
            elif i < 7:
                CourseEnrollmentFactory.create(user=user, course_id=course3.id)
                StudentGradebook.objects.create(user=user, grade=0.72, proforma_grade=0.78, course_id=course3.id)
            elif i < 9:
                CourseEnrollmentFactory.create(user=user, course_id=course1.id)
                StudentGradebook.objects.create(user=user, grade=0.94, proforma_grade=0.67, course_id=course1.id)
            elif i < 11:
                CourseEnrollmentFactory.create(user=user, course_id=course2.id)
                StudentGradebook.objects.create(user=user, grade=0.90, proforma_grade=0.91, course_id=course2.id)
            else:
                # Not started student - should be considered incomplete
                CourseEnrollmentFactory.create(user=user, course_id=course2.id)
                StudentGradebook.objects.create(user=user, grade=0.00, proforma_grade=0.00, course_id=course2.id)

        data = {
            'name': self.test_organization_name,
            'display_name': self.test_organization_display_name,
            'contact_name': self.test_organization_contact_name,
            'contact_email': self.test_organization_contact_email,
            'contact_phone': self.test_organization_contact_phone,
            'logo_url': self.test_organization_logo_url,
            'users': users
        }

        response = self.do_post(self.base_organizations_uri, data)
        test_uri = '{}{}/'.format(self.base_organizations_uri, str(response.data['id']))
        users_uri = '{}users/'.format(test_uri)
        metrics_uri = '{}metrics/'.format(test_uri)
        response = self.do_get(metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_complete_count'], 6)
        self.assertEqual(response.data['users_grade_average'], 0.751)


        courses = {'courses': unicode(course1.id)}
        filtered_metrics_uri = '{}?{}'.format(metrics_uri, urlencode(courses))
        response = self.do_get(filtered_metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_complete_count'], 2)
        self.assertEqual(response.data['users_grade_average'], 0.845)

        courses = {'courses': unicode(course2.id)}
        filtered_metrics_uri = '{}?{}'.format(metrics_uri, urlencode(courses))
        response = self.do_get(filtered_metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_complete_count'], 4)
        self.assertEqual(response.data['users_grade_average'], 0.688)

        courses = {'courses': '{},{}'.format(course1.id, course2.id)}
        filtered_metrics_uri = '{}?{}'.format(metrics_uri, urlencode(courses))
        response = self.do_get(filtered_metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_complete_count'], 6)
        self.assertEqual(response.data['users_grade_average'], 0.758)

        courses = {'courses': '{}'.format(self.course.id)}
        filtered_metrics_uri = '{}?{}'.format(metrics_uri, urlencode(courses))
        response = self.do_get(filtered_metrics_uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['users_grade_complete_count'], 0)
        self.assertEqual(response.data['users_grade_average'], 0)