"""Settings related to the Connect Application"""
import environ

env = environ.Env(
    BRAND_TITLE=(str, 'Connect'),
    ORGANIZATION=(str, 'Owner'),
    HOSTNAME=(str, 'localhost:8000'),
    ORIGIN=(str, 'http://localhost:8000'),
    DEFAULT_FROM_ADDRESS=(str, 'no-reply@connect.local'),
    DEFAULT_FROM_EMAIL=(str, 'Connect <no-reply@connect.local>'),
    SYSTEM_USER_NAME=(str, 'Connect'),
    SYSTEM_USER_EMAIL=(str, 'connect@connect.local'),
    GOOGLE_ANALYTICS_PROPERTY_ID=(str, 'UA-0-0'),
    GOOGLE_ANALYTICS_DEBUG_MODE=(bool, False),
    ICON_PREFIX=(str, "glyphicon glyphicon-")
)


# The 'Brand Title' is what will appear as the "Brand Name" throughout the app.
# However, you'll need to upload your own logo and change the static config to
# actually update the logo on the top left.
BRAND_TITLE = env('BRAND_TITLE')


# The 'Organization' is the organization sponsoring Connect. This will be seen
# on outgoing emails so it's important that you correctly set it in production.
ORGANIZATION = env('ORGANIZATION')


# The 'Hostname' is the domain connect is on (no http/https)
# i.e. `connect.mydomain.com`
HOSTNAME = env('HOSTNAME')

# The 'Origin' is the hostname + protocol.
# i.e. `https://connect.mydomain.com`
ORIGIN = env('ORIGIN')


# The friendly version of the "From"
# i.e. 'Connect <no-reply@connect.mydomain.com>'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# The formal version of the "From" link
# i.e. 'no-reply@connect.mydomain.com'
DEFAULT_FROM_ADDRESS = env('DEFAULT_FROM_ADDRESS')

# The email address of the 'System User' that is the author of notifications
# from the app to end-users. This can likely be left alone, but once created
# can never be changed.
SYSTEM_USER_EMAIL = env('SYSTEM_USER_EMAIL')

# The name of the 'System User' that is the author of notifications from the
# app to end-users.
SYSTEM_USER_NAME = env('SYSTEM_USER_NAME')

# Google Analytics Property ID and Debug Mode.
# If you want to track actions within Connect in Google Analytics create a
# new property for it.
GA_PROPERTYID = env('GOOGLE_ANALYTICS_PROPERTY_ID')

# You'd want to set Google Analytics to debug mode if you're debugging GA
GA_DEBUG_MODE = env('GOOGLE_ANALYTICS_DEBUG_MODE')


# A secret key that's only used for email-related tasks
# Some parts of Connect (specifically those related to email) have to allow
# users to modify their notification settings and unsubscribe without requiring
# the user to know his or her password. We generate unique hases per-user by
# using a constant secret key. It's important to keep this secret, but using
# the same EMAIL_SECRET_KEY on your dev and staging machines might make
# developing email-related code slightly easier.
EMAIL_SECRET_KEY = env('EMAIL_SECRET_KEY')


# Prefix to be appended to all icons. This allows you to use icons other than
# glyphicons
ICON_PREFIX = env('ICON_PREFIX')
