"""Views for Connect resources."""
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.views.generic import RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView

from open_connect.groups.models import Group
from open_connect.resources.forms import ResourceForm
from open_connect.resources.models import (
    Resource, FILE_TYPE_TO_MIME, FILE_TYPES
)
from open_connect.connect_core.utils.views import JSONResponseMixin


class ResourceFormMixin(object):
    """Mixin for updating the ResourceForm for create/update views."""
    def get_form(self, form_class=None):
        """Limit groups choices based on permission level."""
        form = super(ResourceFormMixin, self).get_form(form_class)
        user = self.request.user
        if user.has_perm('resources.can_add_resource_anywhere'):
            return form
        elif user.has_perm('resources.add_resource'):
            form.fields['groups'].queryset = Group.objects.filter(owners=user)
            return form
        else:
            return None


class ResourceCreateView(ResourceFormMixin, CreateView):
    """View for creating a new Resource."""
    model = Resource
    form_class = ResourceForm
    success_url = reverse_lazy('resources')

    def dispatch(self, *args, **kwargs):
        """Limit view to users with access to create a Resource."""
        if not self.request.user.has_perm('resources.add_resource'):
            return HttpResponseForbidden()
        return super(
            ResourceCreateView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        """Handle a valid form."""
        form.instance.created_by = self.request.user
        form.instance.content_type = self.request.FILES.items(
            )[0][1].content_type
        return super(ResourceCreateView, self).form_valid(form)


class ResourceUpdateView(ResourceFormMixin, UpdateView):
    """View for updating an existing Resource."""
    model = Resource
    form_class = ResourceForm
    success_url = reverse_lazy('resources')
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def dispatch(self, *args, **kwargs):
        """Limit view to users with access to update this Resource."""
        result = super(ResourceUpdateView, self).dispatch(*args, **kwargs)
        if not self.object.user_can_edit(user_id=self.request.user.pk):
            return HttpResponseForbidden()
        return result

    def form_valid(self, form):
        """Handle a valid form."""
        if self.request.FILES:
            form.instance.content_type = self.request.FILES.items(
                )[0][1].content_type

        return super(ResourceUpdateView, self).form_valid(form)


class ResourceListView(ListView):
    """View for listing Resources."""
    model = Resource
    context_object_name = 'resources'

    def get_queryset(self):
        """Limit resources to ones posted to groups a user is a member of."""
        queryset = super(ResourceListView, self).get_queryset()
        query = self.request.GET.get('query', None)
        group_id = self.request.GET.get('group_id', None)
        file_type = self.request.GET.get('file_type', None)
        queryset = queryset.filter(groups__in=self.request.user.groups_joined)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(tags__slug__icontains=query)
            ).distinct()
        if group_id:
            queryset = queryset.filter(groups__pk=group_id)
        if file_type:
            queryset = queryset.filter(
                content_type__in=FILE_TYPE_TO_MIME[file_type])
        queryset = queryset.select_related('created_by')
        return queryset

    def get_context_data(self, **kwargs):
        """Update view context"""
        context = super(ResourceListView, self).get_context_data(**kwargs)
        context['file_types'] = FILE_TYPES
        context['query'] = self.request.GET.get('query', '')
        group_id = self.request.GET.get('group_id', '')
        context['group_id'] = group_id
        if group_id:
            user_group = self.request.user.groups_joined.get(pk=group_id)
            context['group'] = user_group
        return context


class ResourceDownloadView(RedirectView):
    """Direct a user to a Resource."""
    permanent = False
    resource = None

    def get(self, request, *args, **kwargs):
        """Method to handle GET Http Requests to ResourceDownloadView"""
        self.resource = Resource.objects.get(slug=self.kwargs['slug'])
        if not self.resource.user_can_download(self.request.user.pk):
            return HttpResponseForbidden()
        return super(ResourceDownloadView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        """Returns the url of a Resource."""
        return self.resource.attachment.url


class ResourceDeleteView(JSONResponseMixin, DeleteView):
    """Delete a resource."""
    model = Resource
    success_url = reverse_lazy('resources')
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def dispatch(self, *args, **kwargs):
        """Method to dispatch all HTTP requests to ResourceDeleteView"""
        result = super(ResourceDeleteView, self).dispatch(*args, **kwargs)
        if not self.object.user_can_delete(user_id=self.request.user.pk):
            return HttpResponseForbidden()
        return result

    def delete(self, request, *args, **kwargs):
        """Renders JSON response instead of redirecting after deletion."""
        super(ResourceDeleteView, self).delete(request, *args, **kwargs)
        return self.render_to_response(
            {'success': True, 'message': 'The resource has been deleted.'})
