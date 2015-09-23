"""Active URL Name Context Processor"""
from django.core.urlresolvers import resolve, Resolver404


def add_active_url_name(request):
    """Function to add active URL name to the page context"""
    try:
        resolved = resolve(request.path_info)
        return {
            'active_url_name': resolved.url_name,
            'app_name': resolved.app_name
        }
    except Resolver404:
        return {}
