"""Authentication backends for Connect"""
# pylint: disable=protected-access
from django.core.cache import cache
from django.contrib.auth.backends import ModelBackend


class CachedModelAuthBackend(ModelBackend):
    """An extension of `ModelBackend` that allows caching"""
    def get_all_permissions(self, user_obj, obj=None):
        """Return all permissions for a user"""
        # Anonymous users should have no permissions by default
        if user_obj.is_anonymous() or obj is not None:
            return set()

        # This should still work even if django removes `user._perm_cache` from
        # future releases of the auth `ModelBackend`
        if not hasattr(user_obj, '_perm_cache'):
            key = '{userkey}_permissions'.format(userkey=user_obj.cache_key)
            cache_result = cache.get(key)
            if cache_result is None:
                user_obj._perm_cache = super(
                    CachedModelAuthBackend, self).get_all_permissions(
                        user_obj, obj)
                # Cache permissions for 15 minutes. As adding a user to a group
                # will result in a change of the modified_at column and thus
                # the `cache_key` we don't have to hugely worry about changes
                cache.set(key, user_obj._perm_cache, 60*30)
            else:
                user_obj._perm_cache = cache_result
        return user_obj._perm_cache
