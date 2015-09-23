"""Test for Connect view utilities"""
from django.test import TestCase

from open_connect.connect_core.utils.views import JSONResponseMixin


class JSONResponseMixinTest(TestCase):
    """Test the JSONResponse Mixin"""
    def test_render_to_response(self):
        """Test the render_to_response method on the JSON Mixin"""
        mixin = JSONResponseMixin()
        response = mixin.render_to_response(context={'something': 123})
        self.assertEqual(response.content, '{\n    "something": 123\n}')
        self.assertEqual(response['Content-Type'], 'application/json')
