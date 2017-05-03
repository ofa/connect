"""Settings related to authentication"""
# pylint: disable=invalid-name,line-too-long
import environ

env = environ.Env(
    LOGIN_REDIRECT_URL=(str, '/messages/'),
    POST_LOGOUT_PAGE=(str, '/'),
    ACCOUNT_EMAIL_VERIFICATION=(str, 'optional'),
    ACCOUNT_IGNORE_UNSUBSCRIBE=(bool, True)
)


####
# URLs exempt from Connects "Always Logged In" functionality
LOGIN_EXEMPT_URLS = [
    r'^login/*',
    r'^complete/*',
    r'^user/login/$',
    r'^user/logout/$',
    r'^user/signup/$',
    r'^user/password/reset/$',
    r'^user/password/reset/key/*',
    r'^user/password/reset/done/',
    r'^user/confirm-email/*',
    r'^connect/auth',
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


####
# Custom authentication model setting
AUTH_USER_MODEL = 'accounts.User'


LOGIN_URL = '/user/login/'
SIGNUP_URL = '/user/signup/'

LOGIN_REDIRECT_URL = env('LOGIN_REDIRECT_URL')
LOGOUT_REDIRECT_URL = env('POST_LOGOUT_PAGE')


AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)


####
# django-allauth options
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = env('ACCOUNT_EMAIL_VERIFICATION')
ACCOUNT_ADAPTER = 'open_connect.accounts.adapter.AccountAdapter'

ACCOUNT_IGNORE_UNSUBSCRIBE = env('ACCOUNT_IGNORE_UNSUBSCRIBE')
