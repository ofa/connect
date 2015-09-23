"""Utilities for the notification app"""
from django.db import models


def get_notification_models():
    """Utility that gets all notification models"""
    return [model for model in models.get_models()
            if getattr(model, 'create_notification', False) is True]
