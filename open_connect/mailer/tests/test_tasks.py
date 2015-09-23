"""Test for mailer tasks"""
# pylint: disable=invalid-name
from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now
from model_mommy import mommy

from open_connect.mailer.models import EmailOpen
from open_connect.mailer import tasks


class TestWipeOldEmailOpens(TestCase):
    """Tests for wipe_old_email_opens"""
    def setUp(self):
        """Setup the TestWipeOldEmailOpens TestCase"""
        self.now = now()
        self.month_ago = self.now - timedelta(days=30)

    def test_wipes_old_email(self):
        """Test that old emails are wiped"""
        latest_email_open = mommy.prepare(EmailOpen)
        latest_email_open.user_agent = ''
        latest_email_open.save()

        old_email_open = mommy.prepare(EmailOpen)
        old_email_open.user_agent = ''
        old_email_open.opened_at = self.month_ago
        old_email_open.save()

        # As the database will always update with the last modified at time we
        # need to do an `UPDATE` operation in the database to change the time
        # the open was created.
        EmailOpen.objects.filter(
            pk=old_email_open.pk).update(opened_at=self.month_ago)

        all_email_opens_pre = EmailOpen.objects.all()

        self.assertIn(latest_email_open, all_email_opens_pre)
        self.assertIn(old_email_open, all_email_opens_pre)

        tasks.wipe_old_email_opens()

        all_email_opens_post = EmailOpen.objects.all()
        self.assertIn(latest_email_open, all_email_opens_post)
        self.assertNotIn(old_email_open, all_email_opens_post)
