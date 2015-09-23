"""Views for the mailer app"""
from django.core.urlresolvers import reverse_lazy
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.views.generic import CreateView, TemplateView, View

from open_connect.accounts.utils import generate_nologin_hash
from open_connect.accounts.models import User
from open_connect.mailer.models import Unsubscribe
from open_connect.mailer.utils import url_representation_decode, create_open

BASE64_TRANS_GIF = 'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'


class OpenView(View):
    """View for all email opens"""
    def get(self, request, *args, **kwargs):
        """Handler for all GET requests"""
        result, verification_hash = url_representation_decode(
            self.kwargs['encoded_data'])

        # Bail if our hash of the data doesn't match the hash in the name
        if verification_hash != self.kwargs['request_hash']:
            raise Http404

        # Require an email (e), unique key (k) and timestamp (t) in the url
        necessary_keys = ['e', 'k', 't']
        if not all([key in result for key in necessary_keys]):
            raise Http404

        create_open(result, request.META)

        return HttpResponse(
            BASE64_TRANS_GIF.decode('base64'), content_type='image/gif'
        )


class UnsubscribeView(CreateView):
    """View for the page users are sent to to unsubscribe from all mailings"""
    model = Unsubscribe
    template_name = "mailer/unsubscribe_form.html"
    success_url = reverse_lazy('unsubscribe_thanks')
    fields = []

    def dispatch(self, request, *args, **kwargs):
        """Dispatch method which verifies approprate GET variables exist"""
        # pylint: disable=attribute-defined-outside-init
        # Confirm that both 'email' and 'code' are in request.GET
        if not all(key in request.GET for key in ('email', 'code')):
            raise Http404

        # Validate that the email is a valid email
        self.email = request.GET['email']
        try:
            validate_email(self.email)
        except ValidationError:
            raise Http404

        # Validate that the secret code is legitimate
        if request.GET['code'] != generate_nologin_hash(self.email.lower()):
            raise Http404

        return super(UnsubscribeView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Process a valid form."""
        form.instance.address = self.email
        form.instance.source = 'user'
        return super(UnsubscribeView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        """Get context data for UnsubscribeView"""
        context = super(UnsubscribeView, self).get_context_data(**kwargs)

        # Try to grab the user's account if one exists
        try:
            context['account'] = User.objects.get(email=self.email)
        except User.DoesNotExist:
            pass

        context['email'] = self.email

        return context


class UnsubscribeThanksView(TemplateView):
    """View for the 'thank you' page for users who unsubscribe"""
    template_name = "mailer/unsubscribe_thanks.html"
