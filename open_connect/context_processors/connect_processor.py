""" Connect Context Processor """
from django.core.urlresolvers import reverse
from django.conf import settings


def connect_processor(request):
    """Connect context processor configured to send simple information"""
    context = {'brand_title': settings.BRAND_TITLE}
    user = request.user

    context['USE_MINIFY'] = settings.USE_MINIFY
    context['icon_prefix'] = settings.ICON_PREFIX

    if user.is_authenticated():
        context['nav_items'] = [
            {'label': 'Messages',
             'link': reverse('threads'), 'class': 'threads'},
            {'label': 'Explore', 'link': reverse('explore')},
            {'label': 'Resources', 'link': reverse('resources')},

        ]

        context['nav2_items'] = [
            {'label': 'My Profile',
             'link': reverse('user_profile')},
            {'label': 'Manage My Account',
             'link': reverse('update_user')},
            {'label': 'Logout', 'link': reverse('logout')},
        ]

        admin_items = []
        # This will need to be changed to find if a user is a moderator
        # once we start allowing non-staff moderators
        if user.can_moderate:
            admin_items.append({
                'label': 'Message Moderation',
                'link': reverse('mod_admin')
            })
            admin_items.append({
                'label': 'Flag Moderation Log',
                'link': reverse('flag_log')
            })
            admin_items.append({
                'label': 'Group Moderation',
                'link': reverse('moderate_requests')
            })
        if user.has_perm('media.can_access_admin_gallery'):
            admin_items.append(
                {'label': 'Admin Gallery', 'link': reverse('admin_gallery')}
            )
        if user.has_perm('media.can_access_popular_urls'):
            admin_items.append(
                {'label': 'Popular URLs', 'link': reverse('url_popularity')}
            )
        if user.has_perm('accounts.add_invite'):
            admin_items.append(
                {'label': 'Invites', 'link': reverse('invites')}
            )
        if user.has_perm('accounts.change_user'):
            admin_items.append(
                {'label': 'User Admin',
                 'link': reverse('admin:accounts_user_changelist')}
            )
        if user.has_perm('groups.change_category') and user.is_staff:
            admin_items.append(
                {'label': 'Category Admin',
                 'link': reverse('admin:groups_category_changelist')}
            )
        if user.has_perm('accounts.can_view_user_report'):
            admin_items.append({
                'label': 'User Report', 'link': reverse('users_report')
            })
        if user.has_perm('accounts.can_view_group_report'):
            admin_items.append({
                'label': 'Group Report', 'link': reverse('groups_report')
            })
        if user.has_perm('taggit.add_tag'):
            admin_items.append(
                {'label': 'Tag Admin',
                 'link': reverse('admin:taggit_tag_changelist')}
            )

        if admin_items:
            context['nav_items'].insert(
                -1,
                {'label': 'Admin', 'link': '#', 'menu': admin_items}
            )

    else:
        login_url = settings.LOGIN_URL

        context['nav_items'] = []
        context['nav2_items'] = [{
            'label': 'Login',
            'link': login_url
        }]
        context['login_url'] = login_url

    return context
