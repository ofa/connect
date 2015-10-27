"""Settings for the Celery Task Runner"""
# pylint: disable=line-too-long,invalid-name
import os

from celery.schedules import crontab
import djcelery
import environ

env = environ.Env(
    DEBUG=(bool, False),

    # Set the celery broker to the django ORM by default
    BROKER_URL=(str, 'django://'),

    # Some Celery defaults found at https://www.cloudamqp.com/docs/celery.html
    BROKER_POOL_LIMIT=(int, 1),
    BROKER_HEARTBEAT=(int, 30),
    BROKER_CONNECTION_TIMEOUT=(int, 30),
    CELERY_EVENT_QUEUE_EXPIRES=(int, 60),
    CELERY_ALWAYS_EAGER=(bool, True),
    CELERY_TIMEZONE=(str, 'UTC'),
    CELERY_SEND_EVENTS=(bool, False),
    CELERY_RESULT_BACKEND=(str, None)
)


djcelery.setup_loader()


# If CloudAMQP is enabled, use that as the broker URL
if os.environ.get('CLOUDAMQP_URL', False):
    BROKER_URL = os.environ.get('CLOUDAMQP_URL')
else:
    BROKER_URL = env('BROKER_URL')


BROKER_POOL_LIMIT = env('BROKER_POOL_LIMIT')
BROKER_HEARTBEAT = env('BROKER_HEARTBEAT')
BROKER_CONNECTION_TIMEOUT = env('BROKER_CONNECTION_TIMEOUT')

CELERY_SEND_EVENTS = env('CELERY_SEND_EVENTS')
CELERY_EVENT_QUEUE_EXPIRES = env('CELERY_EVENT_QUEUE_EXPIRES')
CELERY_ALWAYS_EAGER = env('DEBUG')

# By default Connect does not consume results
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')

CELERYBEAT_SCHEDULE = {
    'send-daily-notifications': {
        'task': 'open_connect.notifications.tasks.send_daily_email_notifications',
        'schedule': crontab(hour=7)
    },
    'send-moderator-notifications': {
        'task': 'open_connect.notifications.tasks.send_moderation_notifications',
        # Execute the 1nd minute after each hour
        'schedule': crontab(minute=1)
    },
    'clear-email-opens': {
        'task': 'open_connect.mailer.tasks.wipe_old_email_opens',
        'schedule': crontab(hour=10, minute=20)
    },
}

CELERY_TIMEZONE = env('CELERY_TIMEZONE')
