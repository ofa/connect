"""Analytics context processor"""
from django.conf import settings


def google_analytics(request):
    """Google Analytics"""
    google_analytics_settings = {
        'id': settings.GA_PROPERTYID,
        'debug': settings.GA_DEBUG_MODE
    }

    return {'ga': google_analytics_settings}
