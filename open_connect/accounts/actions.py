"""Actions that can be performed in admin"""
from django.template.response import TemplateResponse

from open_connect.accounts.forms import AssignToPermGroupForm


def assign_to_perm_group(modeladmin, request, queryset):
    """Assign a user to a permission group"""
    form = AssignToPermGroupForm(
        initial={'users': [user.pk for user in queryset]})
    if 'permission_group' in request.POST:
        form = AssignToPermGroupForm(request.POST)
        if form.is_valid():
            form.save()
            return

    context = {
        'title': 'Assign To Permission Group',
        'form': form,
        'queryset': queryset
    }
    return TemplateResponse(
        request,
        'accounts/admin/actions/assign_account_to_perm_group.html',
        context
    )
