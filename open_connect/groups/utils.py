"""Utilities for groups."""


def groups_string(groups):
    """Returns a string of group names."""
    return ', '.join([str(group) for group in groups])


def groups_tags_string(groups):
    """Returns a string of tags in groups."""
    tags = set()
    for group in groups:
        for tag in group.tags.all():
            tags.add(str(tag))
    return ', '.join(tags)


def groups_categories_string(groups):
    """Returns a string of group categories."""
    return ', '.join(
        [group.category.name for group in groups])
