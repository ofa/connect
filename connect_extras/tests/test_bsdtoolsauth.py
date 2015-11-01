"""Tests for the BSDTools OAuth2 Python-Social-Auth Provider"""
import json

from django.test import TestCase
from django.test.utils import override_settings
from mock import patch
from social.storage.django_orm import BaseDjangoStorage
from social.strategies.django_strategy import DjangoStrategy

from connect_extras.auth_backends.bsdtools import BSDToolsOAuth2


@override_settings(SOCIAL_AUTH_BSDTOOLS_INSTANCE='tools.bluestatedigital.com')
class TestBSDToolsOAuthBackend(TestCase):
    """Tests for BSDToolsOAuth2Backend"""
    def setUp(self):
        """Setup the test"""
        self.backend = BSDToolsOAuth2()

        # We need to use the django strategy to get access to django settings
        self.backend.strategy = DjangoStrategy(BaseDjangoStorage())

    def test_instance_url(self):
        """Ensure that the instance attribute correctly returns"""
        self.assertEqual(self.backend.instance, 'tools.bluestatedigital.com')

    def test_authorization_url(self):
        """Test that the authorization_url method correctly returns"""
        self.assertEqual(
            self.backend.authorization_url(),
            'https://tools.bluestatedigital.com/page/oauth2/authorize')

    def test_access_token_url(self):
        """Test that the access_token_url method correctly returns"""
        self.assertEqual(
            self.backend.access_token_url(),
            'https://tools.bluestatedigital.com/page/oauth2/access-token')

    def test_get_user_details(self):
        """Test that the get_user_details method returns the correct data"""
        user_data_response = json.loads(u'''
            {
                "userid":"john@domain.com",
                "id": "1929",
                "guid": "YxYHXk9rQHhMhrmJobHJymA",
                "firstname":"John",
                "middlename":"D",
                "lastname":"Smith",
                "gender":"M",
                "birth_dt":"1991-04-04 05:00:00",
                "email":[
                    {
                        "email":"john@domain.com",
                        "is_primary":false
                    },
                    {
                        "email":"john.smith@domain.com",
                        "is_primary":true
                    }
                ],
                "address":[
                    {
                        "addr1": "224 North Desplaines Street",
                        "addr2": "Suite 500",
                        "city": "Chicago",
                        "country": "US",
                        "postal_code": "60657"
                    },
                    {
                        "addr1": "123 Front Street",
                        "city": "Milwaukee",
                        "country": "US",
                        "is_primary": true,
                        "postal_code": "53221",
                        "postal_code_ext": "1000",
                        "state_cd": "WI"
                    }
                ],
                "phone":[
                    {
                        "phone":"1112223333",
                        "is_primary":true
                    }
                ]
            }
        ''')
        result = self.backend.get_user_details(user_data_response)

        self.assertDictEqual(result,
            {
                "username": u"1929",
                "email": u"john.smith@domain.com",
                "fullname": u"John Smith",
                "first_name": u"John",
                "last_name": u"Smith"
            })

    def test_partial_user_details(self):
        """Test instances where a full name is not provided"""
        partial_user_data_response = json.loads(u'''
            {
                "userid":"noname@domain.com",
                "id": "1922",
                "guid": "YxYHXk9rQHhMhrmJobHJymA",
                "firstname": "John",
                "email":[
                    {
                        "email":"john@domain.com",
                        "is_primary":false
                    },
                    {
                        "email":"somename@domain.com",
                        "is_primary":true
                    }
                ]
            }
        ''')
        result = self.backend.get_user_details(partial_user_data_response)

        self.assertDictEqual(
            result,
            {
                "username": u"1922",
                "email": u"somename@domain.com",
                "fullname": u"John",
                "first_name": u"John",
                "last_name": u""
            })

    def test_no_name_user_details(self):
        """Test instances where no name is returned"""
        partial_user_data_response = json.loads(u'''
            {
                "userid":"noname@domain.com",
                "id": "1922",
                "guid": "YxYHXk9rQHhMhrmJobHJymA",
                "email":[
                    {
                        "email":"noname@domain.com",
                        "is_primary":true
                    }
                ]
            }
        ''')
        result = self.backend.get_user_details(partial_user_data_response)

        self.assertDictEqual(
            result,
            {
                "username": u"1922",
                "email": u"noname@domain.com",
                "fullname": u"",
                "first_name": u"",
                "last_name": u""
            })

    def test_user_data_request(self):
        """Confirm that the correct user data request is made to BSD"""
        with patch.object(self.backend, 'get_json') as patch_object:
            self.backend.user_data('abcd123')
            patch_object.assert_called_once_with(
                "https://tools.bluestatedigital.com/page/graph/cons",
                params={
                    "access_token": "abcd123"
                }
            )
