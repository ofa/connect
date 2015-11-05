"""
Django settings for whpetition project.
"""
# pylint: disable=invalid-name
import environ

root = environ.Path(__file__) - 3
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['']),
    TIME_ZONE=(str, 'US/Eastern'),
    LANGUAGE_CODE=(str, 'en-us'),
    CSRF_COOKIE_NAME=(str, 'mesages_csrftoken'),

    SESSION_COOKIE_NAME=(str, 'messages_sessionid'),
    SESSION_ENGINE=(str, 'django.contrib.sessions.backends.cached_db'),
    SESSION_SERIALIZER=(
        str, 'django.contrib.sessions.serializers.PickleSerializer'),
    SESSION_EXPIRE_AT_BROWSER_CLOSE=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    SECURE_PROXY_SSL_HEADER=(tuple, ('HTTP_X_FORWARDED_PROTO', 'https')),
    CACHE_MIDDLEWARE_ALIAS=(str, 'default'),
    CACHE_MIDDLEWARE_SECONDS=(int, 0),
    CACHE_MIDDLEWARE_KEY_PREFIX=(str, 'connect__'),
    USE_SES=(bool, False),

    EMAIL_BACKEND=(str, 'django.core.mail.backends.dummy.EmailBackend'),
    EMAIL_SUBJECT_PREFIX=(str, '[Connect] '),

    # SMTP related configuration vars
    EMAIL_HOST=(str, 'localhost'),
    EMAIL_HOST_PASSWORD=(str, ''),
    EMAIL_HOST_USER=(str, ''),
    EMAIL_PORT=(int, 25),
    EMAIL_USE_TLS=(bool, False),
    EMAIL_USE_SSL=(bool, False),
    EMAIL_SSL_CERTFILE=(str, None),
    EMAIL_SSL_KEYFILE=(str, None),
    EMAIL_TIMEOUT=(int, None),

    CUCUMBER_RATE_LIMIT=(int, 1),

    BOUNCY_AUTO_SUBSCRIBE=(bool, False),
    BOUNCY_TOPIC_ARN=(list, None),

    AWS_ACCESS_KEY_ID=(str, ''),
    AWS_SECRET_ACCESS_KEY=(str, ''),
)

####
# Secret Key Settings

SECRET_KEY = env('SECRET_KEY')


####
# Core Application Settings

DEBUG = env('DEBUG')
ROOT_URLCONF = 'connect.urls'
WSGI_APPLICATION = 'connect.wsgi.application'
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

####
# Database Settings

DATABASES = {
    'default': env.db(),
}


#####
# Cache Settings

# Attempt to get the memcache info from Heroku.
try:
    # `django-heroku-memcachify` requires memcache to work. Since we only
    # need it on heroku and don't want to require libmemcached on dev
    # machines, we'll only use it if it's installed
    from memcacheify import memcacheify
    default_cache = memcacheify()['default']

    # memcacheify will use the LocMemCache if there is no heroku cache. So if
    # we see the 'LocMemCache' we know that memcachify is not running on a
    # heroku dyno that is setup for memcached
    # pylint: disable=line-too-long
    if default_cache['BACKEND'] == 'django.core.cache.backends.locmem.LocMemCache':
        default_cache = env.cache()

except ImportError:
    # If `django-heroku-memcachify` is not installed, just use the cache
    # defined in the environment
    default_cache = env.cache()


CACHES = {
    'default': default_cache,
}

CACHE_MIDDLEWARE_ALIAS = env('CACHE_MIDDLEWARE_ALIAS')
CACHE_MIDDLEWARE_SECONDS = env('CACHE_MIDDLEWARE_SECONDS')
CACHE_MIDDLEWARE_KEY_PREFIX = env('CACHE_MIDDLEWARE_KEY_PREFIX')


####
# Installed Apps Settings

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_s3_collectstatic',

    'widget_tweaks',
    'django_nose',
    'clear_cache',

    'open_connect.connect_core',

    'open_connect.accounts',
    'open_connect.connectmessages',
    'open_connect.groups',
    'open_connect.mailer',
    'open_connect.media',
    'open_connect.moderation',
    'open_connect.notifications',
    'open_connect.reporting',
    'open_connect.resources',
    'open_connect.welcome',

    'autocomplete_light',
    'django_extensions',
    'djcelery',
    'kombu.transport.django',
    'pure_pagination',
    'seacucumber',
    'django_bouncy',

    'social.apps.django_app.default',
    'taggit',

    'debug_toolbar',

    # Add
    #'connect_extras',

    # It should be possible to comment this out and have tests pass
    # and correctly display a non-branded connect.
    'private_connect',

)


####
# Custom authentication model setting
AUTH_USER_MODEL = 'accounts.User'


####
# Middleware Settings

MIDDLEWARE_CLASSES = (
    'open_connect.middleware.handle_ip.SetCorrectIPMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'social.apps.django_app.middleware.SocialAuthExceptionMiddleware',
    'open_connect.middleware.login_required.LoginRequiredMiddleware',
    'open_connect.middleware.impersonation.ImpersonationMiddleware',
    'open_connect.middleware.timezone.TimezoneMiddleware',
    'open_connect.middleware.visit_tracking.VisitTrackingMiddleware',
    'open_connect.middleware.accept_terms.AcceptTermsAndConductMiddleware'
)


####
# Session & CSRF Settings

CSRF_COOKIE_NAME = env('CSRF_COOKIE_NAME')
SESSION_COOKIE_NAME = env('SESSION_COOKIE_NAME')
SESSION_ENGINE = env('SESSION_ENGINE')
SESSION_SERIALIZER = env('SESSION_SERIALIZER')
SESSION_EXPIRE_AT_BROWSER_CLOSE = env('SESSION_EXPIRE_AT_BROWSER_CLOSE')

# Allow secure session cookies. Enable this if you're behind HTTPS for extra
# security
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE')

# Allow users to specify a header that will signify a request as secure.
# By default we allow the 'HTTP_X_FORWARDED_PROTO' as Heroku will set this
# header when a request is SSL-enabled and strip it off if an end-user
# attempts to pass this header across.
# If it's possible for an end-user to set this header, unset this!
SECURE_PROXY_SSL_HEADER = env('SECURE_PROXY_SSL_HEADER')

####
# Email Settings

# As we do unsubscribe-prevention in a custom mailer backend, we need to have
# django default to that one
EMAIL_BACKEND = 'open_connect.mailer.backend.ConnectMailerBackend'

# We allow the setting of email backend by environment variable. Since Connect
# is a very outbound-heavy application, we default to the 'dummy' backend to
# prevent accidents.
# Some useful backends would be 'django.core.mail.backends.smtp.EmailBackend'
# for SMTP and 'seacucumber.backend.SESBackend' for Amazon's Simple Email
# Service. `seacucumber` is installed by default.
if env('EMAIL_BACKEND') == 'django.core.mail.backends.smtp.EmailBackend':
    # For SMTP we'll look for the relevant host information in the environment
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_PORT = env('EMAIL_PORT')
    EMAIL_USE_TLS = env('EMAIL_USE_TLS')
    EMAIL_USE_SSL = env('EMAIL_USE_SSL')
    EMAIL_SSL_CERTFILE = env('EMAIL_SSL_CERTFILE')
    EMAIL_SSL_KEYFILE = env('EMAIL_SSL_KEYFILE')
    EMAIL_TIMEOUT = env('EMAIL_TIMEOUT')
else:
    ORIGINAL_EMAIL_BACKEND = env('EMAIL_BACKEND')


# If you are using seacucumber you'll want to have the ability to set the rate
# limit that your SES account is capped at. We can do that with the
# `CUCUMBER_RATE_LIMIT` environment var. By default it's 1 email per second.
# You can get your rate limit by running `python manage.py ses_usage`

CUCUMBER_RATE_LIMIT = env('CUCUMBER_RATE_LIMIT')


###
# Django-bouncy settings
# We've provided the library `django_bouncy` for you to handle incoming bounces
# and complaints from Amazon Simple Email Service. You can find out more info
# about the `Django Bouncy` library at https://github.com/ofa/django-bouncy


# It's wise to specify the specific `Amazon Simple Notification Service` ARN
# for your bounce and complaint notifications
BOUNCY_TOPIC_ARN = env('BOUNCY_TOPIC_ARN')

# When you setup bouncy for the first time, you need to set your configuration
# variable `BOUNCY_AUTO_SUBSCRIBE` to `True`.
# AFTER YOU HAVE SUCCESSFULLY SUBSCRIBED YOUR SNS ENDPOINT YOU MUST EITHER
# DISABLE AUTO-SUBSCRIPTION BY REMOVING THIS CONFIGURATION VARIABLE OR AT THE
# VERY LEAST HARD-CODE YOUR SNS TOPIC ARN.
BOUNCY_AUTO_SUBSCRIBE = env('BOUNCY_AUTO_SUBSCRIBE')


####
# Amazon Web Services/Boto Settings
# AN AWS KEY IS NOT REQUIRED FOR DEVELOPMENT

# More configurations related to S3 can be found in `storage_settings.py` but
# since your code may rely on non-S3 parts of AWS it might be useful here.
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')


####
# Template Settings

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # pylint: disable=line-too-long
                'open_connect.context_processors.active_url_name.add_active_url_name',
                'open_connect.context_processors.connect_processor.connect_processor',
                'open_connect.context_processors.google_analytics.google_analytics',
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
            ],
        },
    },
]


####
# Timezone & Localization Settings
LANGUAGE_CODE = env('LANGUAGE_CODE')

TIME_ZONE = env('TIME_ZONE')
DATETIME_FORMAT = '%Y-%m-%d %H:%M'

USE_I18N = True
USE_L10N = True
USE_TZ = True


####
# Test Runner Settings

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = [
    '--with-xcoverage',
    '--with-xunit',
    # pylint: disable=line-too-long
    '--cover-package=open_connect.accounts,open_connect.context_processors,open_connect.groups,open_connect.middleware,open_connect.notifications,open_connect.connectmessages,open_connect.connect_core,open_connect.media,open_connect.moderation,open_connect.mailer,connect_extras',
    '--nologcapture'
]


####
# Pagination Settings
# Settings for the django-pagination app

PAGINATION_SETTINGS = {
    'PAGE_RANGE_DISPLAYED': 10,
    'MARGIN_PAGES_DISPLAYED': 2,
}
