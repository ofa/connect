# -*- coding: utf-8 -*-
"""Tests for SortableListMixin"""

# pylint: disable=invalid-name
from datetime import datetime
import string

from django.db import models
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils.timezone import make_aware, get_current_timezone
from mock import patch
from model_mommy import mommy

from open_connect.accounts.models import Invite
from open_connect.connect_core.utils.forms import (
    DateTimeRangeForm, PaginateByForm
)
from open_connect.connect_core.utils.mixins import (
    DateTimeRangeListMixin,
    SortableListMixin,
    PaginateByMixin,
    SanitizeHTMLMixin,
    handle_breaks
)


TEST_HTML = u'''
    <strong>Bold</strong><br>
    <em>Italic<br></em> Hey<br/> Yeah
    <a href="http://www.razzmatazz.local">Link<br>
    <img src="https://secure.assets.bostatic.com/hydepark/images/read-my
    -cape.png" alt="awesome">
    <img src="https://secure.assets.bostatic.com/hydepark/images/read-my
    -cape.png" alt="awesome"
    style="border-width: 10px;" width=15px height=1230px></a><br>
    <iframe href="https://roguesite.com/roguescript.xhtml"></iframe>
    <h1>Headline 1</h1> <h2>Headline 2</h2> <script>/* badcode */</script>
      Bad Headline
    <a href="mailto:some@user.local">hi</a>
    <a href="https://thisiscool.com">something</a>
    <a href="ftp://badperson.exe">this is totally legitsies</a>
    <a href="javascript:alert('boo!');">click me</a>
    <iframe hrf="http://www.google.com" width=10 height="15">
    <div style="display: none">Hidden style</div>
    <strong>Unicode test<br>à á â ã ä å æ ç è é ê ë ì í î ï ð ñ ò ó<br>Ⴕ
     Ⴖ Ⴗ Ⴘ Ⴙ Ⴚ
    </strong> Ⴛ Ⴜ Ⴝ Ⴞ Ⴟ Ⴠ<br>
    Testing     Whitespace and                      tab
    <img src="http://badbadsite.com/someimage.jpg">
    Testing<br/><br/><br/>
    Multiple Lines
    <img src="http://localhost/fantastic.jpg" data-embed="cool_embed">
    <img src="http://localhost/big.jpg" style="display: none;">
    <!-- vars:redactor=true -->
'''

DIRTY_SAFE_HTML = u'''
<br/>Break At Start
    Testing     Whitespace and                      tab

    Testing<br/><br/><br/>
    Multiple Lines

    Ⴚ Unicode

    Multiple <br/> breaks
    <br/><br/><br/>

	Hey<br/> Yeah


	


Breaks at end<br/><br/>
<!-- vars:redactor=true -->
'''

PLAIN_TEXT_MESSAGE = u'''Line 1

Line 3



Line 7


'''


class FakeModel(models.Model):
    """Fake model for testing."""
    cookies = models.CharField(blank=True)
    datetime = models.DateTimeField(blank=True, null=True)

    _default_manager = models.Manager()

    class Meta(object):
        """Meta options for FakeModel. Ensure that the model isn't created"""
        abstract = True


class DateTimeRangeListMixinTest(TestCase):
    """Tests for DateTimeRangeListMixin."""
    def setUp(self):
        """Setup the DateTimeRangeListMixinTest TestCase"""
        self.request_factory = RequestFactory()

    def test_get_date_range_form(self):
        """Test form creation."""
        mixin = DateTimeRangeListMixin()
        mixin.request = self.request_factory.get(
            '/?start_datetime=2013-01-01 12:01 am'
            '&end_datetime=2013-12-31 11:59 pm'
        )
        form = mixin.get_date_range_form()
        self.assertIsInstance(form, DateTimeRangeForm)
        self.assertEqual(
            form.initial['start_datetime'],
            u'2013-01-01 12:01 am'
        )
        self.assertEqual(
            form.initial['end_datetime'],
            u'2013-12-31 11:59 pm'
        )

    def test_get_date_range_form_kwargs(self):
        """Test getting form kwargs."""
        mixin = DateTimeRangeListMixin()
        mixin.request = self.request_factory.get(
            '/?start_datetime=2013-01-01 12:01 am'
            '&end_datetime=2013-12-31 11:59 pm'
        )
        kwargs = mixin.get_date_range_form_kwargs()
        self.assertEqual(
            kwargs['initial']['start_datetime'],
            u'2013-01-01 12:01 am'
        )
        self.assertEqual(
            kwargs['initial']['end_datetime'],
            u'2013-12-31 11:59 pm'
        )

    def test_get_date_range_form_initial(self):
        """Test getting form initial values."""
        mixin = DateTimeRangeListMixin()
        mixin.request = self.request_factory.get(
            '/?start_datetime=2013-01-01 12:01 am'
            '&end_datetime=2013-12-31 11:59 pm'
        )
        initial = mixin.get_date_range_form_initial()
        self.assertEqual(initial['start_datetime'], u'2013-01-01 12:01 am')
        self.assertEqual(initial['end_datetime'], u'2013-12-31 11:59 pm')

    def test_get_context_data(self):
        """Test adding form to context."""
        mixin = DateTimeRangeListMixin()
        mixin.request = self.request_factory.get('/')
        self.assertIsInstance(
            mixin.get_context_data()['date_range_form'], DateTimeRangeForm)

    def test_get_queryset(self):
        """Test updating queryset to filter by start and end date/times."""
        # Using invite because it's one of the easier models in Connect to
        # quickly create a timestamped instance with.
        timezone = get_current_timezone()
        invite1 = mommy.make(Invite)
        invite1.created_at = make_aware(
            datetime(2012, 12, 31, 23, 59), timezone)
        invite1.save()
        invite2 = mommy.make(Invite)
        invite2.created_at = make_aware(
            datetime(2013, 06, 01, 00, 01), timezone)
        invite2.save()
        invite3 = mommy.make(Invite)
        invite3.created_at = make_aware(
            datetime(2014, 01, 01, 00, 01), timezone)
        invite3.save()

        # Get the queryset
        mixin = DateTimeRangeListMixin()
        mixin.model = Invite
        mixin.request = self.request_factory.get(
            '/?start_datetime=2013-01-01 12:01 am'
            '&end_datetime=2013-12-31 11:59 pm'
        )
        queryset = mixin.get_queryset()
        self.assertNotIn(invite1, queryset)
        self.assertIn(invite2, queryset)
        self.assertNotIn(invite3, queryset)

    def test_get_queryset_only_start_date(self):
        """Test updating queryset when only start date is provided."""
        # Using invite because it's one of the easier models in Connect to
        # quickly create a timestamped instance with.
        timezone = get_current_timezone()
        invite1 = mommy.make(Invite)
        invite1.created_at = make_aware(
            datetime(2012, 12, 31, 23, 59), timezone)
        invite1.save()
        invite2 = mommy.make(Invite)
        invite2.created_at = make_aware(
            datetime(2013, 06, 01, 00, 01), timezone)
        invite2.save()
        invite3 = mommy.make(Invite)
        invite3.created_at = make_aware(
            datetime(2014, 01, 01, 00, 01), timezone)
        invite3.save()

        # Get the queryset
        mixin = DateTimeRangeListMixin()
        mixin.model = Invite
        mixin.request = self.request_factory.get(
            '/?start_datetime=2013-01-01 12:01 am'
        )
        queryset = mixin.get_queryset()
        self.assertNotIn(invite1, queryset)
        self.assertIn(invite2, queryset)
        self.assertIn(invite3, queryset)

    def test_get_queryset_only_end_date(self):
        """Test updating queryset when only end date is provided."""
        # Using invite because it's one of the easier models in Connect to
        # quickly create a timestamped instance with.
        timezone = get_current_timezone()
        invite1 = mommy.make(Invite)
        invite1.created_at = make_aware(
            datetime(2012, 12, 31, 23, 59), timezone)
        invite1.save()
        invite2 = mommy.make(Invite)
        invite2.created_at = make_aware(
            datetime(2013, 06, 01, 00, 01), timezone)
        invite2.save()
        invite3 = mommy.make(Invite)
        invite3.created_at = make_aware(
            datetime(2014, 01, 01, 00, 01), timezone)
        invite3.save()

        # Get the queryset
        mixin = DateTimeRangeListMixin()
        mixin.model = Invite
        mixin.request = self.request_factory.get(
            '/?end_datetime=2013-12-31 11:59 pm'
        )
        queryset = mixin.get_queryset()
        self.assertIn(invite1, queryset)
        self.assertIn(invite2, queryset)
        self.assertNotIn(invite3, queryset)

    def test_get_queryset_no_dates_provided(self):
        """Test what happens if neither start or end date/time are provided."""
        # Using invite because it's one of the easier models in Connect to
        # quickly create a timestamped instance with.
        timezone = get_current_timezone()
        invite1 = mommy.make(Invite)
        invite1.created_at = make_aware(
            datetime(2012, 12, 31, 23, 59), timezone)
        invite1.save()
        invite2 = mommy.make(Invite)
        invite2.created_at = make_aware(
            datetime(2013, 06, 01, 00, 01), timezone)
        invite2.save()
        invite3 = mommy.make(Invite)
        invite3.created_at = make_aware(
            datetime(2014, 01, 01, 00, 01), timezone)
        invite3.save()

        # Get the queryset
        mixin = DateTimeRangeListMixin()
        mixin.model = Invite
        mixin.request = self.request_factory.get('')
        queryset = mixin.get_queryset()
        self.assertIn(invite1, queryset)
        self.assertIn(invite2, queryset)
        self.assertIn(invite3, queryset)


class PaginateByMixinTest(TestCase):
    """Tests for PaginateByMixin."""
    def setUp(self):
        """Setup the PaginateByMixinTest TestCase"""
        self.request_factory = RequestFactory()

    def test_get_paginate_form(self):
        """Test form creation."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/?per_page=100')
        form = mixin.get_paginate_form()
        self.assertIsInstance(form, PaginateByForm)
        self.assertEqual(form.initial['per_page'], '100')

    def test_get_paginate_form_kwargs(self):
        """Test getting form kwargs."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/?per_page=100')
        kwargs = mixin.get_paginate_form_kwargs()
        self.assertEqual(kwargs['initial']['per_page'], '100')

    def test_get_paginate_form_initial(self):
        """Test getting form initial values."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/?per_page=100')
        initial = mixin.get_paginate_form_initial()
        self.assertEqual(initial['per_page'], '100')

    def test_get_context_data(self):
        """Test adding form to context."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/')
        self.assertIsInstance(
            mixin.get_context_data()['paginate_by_form'], PaginateByForm)

    def test_get_paginate_by(self):
        """Test get_paginate_by."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/?per_page=100')
        self.assertEqual(mixin.get_paginate_by([]), 100)

    def test_get_paginate_by_not_in_querystring(self):
        """Test get_paginate_by when per_page is not provided."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/')
        self.assertEqual(mixin.get_paginate_by([]), None)

    def test_get_paginate_by_not_digit(self):
        """Test get_get_paginate_by when per_page is not a digit."""
        mixin = PaginateByMixin()
        mixin.request = self.request_factory.get('/?per_page=abc')
        self.assertEqual(mixin.get_paginate_by([]), None)


class SortableListMixinTest(TestCase):
    """Tests for SortableListMixin"""
    def setUp(self):
        """Setup the SortableListMixinTest TestCase"""
        self.request_factory = RequestFactory()

    def test_get_context_sort_string_name(self):
        """get_context_sort_string_name() should return 'sort_strings'."""
        mixin = SortableListMixin()
        self.assertEqual(mixin.get_context_sort_string_name(), 'sort_strings')

    def test_get_queryset_sort_asc(self):
        """Test get_queryset with sort asc."""
        mixin = SortableListMixin()
        mixin.model = FakeModel
        mixin.request = self.request_factory.get('/?sort=asc')
        response = mixin.get_queryset()
        self.assertEqual(response.query.order_by, ['pk'])

    def test_get_queryset_sort_desc(self):
        """Test get_queryset with sort desc."""
        mixin = SortableListMixin()
        mixin.model = FakeModel
        mixin.request = self.request_factory.get('/?sort=desc')
        response = mixin.get_queryset()
        self.assertEqual(response.query.order_by, ['-pk'])

    def test_get_queryset_sort_not_valid(self):
        """Test get_queryset with an invalid sort option."""
        mixin = SortableListMixin()
        mixin.model = FakeModel
        mixin.default_sort = 'asc'
        mixin.request = self.request_factory.get('/?sort=blah')
        response = mixin.get_queryset()
        self.assertEqual(response.query.order_by, ['pk'])

    def test_get_queryset_order_by_valid(self):
        """Test get_queryset with a valid order_by value."""
        mixin = SortableListMixin()
        mixin.model = FakeModel
        mixin.valid_order_by = ['cookies']
        mixin.request = self.request_factory.get('/?order_by=cookies')
        response = mixin.get_queryset()
        self.assertEqual(response.query.order_by, ['cookies'])

    def test_get_queryset_order_by_invalid(self):
        """Test get_queryset with an invalid order_by value."""
        mixin = SortableListMixin()
        mixin.model = FakeModel
        mixin.valid_order_by = ['cookies']
        mixin.default_order_by = 'cookies'
        mixin.default_sort = 'desc'
        mixin.request = self.request_factory.get('/?order_by=brownies')
        response = mixin.get_queryset()
        self.assertEqual(response.query.order_by, ['-cookies'])

    def test_get_query_string(self):
        """Test get_query_string."""
        mixin = SortableListMixin()
        mixin.request = self.request_factory.get(
            '?cow=moo&order_by=thing&sort=asc&coffee=needed')
        result = mixin.get_query_string()
        self.assertEqual(result, 'coffee=needed&cow=moo')

    def test_get_sort_strings(self):
        """Test get_sort_strings."""
        mixin = SortableListMixin()
        mixin.request = self.request_factory.get('/')
        mixin.valid_order_by = ['coffee', 'cow']
        result = mixin.get_sort_strings('coffee=needed&me=hungry')
        self.assertEqual(
            result,
            {'coffee': '?order_by=coffee&sort=asc&coffee=needed&me=hungry',
             'cow': '?order_by=cow&sort=asc&coffee=needed&me=hungry'}
        )

    def test_get_sort_strings_existing_order_by_sort_is_inverted(self):
        """Test that order_by field has an inverted sort in sort strings."""
        mixin = SortableListMixin()
        mixin.request = self.request_factory.get('/?order_by=coffee')
        mixin.valid_order_by = ['coffee', 'cow']
        result = mixin.get_sort_strings('coffee=needed&me=hungry')
        self.assertEqual(
            result,
            {'coffee': '?order_by=coffee&sort=desc&coffee=needed&me=hungry',
             'cow': '?order_by=cow&sort=asc&coffee=needed&me=hungry'}
        )

    def test_get_context_data(self):
        """Test get_context_data."""
        mixin = SortableListMixin()
        mixin.request = self.request_factory.get('/?order_by=coffee&me=hungry')
        mixin.valid_order_by = ['coffee']
        result = mixin.get_context_data(object_list=[])
        self.assertEqual(result['query_string'], 'me=hungry')
        self.assertEqual(result['sort_strings'], {
            'coffee': '?order_by=coffee&sort=desc&me=hungry'})


class SanitizeHTMLMixinTest(TestCase):
    """Tests for SanitizeHTMLMixin."""
    def setUp(self):
        """Setup SanitizeHTMLMixin Test"""
        self.mixin = SanitizeHTMLMixin()

    @patch('open_connect.connect_core.utils.mixins.clean_html', return_value='')
    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_sanitize_html_text_calls(self, mock):
        """Test that django's clean_html function is called"""
        self.mixin.sanitize_html(TEST_HTML)

        mock.called_once_with(TEST_HTML)

    def test_handle_breaks(self):
        """Test the handle_breaks function"""
        # Use the "safe" html that contains a lot of <br/> tags, spaces and
        # newlines
        result = handle_breaks(DIRTY_SAFE_HTML)

        # Test whitespace, newline and tab removal
        self.assertTrue('  ' in DIRTY_SAFE_HTML)
        self.assertFalse('  ' in result)

        self.assertTrue('\n\n' in DIRTY_SAFE_HTML)
        self.assertFalse('\n\n' in result)

        self.assertTrue('\t' in DIRTY_SAFE_HTML)
        self.assertFalse('\t' in result)

        # Test Unicode
        self.assertTrue(u'Ⴚ' in result)

        # Test newlines added after html linebreaks
        self.assertFalse('<br/>\n<br/>\n' in DIRTY_SAFE_HTML)
        self.assertTrue('<br/>\n<br/>\n' in result)

        # Test space around html break removal
        self.assertFalse('Hey<br/> Yeah' in result)
        self.assertFalse('Hey<br/>\n Yeah' in result)
        self.assertTrue('Hey<br/>\nYeah' in result)

        # Test multiple html linebreak removal
        self.assertFalse('<br/><br/><br/>' in result)
        self.assertFalse('<br/>\n<br/>\n<br/>' in result)
        self.assertTrue('Testing<br/>\n<br/>\nMultiple Lines' in result)

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_cleanse_tags(self):
        """Test that invalid html is stripped and valid html is not."""
        # pylint: disable=protected-access
        safe_html = self.mixin._cleanse_tags(TEST_HTML)

        # Test Allowed Tags
        self.assertTrue('<strong>' in safe_html)
        self.assertTrue('<em>' in safe_html)
        self.assertTrue('<a href=' in safe_html)
        self.assertTrue('br' in safe_html)
        self.assertTrue('img' in safe_html)

        # Test Allowed Attributes
        self.assertTrue('href=' in safe_html)
        self.assertTrue('src=' in safe_html, msg=safe_html)
        self.assertTrue('data-embed=' in safe_html, msg=safe_html)

        # Test allowed url schemes in links
        self.assertTrue('<a href="mailto:some@user.local">hi</a>' in safe_html)
        self.assertTrue('<a href="https://thisiscool.com">' in safe_html)

        # Test bad url schemes in links
        self.assertFalse('<a href="javascript:alert' in safe_html)
        self.assertFalse('<a href="ftp://badperson' in safe_html)

        # Test Unacceptable HTML
        self.assertFalse('iframe' in safe_html)
        self.assertFalse('<script>' in safe_html)
        self.assertFalse('h1' in safe_html)
        self.assertFalse('div' in safe_html)
        self.assertFalse('alt=' in safe_html)

        # Test Unacceptable Attributes
        self.assertFalse('display: none;' in safe_html)
        self.assertFalse('width=' in safe_html)
        self.assertFalse('height=' in safe_html)

        # Test Unicode
        self.assertTrue(u'Ⴚ'.encode("utf-8") in safe_html)

        # Test src attribute with a valid domain
        self.assertTrue('localhost' in safe_html)

        # Test src attribute with an invalid domain
        self.assertFalse('badbadsite.com' in safe_html)

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_adds_max_width(self):
        """Test that max-width is added to all image tags."""
        # pylint: disable=protected-access,invalid-name

        # Test when ADD_MAX_WIDTH is True
        self.mixin.ADD_MAX_WIDTH = True
        safe_html_with_max_width = self.mixin._cleanse_tags(TEST_HTML)
        self.assertIn(
            '<img src="http://localhost/big.jpg" style="max-width: 100%;"/>',
            safe_html_with_max_width)

        # Test when ADD_MAX_WIDTH is False
        self.mixin.ADD_MAX_WIDTH = False
        safe_html_no_max_width = self.mixin._cleanse_tags(TEST_HTML)
        self.assertNotIn('max-width', safe_html_no_max_width)

    @patch('open_connect.connect_core.utils.mixins.handle_breaks')
    @patch('open_connect.connect_core.utils.mixins.clean_html')
    @patch.object(SanitizeHTMLMixin, '_cleanse_tags')
    def test_sanitize_html(self, mock_rm_tags, mock_clean_html, mock_breaks):
        """Test that sanitize_html runs things"""
        result = self.mixin.sanitize_html(TEST_HTML)
        self.assertEqual(result, mock_breaks.return_value)

        mock_clean_html.assert_called_with(TEST_HTML)

        # Confirm that the string replacement happens
        clean_html_return = string.replace(
            mock_clean_html.return_value, '\n', '<br/>')

        mock_rm_tags.assert_called_with(clean_html_return)
        mock_breaks.assert_called_with(mock_rm_tags.return_value)

    def test_plain_text(self):
        """Test a plain text submission"""
        result = self.mixin.sanitize_html(PLAIN_TEXT_MESSAGE)

        self.assertEqual(
            result, 'Line 1<br/>\n<br/>\nLine 3<br/>\n<br/>\nLine 7')

        message = PLAIN_TEXT_MESSAGE + '<!-- vars:redactor=true -->'

        result = self.mixin.sanitize_html(message)
        self.assertEqual(
            result, 'Line 1 Line 3 Line 7')
