"""Storage backends for Connect."""
# pylint: disable=no-init

from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import get_storage_class


# pylint: disable=invalid-name
AttachmentStorageEngine = get_storage_class(
    import_path=getattr(
        settings,
        'ATTACHMENT_STORAGE_ENGINE',
        # We have to define a fallback of the FileSystemStorage here because
        # `get_storage_class`, by default, will attempt to make our
        # `AttachmentStorage` inherit from itself.
        'django.core.files.storage.FileSystemStorage')
)


def uniqify_filename(filename):
    """Generate a unique filename that maintains the extension"""
    filelist = filename.rsplit('.', 1)
    filelist[0] = uuid4().hex
    return '.'.join(filelist)


def setting(name, default=None):
    """
    Helper function to get a Django setting by name or (optionally) return
    a default (or else ``None``).
    """
    return getattr(settings, name, default)


class HighValueStorage(AttachmentStorageEngine):
    """
    A custom storage that, when attached to boto, will use object access
    controll to make uploaded assets protected
    """

    default_acl = 'private'
    secure_urls = True

    # We have to override any `custom_domain` set in the settings file
    # because our storage engine will take that setting as a signal that all
    # files have a 'public' ACL
    custom_domain = None

    # All URLs should expire after 1 hour. This will let us cache the URL and
    # reduce CPU associated in generating signed URLs
    querystring_expire = 600
    querystring_auth = True


class AttachmentStorage(HighValueStorage):
    """AttachmentStorage is a django storage for all file attachments"""

    def get_available_name(self, name):
        """
        In order to prevent file overwriting one another this will generate
        a new filename with the format `YYMMDD.uniquehash.filename.extension`
        """
        # Set the format of our filename
        filename_format = '{path}/{date}.{filename}'

        # If the storage engine is S3, call _clean_name() to clean the name
        try:
            clean_name = self._clean_name(name)
        except AttributeError:
            clean_name = name

        # Generate the YYMMDD formatted date
        date = datetime.now().strftime('%y%m%d')

        # rsplit the filename on '/' so we have a 2 value list of
        # the path and filename
        splitname = clean_name.rsplit('/', 1)

        # Compile all the relevant strings to generate the full path/filename
        final_name = filename_format.format(
            path=splitname[0],
            date=date,
            filename=uniqify_filename(splitname[1])
        )
        return final_name
