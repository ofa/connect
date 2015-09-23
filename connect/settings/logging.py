"""Settings for logging within Connect"""
# pylint: disable=line-too-long,invalid-name
import environ

env = environ.Env(
    LOG_LEVEL=(str, 'WARNING')
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': env('LOG_LEVEL'),
            'propagate': True,
        },
        'messages.models': {
            'handlers': ['debug'],
            'level': env('LOG_LEVEL'),
            'propagate': True
        },
        'groups.views': {
            'handlers': ['debug'],
            'level': env('LOG_LEVEL'),
            'propagate': True
        },
        'accounts.models': {
            'handlers': ['debug'],
            'level': env('LOG_LEVEL'),
            'propagate': True
        },
        'celery': {
            'handlers': ['console'],
            'level': env('LOG_LEVEL'),
        },
        'groups.tasks': {
            'handlers': ['debug'],
            'level': env('LOG_LEVEL'),
            'propagate': True
        },
        'connectmessages.models': {
            'handlers': ['debug'],
            'level': env('LOG_LEVEL'),
            'propagate': True
        }
    }
}
