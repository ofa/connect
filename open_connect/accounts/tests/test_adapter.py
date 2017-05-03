# -*- coding: utf-8 -*-
"""Test Connect's django-allauth adapter"""
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch

from open_connect.connect_core.utils.basetests import ConnectTestMixin


class TestAllauthAdapter(TestCase, ConnectTestMixin):
    """Test the Django Allauth Adapter"""

    @override_settings(
        DEFAULT_FROM_EMAIL='Dummy From <dummy@from.local>',
        ACCOUNT_IGNORE_UNSUBSCRIBE=True)
    def test_render_mail(self):
        """Test rendering mail"""
        # We import AccountAdapter inside the test so the override_settings()
        # will impact which backend is actually chosen by the adapter
        from open_connect.accounts.adapter import AccountAdapter
        from open_connect.mailer.backend import DefaultBackend

        user = self.create_user(email='adaptertest@example.local')

        adapter = AccountAdapter()
        template_prefix = 'account/email/email_confirmation'
        email = 'adaptertest@example.local'
        context = {
            'user': user
        }
        message = adapter.render_mail(template_prefix, email, context)

        # Confirm the connection is actually our fake backend and not the
        # custom Connect backend. This is true due to the
        # `ACCOUNT_IGNORE_UNSUBSCRIBE` variable being true
        self.assertIsInstance(message.connection, DefaultBackend)

        self.assertEqual(message.from_email, 'Dummy From <dummy@from.local>')
        self.assertEqual(message.to, ['adaptertest@example.local'])

        # Confirm the HTML version was attached
        self.assertEqual(message.alternatives[0][1], 'text/html')

        # Confirm the unsubscribe URL is in both the plain text and HTML body
        self.assertIn(user.unsubscribe_url, message.body)
        self.assertIn(user.unsubscribe_url, message.alternatives[0][0])

    @override_settings(ACCOUNT_IGNORE_UNSUBSCRIBE=False)
    def test_render_mail_connectbackend(self):
        """Test the Connect-unsubscribe-respecting backend toggle setting"""
        from open_connect.accounts.adapter import AccountAdapter
        from open_connect.mailer.backend import ConnectMailerBackend
        user = self.create_user(email='adaptertest2@example.local')

        adapter = AccountAdapter()
        template_prefix = 'account/email/email_confirmation'
        email = 'adaptertest2@example.local'
        context = {
            'user': user
        }
        message = adapter.render_mail(template_prefix, email, context)

        self.assertIsInstance(message.connection, ConnectMailerBackend)

    @patch('open_connect.accounts.adapter.render_to_string')
    def test_render_mail_template_engine(self, mock):
        """Test the calls to `render_to_string` in render_mail"""
        from open_connect.accounts.adapter import AccountAdapter
        user = self.create_user(email='adaptertest3@example.local')

        adapter = AccountAdapter()
        template_prefix = 'test/template/prefix'
        email = 'adaptertest3@example.local'
        input_context = {
            'user': user
        }

        # Return separate template responses for each of the 3 calls to
        # `render_to_strong`
        mock.side_effect = [
            # In order to test our string manipulation we'll add a few
            # linebreaks and additional spaces to the subject template response
            ' Subject\nReturn\n ',
            'Text Return',
            # To test unicode support, add an emoji
            u'HTML Return 😀'
        ]

        message = adapter.render_mail(template_prefix, email, input_context)

        # Make sure each call was correctly done and inserted into the message
        self.assertEqual(message.subject, 'Subject Return')
        self.assertEqual(message.body, 'Text Return')
        self.assertEqual(message.alternatives[0][0], u'HTML Return 😀')

        # Make sure only 3 `render_to_string` calls were done
        self.assertEqual(mock.call_count, 3)

        # Generat a dictionary of the context expected to be passed into the
        # template engine
        expected_context = {
            'email': 'adaptertest3@example.local',
            'user': user,
            'recipient': user
        }

        # Check each call to `render_to_string`
        subject_call_args = mock.call_args_list[0][0]
        self.assertEqual(
            subject_call_args[0], 'test/template/prefix_subject.txt')
        self.assertDictEqual(subject_call_args[1], expected_context)

        text_email_call_args = mock.call_args_list[1][0]
        self.assertEqual(
            text_email_call_args[0], 'test/template/prefix_message.txt')
        self.assertDictEqual(text_email_call_args[1], expected_context)

        html_email_call_args = mock.call_args_list[2][0]
        self.assertEqual(
            html_email_call_args[0], 'test/template/prefix_message.html')
        self.assertDictEqual(html_email_call_args[1], expected_context)
