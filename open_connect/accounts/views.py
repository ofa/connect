"""Views for the accounts app."""

from collections import OrderedDict
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.http import (
    HttpResponseRedirect,
    Http404,
    HttpResponse
)
from django.views.generic import (
    RedirectView, DetailView, ListView, FormView, UpdateView
)
from django.views.decorators.http import require_POST
from pure_pagination import PaginationMixin

from open_connect.accounts.forms import (
    UserForm,
    InviteForm,
    UserImageForm,
    BanUserForm,
    UnBanUserForm,
    BecomeUserForm,
    InviteEntryForm,
    TermsAndConductAcceptForm,
    UserPermissionForm
)
from open_connect.accounts.models import User, Invite
from open_connect.groups.models import Group
from open_connect.moderation.forms import ModNotificationUpdateForm
from open_connect.notifications.forms import get_subscription_formset
from open_connect.connect_core.utils.mixins import (
    SortableListMixin,
    PaginateByMixin
)
from open_connect.connect_core.utils.views import (
    MultipleFormsView, CommonViewMixin
)
from open_connect.connect_core.utils.third_party.cached_property import (
    cached_property
)


class UserDetailView(DetailView):
    """View for displaying a single user."""
    model = User
    context_object_name = 'account'

    @property
    def user(self):
        """Cache and return the user."""
        if not hasattr(self, '_user'):
            # pylint: disable=attribute-defined-outside-init
            self._user = self.model.objects.select_related(
                'image').get(uuid=self.kwargs['user_uuid'])
        return self._user

    def show_banned_warning(self):
        """Should the banned warning be displayed on the page."""
        if self.user.is_banned and not self.user == self.request.user:
            return True
        return False

    def get_context_data(self, **kwargs):
        """Set the active nav item to the current object."""
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['nav_active_item'] = self.object
        context['dd_active_item'] = 'Profile'
        context['show_banned_warning'] = self.show_banned_warning()
        context['subscription_formset'] = get_subscription_formset(
            user=self.request.user)
        context['groups_joined'] = Group.objects.filter(
            group__user__id=self.object.pk).select_related('image', 'group')
        context['subscribed_ids'] = self.request.user.groups_joined.values_list(
            'pk', flat=True)
        # pylint: disable=line-too-long
        context['show_message_button'] = self.request.user.can_direct_message_user(self.object)
        context['profile_is_self'] = self.request.user.pk == self.object.pk
        context['mod_update_form'] = ModNotificationUpdateForm(
            instance=self.request.user)
        return context

    def get_object(self, queryset=None):
        if not self.request.user.can_view_profile(self.user):
            raise Http404
        if self.show_banned_warning():
            messages.warning(self.request, 'This is a banned account.')
        return self.user


class UserUpdateView(MultipleFormsView):
    """View for updating a user."""
    form_classes = OrderedDict({
        'user_form': UserForm,
        'image_form': UserImageForm
    })
    form_class = UserForm
    template_name = 'accounts/user_form.html'

    def get_context_data(self, **kwargs):
        """Set the active nav item to the current object."""
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context['nav_active_item'] = self.request.user
        context['title'] = self.request.user
        context['user'] = self.request.user
        return context

    def get_form_kwargs(self, form_class_name):
        """Get kwargs for the forms."""
        kwargs = super(UserUpdateView, self).get_form_kwargs(form_class_name)
        if form_class_name == 'user_form':
            kwargs['instance'] = self.request.user
        elif form_class_name == 'image_form':
            kwargs['instance'] = self.request.user.image
        return kwargs

    def get_forms(self, form_classes):
        """Get forms."""
        forms = super(UserUpdateView, self).get_forms(form_classes)
        if not self.request.user.groups_moderating.exists():
            del forms['user_form'].fields['receive_group_join_notifications']
        return forms

    def form_valid(self, forms, all_cleaned_data):
        """Process a valid form and redirect user."""
        # Force the current user to be bound to the form for security
        forms['user_form'].instance = self.request.user
        # Save the image
        image = None
        if forms['image_form'].cleaned_data['image']:
            forms['image_form'].instance.user = self.request.user
            image = forms['image_form'].save()
            forms['user_form'].instance.image = image
        if not image and self.request.user.image:
            self.request.user.image = None

        forms['user_form'].save()

        return HttpResponseRedirect(reverse('user_profile'))


class UpdateUserPermissionView(CommonViewMixin, UpdateView):
    """View for updating a user's application permissions."""
    model = User
    form_class = UserPermissionForm
    slug_field = 'uuid'
    slug_url_kwarg = 'user_uuid'
    template_name = 'accounts/user_form_permission_change.html'
    nav_active_item = 'Admin'
    context_object_name = 'account'

    # Permissions that can be edited by this view, in the format
    # ('app_label', 'permission_codename')
    editable_permissions = (
        ('accounts', 'add_invite'),
        ('accounts', 'can_unban'),
        ('accounts', 'can_ban'),
        ('accounts', 'can_view_banned'),
        ('accounts', 'can_view_user_report'),
        ('accounts', 'can_view_group_report'),
        ('accounts', 'can_moderate_all_messages'),
        ('accounts', 'can_initiate_direct_messages'),
        ('media', 'can_promote_image'),
        ('media', 'can_access_admin_gallery'),
        ('media', 'can_access_admin_gallery'),
        ('groups', 'add_group'),
        ('groups', 'change_group'),
        ('groups', 'can_edit_any_group'),
        ('resources', 'add_resource'),
        ('resources', 'can_add_resource_anywhere')
    )

    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch the User Permission Update View

        This view cannot be used by a user actively impersonating another user.
        """
        if getattr(request.user, 'impersonating', False):
            raise PermissionDenied

        return super(UpdateUserPermissionView, self).dispatch(
            request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the queryset of possible Users for the Permission Update View

        This view cannot be used to edit the permissions of the requesting user
        nor can it be used to edit the permissions of a superuser.
        """
        return super(UpdateUserPermissionView, self).get_queryset().exclude(
            is_superuser=True).exclude(pk=self.request.user.pk)

    def get_editable_permissions(self):
        """
        Return a queryset of Permission objects that can be assigned

        The view has an attribute called `editable_permissions` but that
        attribute only lists app names and permission codenames. We need to
        turn that tuple of tuples into a queryset of permissions.
        """
        # Dynamic generation of OR queries is based on code found at
        # https://bradmontgomery.net/blog/adding-q-objects-in-django/
        permission_filter = Q()
        for permission in self.editable_permissions:
            permission_filter.add(
                Q(content_type__app_label=permission[0],
                  codename=permission[1]), Q.OR)

        return Permission.objects.filter(
            permission_filter)

    def get_permissions_queryset(self):
        """
        Get the queryset to pre-fill the optional individual permission list

        There are a significant number of possible permissions within every
        django app. Most of these permissions are not necessary for the
        operation of the app, so we never display more than the ones required.

        However, due to the way that UpdateViews and Many-to-Many forms are
        saved when a form with a many-to-many field is submitted all existing
        relationships are cleared and replaced with those submitted.

        If, by some chance, a user has an individual permission that is not
        listed above, the easiest way to handle this is to simply append the
        permission to the form in order to prevent data corruption.
        """
        editable_permissions_queryset = self.get_editable_permissions()
        existing_permissions_queryset = self.object.user_permissions.all()

        return Permission.objects.filter(
            Q(pk__in=editable_permissions_queryset.values('pk')) |
            Q(pk__in=existing_permissions_queryset.values('pk'))
            ).order_by('content_type__app_label').select_related('content_type')

    def get_form(self, form_class):
        """Return the form using the correct Permission queryset"""
        form = super(UpdateUserPermissionView, self).get_form(form_class)
        form.fields[
            'user_permissions'].queryset = self.get_permissions_queryset()

        return form


class UserProfileRedirectView(RedirectView):
    """View for redirecting a user to their profile."""
    permanent = False

    def get_redirect_url(self, **kwargs):
        """Return the user detail url."""
        return reverse(
            'user_details', kwargs={'user_uuid': self.request.user.uuid})


class InviteCreateView(CommonViewMixin, FormView):
    """View for inviting a user."""
    form_class = InviteForm
    nav_active_item = 'Admin'
    template_name = 'accounts/invite_form.html'

    def get_form(self, form_class):
        form = super(InviteCreateView, self).get_form(form_class)
        if not self.request.user.is_superuser:
            del form.fields['is_superuser']
            form.fields['groups'].queryset = self.request.user.groups_joined
        if not self.request.user.is_staff:
            del form.fields['is_staff']
        return form

    def get_success_url(self):
        """Return the URL a user should be directed to."""
        return reverse('invites')

    def form_valid(self, form):
        """Process a valid form."""
        form.created_by = self.request.user
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class InviteListView(PaginationMixin, PaginateByMixin, SortableListMixin,
                     CommonViewMixin, ListView):
    """View for listing invites."""
    model = Invite
    nav_active_item = 'Admin'
    dd_active_item = 'Invites'
    valid_order_by = [
        'email', 'code', 'is_staff', 'is_superuser', 'created_at', 'created_by',
        'notified', 'consumed_at'
    ]
    default_order_by = 'created_at'
    paginate_by = 20
    context_object_name = 'invites'

    def get_queryset(self):
        """Get the queryset."""
        queryset = super(InviteListView, self).get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(email__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        """Get context data."""
        context = super(InviteListView, self).get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class InviteEntryView(CommonViewMixin, FormView):
    """View for users to enter their invite code."""
    form_class = InviteEntryForm
    template_name = 'invite_entry_form.html'

    def get_success_url(self):
        """Return the user to where they came from."""
        return self.request.GET.get('next', '/')

    def form_valid(self, form):
        """Save the form."""
        form.user_id = self.request.user.pk
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class TermsAndConductAcceptView(FormView):
    """View for accepting ToS and UCoC."""
    form_class = TermsAndConductAcceptForm
    template_name = 'terms_and_conduct_form.html'

    def get_initial(self):
        """Pre-fills form since fields are hidden.

        Originally there were checkboxes that had to be checked, but that
        requirement was removed. Since the form was aleady there and we could
        potentially go back at some point, the fields are now hidden and
        always selected.
        """
        initial = super(TermsAndConductAcceptView, self).get_initial()
        initial['next'] = self.request.GET.get('next', '/')
        initial['accept_tos'] = True
        initial['accept_ucoc'] = True
        return initial

    def form_valid(self, form):
        """Save the form."""
        form.save(user_id=self.request.user.pk)
        return HttpResponseRedirect(form.cleaned_data['next'])


class BanUnBanViewBase(FormView):
    """Base class for ban and unban views"""
    @property
    def user(self):
        """Cache and return the user."""
        if not hasattr(self, '_user'):
            # pylint: disable=attribute-defined-outside-init
            self._user = User.objects.get(uuid=self.kwargs['user_uuid'])
        return self._user

    def get_initial(self):
        """Get initial values for form."""
        initial = super(BanUnBanViewBase, self).get_initial()
        initial['user'] = self.user
        return initial

    def get_context_data(self, **kwargs):
        """Update the view context."""
        context = super(BanUnBanViewBase, self).get_context_data(**kwargs)
        context['account'] = self.user
        return context

    def get_success_url(self):
        """Get the url to return the user to on success."""
        return reverse('user_details', kwargs={'user_uuid': self.user.uuid})


class BanUserView(BanUnBanViewBase):
    """View for banning a user."""
    form_class = BanUserForm
    template_name = 'accounts/ban_form.html'

    def form_valid(self, form):
        """Process the valid form."""
        form.save()
        user = form.cleaned_data['user']
        if form.cleaned_data['confirm']:
            messages.success(self.request, '%s has been banned' % user)
        else:
            messages.info(self.request, '%s has not been banned.' % user)
        return HttpResponseRedirect(self.get_success_url())


class UnBanUserView(BanUnBanViewBase):
    """View for unbanning a user."""
    form_class = UnBanUserForm
    template_name = 'accounts/unban_form.html'

    def form_valid(self, form):
        """Process the valid form."""
        form.save()
        user = form.cleaned_data['user']
        if form.cleaned_data['confirm']:
            messages.success(self.request, '%s is no longer banned.' % user)
        else:
            messages.info(self.request, '%s is still banned.' % user)
        return HttpResponseRedirect(self.get_success_url())


class BecomeUserView(FormView):
    """View for becoming another user."""
    form_class = BecomeUserForm
    template_name = 'accounts/become_user_form.html'

    def get_success_url(self):
        """Returns the url to redirect to on success."""
        next_page = self.request.GET.get('next', reverse('threads'))
        return next_page

    @cached_property()
    def user_to_become(self):
        """Return the user to become"""
        return User.objects.get(uuid=self.kwargs['user_uuid'])

    def form_valid(self, form):
        """Handles a valid form response."""
        if self.request.user.can_impersonate():
            session = self.request.session
            session['impersonate_id'] = form.cleaned_data['user_to_become'].pk
            session.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        """Sets the form's initial values."""
        initial = super(BecomeUserView, self).get_initial()
        initial['user_to_become'] = self.user_to_become
        return initial

    def get_context_data(self, **kwargs):
        """Add the user_user_to_become to the context."""
        context = super(BecomeUserView, self).get_context_data(**kwargs)
        context['user_to_become'] = self.user_to_become
        return context


def unbecome_user(request):
    """Revert back to viewing site as the logged in user."""
    session = request.session
    if 'impersonate_id' in session:
        del session['impersonate_id']
        session.save()
    return HttpResponseRedirect(request.GET.get('next', reverse('threads')))


@require_POST
def user_tutorial_view(request):
    """View for updating whether or not ."""
    request.user.has_viewed_tutorial = not request.user.has_viewed_tutorial
    request.user.save()

    return HttpResponse(
        json.dumps({
            'success': True
        }),
        content_type='application/json'
    )
