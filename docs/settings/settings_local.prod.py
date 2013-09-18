from settings import *

DEBUG = False
TEMPLATE_DEBUG = False

# The default database should point to the master.
DATABASES = {
    'default': {
        'NAME': 'zamboni',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '',
        'PORT': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {'init_command': 'SET storage_engine=InnoDB'},
    },
    'slave': {
        'NAME': 'zamboni',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '',
        'PORT': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {'init_command': 'SET storage_engine=InnoDB'},
    },
}

# Put the aliases for slave databases in this list.
SLAVE_DATABASES = ['slave']

# Use IP:PORT pairs separated by semicolons.
CACHES = {
    'default': {
        'BACKEND': 'caching.backends.memcached.CacheClass',
        'LOCATION': ['localhost:11211', 'localhost:11212'],
        'TIMEOUT': 500,
    }
}

# This is used to hash some things in Django.
SECRET_KEY = 'replace me with something long'

# Remove any apps that are only needed for development.
INSTALLED_APPS = tuple(app for app in INSTALLED_APPS if app not in DEV_APPS)

LOG_LEVEL = logging.WARNING

DEBUG_PROPAGATE_EXCEPTIONS = DEBUG


# Sample heka configuration. Uncommented, this would override what is in
# lib/settings_base.py.

# HEKA_CONF = {
#     'logger': 'zamboni',
#     'stream': {
#         'class': 'heka.streams.UdpStream',
#         'host': ['10.0.1.5', '10.0.1.10']
#         'port': 5566
#     },
#     'plugins': {
#         'raven': ('heka_raven.raven_plugin.config_plugin',
#                  {'dsn': 'udp://username:password@127.0.0.1:9000/2'}),
#     },
# }
#
# from heka.config import client_from_dict_config
# HEKA = client_from_dict_config(HEKA_CONF)


# If you want to allow self-reviews for add-ons/apps, then enable this.
# In production we do not want to allow this.
ALLOW_SELF_REVIEWS = False
