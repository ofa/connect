"""Settings related to file handling"""
# pylint: disable=invalid-name
import os

from boto.s3.connection import OrdinaryCallingFormat
import environ

from importlib import import_module


env = environ.Env(
    DEBUG=(bool, False),
    CONNECT_APP=(str, False),
    USE_S3=(bool, False),
    DEFAULT_S3_PATH=(str, 'connect/uploads'),
    STATIC_S3_PATH=(str, 'connect/static')
)


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))


# Django's "AppDirectoriesFinder" staticfiles finder goes through applications
# in the order they are listed in INSTALLED_APPS, and then prioritizes the
# FIRST static file it finds which matches a static file lookup.
# Django's ``django.template.loaders.app_directories.Loader`` template loader
# will go through all the template folders in INSTALLED_APPS and prioritize
# the FINAL template it finds which matches a lookup.
# Thus we need to hard code in the actual static files we want to override
# the open source version with.
if env('CONNECT_APP'):
    CONNECT_APP_PATH = import_module(env('CONNECT_APP')).__path__[0]
    CONNECT_STATIC_PATH = os.path.join(CONNECT_APP_PATH, 'static/connect/')
else:
    # If there is no custom Connect application, use the open source files
    # held in the 'open_connect/connect_core/static/' directory
    CONNECT_STATIC_PATH = os.path.join(
        BASE_PATH, 'open_connect/connect_core/static/connect/')


# Locations of static assets
STATICFILES_DIRS = (
    os.path.join(BASE_PATH, 'assets'),
    os.path.join(BASE_PATH, 'bower_components'),

    # The location of the compiled static files for Connect
    CONNECT_STATIC_PATH
)

# Preload metadata for S3 (used for django-s3-collectstatic)
AWS_PRELOAD_METADATA = True

# Use minification whenever DEBUG is turned off
USE_MINIFY = not env('DEBUG')

# All media/uploads should use the built-in attachment storage. Which inherits
# from the 'ATTACHMENT_STORAGE' defined in the variable. This storage will
# ensure that all uploads are unique.
DEFAULT_FILE_STORAGE = 'open_connect.connect_core.utils.storages.AttachmentStorage'

# Test of we should be using S3 for static files or fall back to filesystem
# storage
if env('USE_S3'):
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')

    # If you're using a custom domain other than `bucketname.s3.amazonaws.com`
    # assign it to `AWS_S3_CUSTOM_DOMAIN`
    # This will be used for static assets only, as our storage engine does
    # not support secure URLs not hosted on S3.
    # THIS DOMAIN MUST HAVE A VALID SSL CERTIFICATE
    AWS_S3_CUSTOM_DOMAIN = env(
        'AWS_S3_CUSTOM_DOMAIN',
        default='%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME)

    AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()

    AWS_QUERYSTRING_ACTIVE = True


    STATICFILES_STORAGE = 's3_folder_storage.s3.StaticStorage'
    ATTACHMENT_STORAGE_ENGINE = 's3_folder_storage.s3.DefaultStorage'

    # Paths on S3 for various content
    DEFAULT_S3_PATH = env('DEFAULT_S3_PATH')
    STATIC_S3_PATH = env('STATIC_S3_PATH')

    STATIC_ROOT = "/%s/" % STATIC_S3_PATH
    STATIC_URL = '//%s/%s/' % (
        AWS_S3_CUSTOM_DOMAIN, STATIC_S3_PATH)
    AWS_DEFAULT_ACL = 'public-read'

    MEDIA_ROOT = '/%s/' % DEFAULT_S3_PATH
    MEDIA_URL = '//%s/%s/' % (
        AWS_S3_CUSTOM_DOMAIN, DEFAULT_S3_PATH)

else:
    MEDIA_ROOT = os.path.join(BASE_PATH, 'uploads')
    MEDIA_URL = '/uploads/'
    STATIC_ROOT = os.path.join(BASE_PATH, 'static')
    STATIC_URL = '/static/'

    ATTACHMENT_STORAGE_ENGINE = 'django.core.files.storage.FileSystemStorage'
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
