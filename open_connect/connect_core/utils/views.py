"""Connect utility views.

These views are meant to be extended by other views.
"""
# pylint: disable=no-self-use,unused-argument

from collections import OrderedDict
from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.forms import BaseForm
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic.base import TemplateResponseMixin, View
import json


class CommonViewMixin(object):
    """A mixin for Class Based Views that use Connect's template"""
    def get_context_data(self, **kwargs):
        """Add into the context some useful information for base templates"""
        context = super(CommonViewMixin, self).get_context_data(**kwargs)
        if hasattr(self, 'title'):
            context['title'] = self.title

        if hasattr(self, 'nav_active_item'):
            context['nav_active_item'] = self.nav_active_item

        if hasattr(self, 'dd_active_item'):
            context['dd_active_item'] = self.dd_active_item

        if hasattr(self, 'breadcrumbs'):
            context['breadcrumbs'] = self.breadcrumbs

        if hasattr(self, 'messages'):
            for message in self.messages:
                messages.add_message(
                    self.request, message['type'], message['message'])

        return context


class JSONResponseMixin(object):
    """Mixin for django ListView to provide JSON response."""
    def render_to_response(self, context):
        """Returns a JSON response containing 'context' as payload"""
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        """Construct an `HttpResponse` object."""
        return HttpResponse(
            content, content_type='application/json', **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        """Convert the context dictionary into a JSON object"""
        return json.dumps(context, indent=4)


class MultipleFormsMixin(object):
    """
    A mixin that provides a way to show and handle multiple forms in a request.
    """

    initial = {}
    form_classes = None
    success_url = None
    ignore_validation = []

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = self.initial.copy()
        for form_class_name in self.form_classes.iterkeys():
            if form_class_name not in initial:
                initial[form_class_name] = {}
        return initial

    def get_form_classes(self):
        """
        Returns the form classes to use in this view
        """
        return self.form_classes

    def get_forms(self, form_classes):
        """
        Returns instances of the forms to be used in this view.
        """
        forms = OrderedDict()
        for form_class_name, form_class in form_classes.iteritems():
            forms[form_class_name] = form_class(
                **self.get_form_kwargs(form_class_name))
        return forms

    def get_form_kwargs(self, form_class_name):
        """
        Returns the keyword arguments for instanciating the forms.
        """
        kwargs = {'initial': self.get_initial().get(form_class_name, {})}
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
                })
        return kwargs

    def get_context_data(self, **kwargs):
        """Returns dictionary to be provided as template context."""
        return kwargs

    def get_success_url(self):
        """Returns the url to redirect to on success."""
        if self.success_url:
            url = self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def form_valid(self, forms, all_cleaned_data):
        """Process a valid form and redirect the user."""
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, forms):
        """Process an invalid form and display the form with errors."""
        return self.render_to_response(self.get_context_data(**forms))


class ProcessMultipleFormsView(View):
    """
    A mixin that processes forms on POST.
    """
    def get(self, request, *args, **kwargs):
        """Process a get request."""
        form_classes = self.get_form_classes()
        forms = self.get_forms(form_classes)
        kwargs = forms
        kwargs['forms'] = [
            form_class for form_class in forms.itervalues()
            if isinstance(form_class, BaseForm)
        ]
        return self.render_to_response(self.get_context_data(**kwargs))

    def render_invalid_response(self, forms):
        """Renders a response if forms don't validate."""
        kwargs = forms
        kwargs['forms'] = [
            form_class for form_class in forms.itervalues()
            if isinstance(form_class, BaseForm)
        ]
        kwargs['form_errors'] = True
        return self.form_invalid(kwargs)

    def post(self, request, *args, **kwargs):
        """Process a post request."""
        form_classes = self.get_form_classes()
        forms = self.get_forms(form_classes)
        all_forms_valid = True
        all_cleaned_data = {}
        invalid_forms = []
        for form_name, form in forms.iteritems():
            if not form.is_valid():
                invalid_forms.append(form_name)
                all_forms_valid = False
            else:
                if isinstance(form.cleaned_data, list):
                    # This is a formset, cleaned_data is a list of dicts
                    for instance in form.cleaned_data:
                        all_cleaned_data.update(instance)
                else:
                    all_cleaned_data.update(form.cleaned_data)
        if all_forms_valid:
            return self.form_valid(forms, all_cleaned_data)
        else:
            return self.render_invalid_response(forms)


class BaseMultipleFormsView(MultipleFormsMixin, ProcessMultipleFormsView):
    """
    A base view for displaying forms
    """


class MultipleFormsView(TemplateResponseMixin, BaseMultipleFormsView):
    """
    A view for displaying forms, and rendering a template response.
    """
