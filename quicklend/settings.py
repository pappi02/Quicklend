import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-!q5echi!=v^r3!aa21j(@oo_a=3xmdt@*a$dgh3_mq-3q_bvp&'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


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
            BASE_DIR / 'templates',  # Add this to specify where to look for templates
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


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
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
# Make sure static files are handled correctly
STATIC_URL = '/static/'

# Correct path to static files
STATICFILES_DIRS = [BASE_DIR / 'static']


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_ROOT = BASE_DIR / 'staticfiles'


# Enable the OTP static plugin
OTP_STATIC = True




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



# Redirect users to the loan list page after login
LOGIN_REDIRECT_URL = '/dashboard/'  # Redirect to loan list after login

# Optional: Customize the login redirect behavior when users are already logged in
LOGOUT_REDIRECT_URL = 'login' # Redirect to home page (login page) after logout



# Session settings for 5-minute inactivity timeout
SESSION_COOKIE_AGE = 300  # 5 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True  # Reset session expiry on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Do not expire on browser close


MEDIA_URL = '/media/'  # This is the URL prefix for media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



# Email configuration for Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'pappichulo2002@gmail.com'
EMAIL_HOST_PASSWORD = 'uglkqipgixrejusd'
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = 'pappichulo2002@gmail.com'


# settings.py
#TWILIO_ACCOUNT_SID = 'AC2e2409163c8dd0ee5b036f69e816c3a4'
#TWILIO_AUTH_TOKEN = '4a4ee1b9b075000f870273304373e287'
#TWILIO_PHONE_NUMBER = '+14242709645'
CSRF_TRUSTED_ORIGINS = [
    "https://quicklend.site",
    "https://www.quicklend.site",  # optional, if applicable
]
