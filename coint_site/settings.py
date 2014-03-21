"""
Django settings for coint_site project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
SETTINGS_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(SETTINGS_DIR)

# check for local environment settings
if os.path.exists(os.path.join(SETTINGS_DIR, 'local_settings.py')):
    from local_settings import set_env
    set_env()

# Celery
BROKER_URL = os.getenv('RABBITMQ_BIGWIG_URL')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'zo1ynhnr_h4a!7a1%7q&ke3uttw!iscl-d#di2s4cwd(z03jq!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'coint',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'coint_site.urls'

WSGI_APPLICATION = 'coint_site.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

# Parse database configuration from environment variables

import dj_database_url
import dj_mongohq_url

DATABASES = dict()
DATABASES['default'] = dj_database_url.config()
DATABASES['mongodb'] = dj_mongohq_url.config(env='MONGOHQ_URL')

TEMPODB = dict()
TEMPODB['HOST'] = os.getenv('TEMPODB_API_HOST')
TEMPODB['PORT'] = os.getenv('TEMPODB_API_PORT')
TEMPODB['KEY'] = os.getenv('TEMPODB_API_KEY')
TEMPODB['SECRET'] = os.getenv('TEMPODB_API_SECRET')
tempodb_api_secure = os.getenv('TEMPODB_API_SECURE')
if tempodb_api_secure:
    if tempodb_api_secure == 'True':
        TEMPODB['SECURE'] = True
    elif tempodb_api_secure == 'False':
        TEMPODB['SECURE'] = False
    else:  # allow other values coming from tempodb's heroku setup
        TEMPODB['SECURE'] = tempodb_api_secure

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Eastern'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

# Static asset configuration
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_PATH, '../coint/static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)