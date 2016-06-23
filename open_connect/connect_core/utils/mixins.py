"""Mixin for making a multiple object generic view sortable."""
# pylint: disable=attribute-defined-outside-init
from datetime import datetime
from urllib import urlencode
from urlparse import parse_qs, urlparse
import re
import string

from bs4 import BeautifulSoup
import bleach
from django.conf import settings
from django.utils.timezone import make_aware, get_current_timezone
from django.views.generic.list import MultipleObjectMixin

from open_connect.connect_core.utils.forms import (
    DateTimeRangeForm, PaginateByForm
)


# pylint: disable=invalid-name
special_chars_regex = re.compile(r'\s+')
spaces_near_breaks_regex = re.compile(r'( *<br/> *)')
single_break = re.compile(r'(<br/>)')
three_or_more_breaks_regex = re.compile(r'(<br/>){3,}')
opening_closing_break = re.compile(r'(^(<br/>)+)|((<br/>)+$)')
# pylint: disable=line-too-long
from open_connect.connect_core.utils.third_party.django_clean_html_backport import clean_html


class DateTimeRangeListMixin(MultipleObjectMixin):
    """Mixin for filtering a list view by date & time."""
    datetime_format = '%Y-%m-%d %I:%M %p'
    date_range_field = 'created_at'
    start_date_key = 'start_datetime'
    end_date_key = 'end_datetime'
    date_range_form_class = DateTimeRangeForm
    date_range_form_context_name = 'date_range_form'

    def get_date_range_form(self):
        """Get the range selection form."""
        return self.date_range_form_class(**self.get_date_range_form_kwargs())

    def get_date_range_form_kwargs(self):
        """Get form keyword arguments."""
        return {'initial': self.get_date_range_form_initial()}

    def get_date_range_form_initial(self):
        """Get form initial data."""
        return {
            'start_datetime': self.request.GET.get(self.start_date_key, None),
            'end_datetime': self.request.GET.get(self.end_date_key, None)
        }

    def get_context_data(self, **kwargs):
        """Add form to the context."""
        if 'object_list' in kwargs:
            self.object_list = kwargs.pop('object_list')
        elif not hasattr(self, 'object_list'):
            self.object_list = None
        context = super(
            DateTimeRangeListMixin, self).get_context_data(**kwargs)
        context[self.date_range_form_context_name] = self.get_date_range_form()
        return context

    def get_queryset(self):
        """Alters queryset to limit by date range."""
        start_date = self.request.GET.get(self.start_date_key, None)
        end_date = self.request.GET.get(self.end_date_key, None)
        query_kwargs = {}
        if start_date:
            start_date = make_aware(
                datetime.strptime(start_date, self.datetime_format),
                get_current_timezone()
            )
            query_kwargs['%s__gte' % self.date_range_field] = start_date
        if end_date:
            end_date = make_aware(
                datetime.strptime(end_date, self.datetime_format),
                get_current_timezone()
            )
            query_kwargs['%s__lte' % self.date_range_field] = end_date
        return super(
            DateTimeRangeListMixin, self).get_queryset().filter(**query_kwargs)


class SortableListMixin(MultipleObjectMixin):
    """Mixin for making a multiple object generic view sortable."""
    valid_order_by = ['pk']
    default_order_by = 'pk'
    default_sort = 'asc'
    order_by_key = 'order_by'
    sort_key = 'sort'
    sort_string_format = (
        '?{order_by_key}={order_by}&{sort_key}={sort}&{querystring}')

    # pylint: disable=no-self-use
    def get_context_sort_string_name(self):
        """Set sort string key to sort_strings."""
        return 'sort_strings'

    def order_queryset(self, queryset):
        """Apply an order operation on a provided queryset"""
        order_by = self.request.GET.get(self.order_by_key)
        sort = self.request.GET.get(self.sort_key, self.default_sort)

        # Restrict options to those that are valid
        if sort not in ('asc', 'desc'):
            sort = self.default_sort

        if sort == 'asc':
            sort = ''
        else:
            sort = '-'

        if order_by not in self.valid_order_by:
            order_by = self.default_order_by

        queryset = queryset.order_by('%s%s' % (sort, order_by))
        return queryset

    def get_queryset(self):
        """Allow sorting of the queryset."""
        queryset = super(SortableListMixin, self).get_queryset()
        return self.order_queryset(queryset)

    def get_query_string(self):
        """Build the query string."""
        query_string = parse_qs(self.request.META['QUERY_STRING'])
        if self.order_by_key in query_string:
            del query_string[self.order_by_key]
        if self.sort_key in query_string:
            del query_string[self.sort_key]
        return urlencode(query_string, doseq=True)

    def get_sort_strings(self, query_string=''):
        """Build a dictionary that can be used to create sorting links."""
        existing_sort = self.request.GET.get(self.sort_key, self.default_sort)
        existing_order_by = self.request.GET.get(
            self.order_by_key, self.default_order_by)
        sort_strings = {}
        for order_by in self.valid_order_by:
            if order_by == existing_order_by:
                if existing_sort == 'asc':
                    sort = 'desc'
                else:
                    sort = 'asc'
            else:
                sort = self.default_sort
            sort_strings[order_by] = self.sort_string_format.format(
                order_by_key=self.order_by_key,
                order_by=order_by,
                sort_key=self.sort_key,
                sort=sort,
                querystring=query_string
            )
        return sort_strings

    def get_context_data(self, **kwargs):
        """Update context for the view."""
        if 'object_list' in kwargs:
            self.object_list = kwargs.pop('object_list')
        context = super(SortableListMixin, self).get_context_data(**kwargs)
        query_string = self.get_query_string()
        context['query_string'] = query_string
        context['full_query_string'] = self.request.META['QUERY_STRING']
        context[self.get_context_sort_string_name()] = self.get_sort_strings(
            query_string)
        return context


class PaginateByMixin(MultipleObjectMixin):
    """Adds ability to set paginate_by using query string."""
    paginate_key = 'per_page'
    paginate_form_class = PaginateByForm
    paginate_form_context_name = 'paginate_by_form'

    def get_paginate_form(self):
        """Get the form."""
        return self.paginate_form_class(**self.get_paginate_form_kwargs())

    def get_paginate_form_kwargs(self):
        """Get form keyword arguments."""
        return {'initial': self.get_paginate_form_initial()}

    def get_paginate_form_initial(self):
        """Get form initial data."""
        return {
            'per_page': self.request.GET.get(self.paginate_key, None),
        }

    def get_context_data(self, **kwargs):
        """Add form to the context."""
        if 'object_list' in kwargs:
            self.object_list = kwargs.pop('object_list')
        elif not hasattr(self, 'object_list'):
            self.object_list = None
        context = super(PaginateByMixin, self).get_context_data(**kwargs)
        context[self.paginate_form_context_name] = self.get_paginate_form()
        return context

    def get_paginate_by(self, queryset):
        """Get the number of items to paginate by"""
        paginate_by = self.request.GET.get(self.paginate_key, None)
        if paginate_by and paginate_by.isdigit():
            return int(paginate_by)
        return super(PaginateByMixin, self).get_paginate_by(queryset)


def handle_breaks(html):
    """Cleanup code and handle <br/> tags"""
    # Clean up the code a bit by turning newlines, tabs,
    # and multiple spaces into single spaces.
    html = special_chars_regex.sub(' ', html)

    # Remove spaces before and after HTML breaks
    html = spaces_near_breaks_regex.sub('<br/>', html)

    # Turn 3 or more <br/> tags into 2 tags
    html = three_or_more_breaks_regex.sub('<br/><br/>', html)

    # Remove the leading and trailing whitespace caused by
    # the previous regex
    html = html.strip()

    # Remove any leading and closing <br/> tags
    html = opening_closing_break.sub('', html)

    # Add a newline after every linebreak, to prevent a wall of HTML
    html = single_break.sub('<br/>\n', html)

    return html


class SanitizeHTMLMixin(object):
    """Mixin that sanitizes user-submitted HTML"""
    VALID_TAGS = ['strong', 'em', 'br', 'a', 'img']
    VALID_ATTRS = ['href', 'src', 'data-embed']
    VALID_SCHEMES = ['http', 'https', 'mailto']
    ADD_MAX_WIDTH = True

    def _cleanse_tags(self, message):
        """Using BeautifulSoup and bleach, remove or modify bad tags & attrs"""
        bleached_message = bleach.clean(
            message,
            tags=self.VALID_TAGS,
            attributes=self.VALID_ATTRS,
            protocols=self.VALID_SCHEMES,
            strip=True)

        soup = BeautifulSoup(bleached_message, "lxml")

        # Find all the tags in the HTML code
        for tag in soup.findAll():
            # We have to remove any invalid tags created by `lxml`, like <html>
            # and <body>
            if tag.name not in self.VALID_TAGS:
                tag.hidden = True

            for attr, value in dict(tag.attrs).iteritems():
                # Make sure any src attributes are on an allowed domain
                if attr == 'src':
                    parsed_src = urlparse(value)
                    valid_netlocs = settings.ALLOWED_HOSTS
                    valid_netlocs.append('')
                    if parsed_src.netloc not in valid_netlocs:
                        tag.hidden = True

            # All image tags should have a max-width style attribute to ensure
            # they always fit inside any template or email client they're
            # inserted into.
            if self.ADD_MAX_WIDTH and tag.name == 'img':
                tag.attrs['style'] = 'max-width: 100%;'

        # Grab the HTML from BeautifulSoup, return it in UTF8
        return unicode(soup).encode("utf-8", errors="ignore")

    def sanitize_html(self, message):
        """Sanitize user-submitted HTML"""
        # Use django's built-in HTML cleaner to improve HTML. This will also
        # run the HTML through django's normalize_newlines utility
        message = clean_html(message)

        # Detect if redactor is enabled
        if 'vars:redactor=true' not in message:
            # If redactor is not enabled, replace \n with <br/>
            message = string.replace(message, '\n', '<br/>')

        clean_code = self._cleanse_tags(message)

        final = handle_breaks(clean_code)

        return final
