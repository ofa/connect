"""Groups application."""
# pylint: disable=invalid-name
import django.dispatch


# Define custom signals for members being added and removed
group_member_added = django.dispatch.Signal(providing_args=["group", "user"])
group_member_removed = django.dispatch.Signal(providing_args=["group", "user"])
