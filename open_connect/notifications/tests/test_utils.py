"""Tests for notifications.utils."""
# pylint: disable=attribute-defined-outside-init

from django.db import models
from django.test import TestCase
from mock import patch

from open_connect.notifications import utils


class FakeModel(models.Model):
    """Fake model for testing."""
    somefield = models.TextField()

    class Meta(object):
        managed = False


@patch.object(utils.models, 'get_models')
class GetNotificationModelsTest(TestCase):
    """Tests for get_notification_models."""
    def test_get_notification_models(self, mock):
        """Only notification models are returned by get_notification_models."""
        notification_model = FakeModel()
        notification_model.create_notification = True
        no_attribute_model = FakeModel()
        false_model = FakeModel()
        false_model.create_notification = False
        not_boolean_model = FakeModel()
        not_boolean_model.create_notification = 'unicorns!'
        mock.return_value = [
            notification_model,
            no_attribute_model,
            false_model,
            not_boolean_model
        ]
        result = utils.get_notification_models()
        self.assertEqual(result, [notification_model])
