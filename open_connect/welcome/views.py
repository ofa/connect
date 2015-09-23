"""Views for when a user first visits."""

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from open_connect.connect_core.utils.views import CommonViewMixin


class WelcomeView(CommonViewMixin, TemplateView):
    """WelcomeView redirects users to the appropriate page based."""
    template_name = 'welcome.html'
    title = "Welcome"

    def get(self, request, *args, **kwargs):
        """Process get request."""
        if request.user.is_authenticated():
            if request.user.groups.all().exists():
                return HttpResponseRedirect(reverse('threads'))
            else:
                return HttpResponseRedirect(reverse('groups'))
        return super(WelcomeView, self).get(request, *args, **kwargs)
