import os
from pathlib import Path
import environ
#import pymysql

# Install pymysql as MySQLdb
#pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

# Read the .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'loans',  # Your app where static files are located
    'two_factor',
    'django_otp',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'quicklend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Path for custom templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'quicklend.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Other configurations (SECRET_KEY, DEBUG, ALLOWED_HOSTS, etc.)
SECRET_KEY = env('SECRET_KEY')  # SECRET_KEY from .env
DEBUG = env('DJANGO_DEBUG')  # DEBUG from .env
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'quicklend.website', 'www.quicklend.website'])

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# OTP static plugin
OTP_STATIC = True

# Authentication settings
LOGIN_REDIRECT_URL = '/dashboard/'  # Redirect after login
LOGOUT_REDIRECT_URL = 'login'       # Redirect after logout

# Session settings: expire sessions when the browser closes.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email configuration - use environment variables
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')  # Email user from .env
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')  # Email password from .env
# DEFAULT_FROM_EMAIL = f'Your Company Name <{EMAIL_HOST_USER}>'

# Optional: Uncomment and configure the following if you use Twilio.
# TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
# TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')

# Optional Production Settings:
# If you are serving your site over HTTPS, consider enabling these:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# You may also add additional logging or error reporting settings.


