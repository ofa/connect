"""Connect utility forms."""
# pylint: disable=no-init
from django import forms


class DateTimeRangeForm(forms.Form):
    """Form for date/time pickers."""
    start_datetime = forms.DateTimeField(required=False)
    end_datetime = forms.DateTimeField(required=False)


class PaginateByForm(forms.Form):
    """Form for selecting how many items to show per page."""
    CHOICES = (
        ('25', '25'),
        ('50', '50'),
        ('100', '100'),
        ('200', '200')
    )
    per_page = forms.IntegerField(
        required=False, widget=forms.Select(choices=CHOICES))
