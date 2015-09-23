"""
Folder containing all configuration files for Connect

Most django projects will have a `settings.py` file. Thanks to python's
ability to treat entire folders as if they're an individual file if the name
is correct, we can create a `settings` folder and import from smaller settings
files.

As individual Connect users may customize settings within Connect, this
file-based separation will make handling merge conflicts far easier. Plus
breaking settings out into multiple files results in much shorter files.
"""
import environ

# Load all key/values from a `.env` file into the configuration
environ.Env.read_env('.env')


# We use wildcard imports here to bring all the settings from the smaller
# settings files into this __init__ file. This is essentially concatinating
# multiple files into one large settings.py

# pylint: disable=wildcard-import
from .base_settings import *
from .application_settings import *
from .authentication_settings import *
from .celery_settings import *
from .logging import *
from .storage_settings import *
