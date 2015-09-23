"""Settings related to authentication"""
# pylint: disable=invalid-name

from django.utils.module_loading import import_by_path
import environ

env = environ.Env(
    DEFAULT_AUTH_BACKEND=(str, 'social.backends.ngpvan.ActionIDOpenID'),
    POST_LOGOUT_PAGE=(str, '/'),
    SOCIAL_AUTH_NEW_USER_REDIRECT_URL=(str, '/explore/'),
    LOGIN_REDIRECT_URL=(str, '/messages/'),
    LOGIN_ERROR_URL=(str, '/'),
    SOCIAL_AUTH_PROTECTED_FIELDS=(list, 'username'),
    USE_SOCIAL_AUTH_AS_ADMIN_LOGIN=(bool, True),
)


LOGIN_EXEMPT_URLS = [
    r'^login/*',
    r'^complete/*',
    r'^accounts/login/$',
    r'^accounts/logout/$',
    r'^accounts/enter-invite/$',
    r'^accounts/accept-terms/$',
    r'^static/*',
    r'^uploads/*',
    r'^explore/$',
    r'^subscriptions/unsubscribe/*',
    r'^subscriptions/bouncy/$',
    r'^mail/*',
    r'^media/image/*',
    r'^robots\.txt$',
    r'^favicon\.ico$'
]

# If using the default NGPVAN ActionID backend and no POST_LOGOUT_PAGE is set
if env('POST_LOGOUT_PAGE') == '/' and env('DEFAULT_AUTH_BACKEND') == 'social.backends.ngpvan.ActionIDOpenID':
    POST_LOGOUT_PAGE = 'https://accounts.ngpvan.com/Account/LogOut'
else:
    POST_LOGOUT_PAGE = env('POST_LOGOUT_PAGE')


DEFAULT_AUTH_BACKEND = env('DEFAULT_AUTH_BACKEND')
USE_SOCIAL_AUTH_AS_ADMIN_LOGIN = env('USE_SOCIAL_AUTH_AS_ADMIN_LOGIN')
AUTH_BACKEND = import_by_path(DEFAULT_AUTH_BACKEND)

AUTHENTICATION_BACKENDS = (
    DEFAULT_AUTH_BACKEND,
    'open_connect.connect_core.utils.auth_backends.CachedModelAuthBackend',
)

DEFAULT_AUTH_BACKEND_NAME = AUTH_BACKEND.name
LOGIN_URL = '/login/' + DEFAULT_AUTH_BACKEND_NAME +'/'
LOGIN_REDIRECT_URL = env('LOGIN_REDIRECT_URL')
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = env('SOCIAL_AUTH_NEW_USER_REDIRECT_URL')
LOGIN_ERROR_URL = env('LOGIN_ERROR_URL')

USER_FIELDS = [
    'email',
    'first_name',
    'last_name',
    'username'
]

# Fields that will never be auto-updated or modified by the python-social-auth
# user data pipeline
SOCIAL_AUTH_PROTECTED_FIELDS = env('SOCIAL_AUTH_PROTECTED_FIELDS')

# Pipeline that python-social-auth should follow
SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',

    # Uncomment to enable merging of profiles based on email. Not recommended
    # as it exposes potential security issues.
    #'social.pipeline.social_auth.associate_by_email',

    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',

    # Uncomment to have changes to the user's profile on the auth provider
    # update their details on connect
    #'social.pipeline.user.user_details'
)
