"""Tests for utils/models.py"""
from datetime import datetime

from django.test import TestCase
from mock import Mock

from open_connect.connect_core.utils.models import CacheMixinModel


class TestCacheModelMixin(TestCase):
    """Tests for CacheModelMixin"""
    def test_cache_key(self):
        """Test the cache_key property"""
        mixin = CacheMixinModel()
        mock_meta = Mock()
        mock_meta.app_label = 'aca'
        mock_meta.model_name = 'HealthcareStories'
        # pylint: disable=protected-access
        mixin._meta = mock_meta

        # pylint: disable=invalid-name
        mixin.pk = 8200000

        mixin.modified_at = datetime(2012, 6, 28, 3, 6, 40, 508700)

        self.assertEqual(
            mixin.cache_key,
            u'modelkey-aca-healthcarestories-1-8200000-2012-06-28-030640508700'
        )
