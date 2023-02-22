#
# Copyright 2019 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""
Django settings for rbac project.

Generated by 'django-admin startproject' using Django 2.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import os

import datetime
import sys
import logging
import pytz

from boto3 import client as boto_client
from corsheaders.defaults import default_headers
from dateutil.parser import parse as parse_dt
from app_common_python import LoadedConfig, KafkaTopics

from . import ECSCustom

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases


from . import database

from .env import ENVIRONMENT

# Sentry monitoring configuration
# Note: Sentry is disabled unless it is explicitly turned on by setting DSN

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration(), RedisIntegration()])
    print("Sentry SDK initialization was successful!")
else:
    print("SENTRY_DSN was not set, skipping Sentry initialization.")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GIT_COMMIT = ENVIRONMENT.get_value("GIT_COMMIT", default="local-dev")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# The SECRET_KEY is provided via an environment variable in OpenShift
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    # safe value used for development when DJANGO_SECRET_KEY might not be set
    "asvuhxowz)zjbo4%7pc$ek1nbfh_-#%$bq_x8tkh=#e24825=5",
)

# SECURITY WARNING: don't run with debug turned on in production!
# Default value: False
DEBUG = False if os.getenv("DJANGO_DEBUG", "False") == "False" else True  # pylint: disable=R1719

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    # django
    # 'django.contrib.admin',
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_prometheus",
    "django_extensions",
    # local apps
    "api",
    "management",
]

SHARED_APPS = (
    "management",
    "api",
    "django.contrib.contenttypes",
    # 'django.contrib.admin',
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "django_extensions",
)

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "rbac.middleware.DisableCSRF",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "rbac.middleware.IdentityHeaderMiddleware",
    "internal.middleware.InternalIdentityHeaderMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

DEVELOPMENT = ENVIRONMENT.bool("DEVELOPMENT", default=False)
if DEVELOPMENT:
    MIDDLEWARE.insert(5, "rbac.dev_middleware.DevelopmentIdentityHeaderMiddleware")
# Don't try to go verify Principals against the BOP user service
BYPASS_BOP_VERIFICATION = ENVIRONMENT.bool("BYPASS_BOP_VERIFICATION", default=False)

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.AllowAllUsersModelBackend"]


ROOT_URLCONF = "rbac.urls"

WSGI_APPLICATION = "rbac.wsgi.application"

DATABASES = {"default": database.config()}

PROMETHEUS_EXPORT_MIGRATIONS = False

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/


API_PATH_PREFIX = os.getenv("API_PATH_PREFIX", "/")
STATIC_API_PATH_PREFIX = API_PATH_PREFIX
if STATIC_API_PATH_PREFIX != "" and (not STATIC_API_PATH_PREFIX.endswith("/")):
    STATIC_API_PATH_PREFIX = STATIC_API_PATH_PREFIX + "/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "{}/static/".format(API_PATH_PREFIX.rstrip("/"))

STATICFILES_DIRS = [os.path.join(BASE_DIR, "..", "docs/source/specs")]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

INTERNAL_IPS = ["127.0.0.1"]

DEFAULT_PAGINATION_CLASS = "api.common.pagination.StandardResultsSetPagination"
DEFAULT_EXCEPTION_HANDLER = "api.common.exception_handler.custom_exception_handler"

# django rest_framework settings
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"],
    "DEFAULT_PAGINATION_CLASS": DEFAULT_PAGINATION_CLASS,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": DEFAULT_EXCEPTION_HANDLER,
    "ORDERING_PARAM": "order_by",
}

# CW settings
if ENVIRONMENT.bool("CLOWDER_ENABLED", default=False):
    if ENVIRONMENT.bool("CW_NULL_WORKAROUND", default=True):
        CW_AWS_ACCESS_KEY_ID = None
        CW_AWS_SECRET_ACCESS_KEY = None
        CW_AWS_REGION = None
        CW_LOG_GROUP = None
    else:
        CW_AWS_ACCESS_KEY_ID = LoadedConfig.logging.cloudwatch.accessKeyId
        CW_AWS_SECRET_ACCESS_KEY = LoadedConfig.logging.cloudwatch.secretAccessKey
        CW_AWS_REGION = LoadedConfig.logging.cloudwatch.region
        CW_LOG_GROUP = LoadedConfig.logging.cloudwatch.logGroup
else:
    CW_AWS_ACCESS_KEY_ID = ENVIRONMENT.get_value("CW_AWS_ACCESS_KEY_ID", default=None)
    CW_AWS_SECRET_ACCESS_KEY = ENVIRONMENT.get_value("CW_AWS_SECRET_ACCESS_KEY", default=None)
    CW_AWS_REGION = ENVIRONMENT.get_value("CW_AWS_REGION", default="us-east-1")
    CW_LOG_GROUP = ENVIRONMENT.get_value("CW_LOG_GROUP", default="platform-dev")

CW_CREATE_LOG_GROUP = ENVIRONMENT.bool("CW_CREATE_LOG_GROUP", default=False)

LOGGING_FORMATTER = os.getenv("DJANGO_LOG_FORMATTER", "simple")
DJANGO_LOGGING_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
RBAC_LOGGING_LEVEL = os.getenv("RBAC_LOG_LEVEL", "INFO")
LOGGING_HANDLERS = os.getenv("DJANGO_LOG_HANDLERS", "console").split(",")
VERBOSE_FORMATTING = "%(levelname)s %(asctime)s %(module)s " "%(process)d %(thread)d %(message)s"

if DEBUG and "ecs" in LOGGING_HANDLERS:
    DEBUG_LOG_HANDLERS = [v for v in LOGGING_HANDLERS if v != "ecs"]
    if DEBUG_LOG_HANDLERS == []:
        DEBUG_LOG_HANDLERS = ["console"]
else:
    DEBUG_LOG_HANDLERS = LOGGING_HANDLERS

LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", BASE_DIR)
DEFAULT_LOG_FILE = os.path.join(LOG_DIRECTORY, "app.log")
LOGGING_FILE = os.getenv("DJANGO_LOG_FILE", DEFAULT_LOG_FILE)

if CW_AWS_ACCESS_KEY_ID:
    LOGGING_HANDLERS += ["watchtower"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": VERBOSE_FORMATTING},
        "simple": {"format": "[%(asctime)s] %(levelname)s: %(message)s"},
        "ecs_formatter": {"()": "rbac.ECSCustom.ECSCustomFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": LOGGING_FORMATTER},
        "file": {
            "level": RBAC_LOGGING_LEVEL,
            "class": "logging.FileHandler",
            "filename": LOGGING_FILE,
            "formatter": LOGGING_FORMATTER,
        },
        "ecs": {"class": "logging.StreamHandler", "formatter": "ecs_formatter"},
    },
    "loggers": {
        "django": {"handlers": LOGGING_HANDLERS, "level": DJANGO_LOGGING_LEVEL},
        "django.server": {"handlers": DEBUG_LOG_HANDLERS, "level": DJANGO_LOGGING_LEVEL, "propagate": False},
        "django.request": {"handlers": DEBUG_LOG_HANDLERS, "level": DJANGO_LOGGING_LEVEL, "propagate": False},
        "api": {"handlers": LOGGING_HANDLERS, "level": RBAC_LOGGING_LEVEL},
        "rbac": {"handlers": LOGGING_HANDLERS, "level": RBAC_LOGGING_LEVEL},
        "management": {"handlers": LOGGING_HANDLERS, "level": RBAC_LOGGING_LEVEL},
    },
}

if CW_AWS_ACCESS_KEY_ID:
    NAMESPACE = ENVIRONMENT.get_value("APP_NAMESPACE", default="unknown")

    boto3_logs_client = boto_client(
        "logs",
        region_name=CW_AWS_REGION,
        aws_access_key_id=CW_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CW_AWS_SECRET_ACCESS_KEY,
    )

    WATCHTOWER_HANDLER = {
        "level": RBAC_LOGGING_LEVEL,
        "class": "watchtower.CloudWatchLogHandler",
        "boto3_client": boto3_logs_client,
        "log_group_name": CW_LOG_GROUP,
        "stream_name": NAMESPACE,
        "formatter": LOGGING_FORMATTER,
        "use_queues": True,
        "create_log_group": CW_CREATE_LOG_GROUP,
    }
    LOGGING["handlers"]["watchtower"] = WATCHTOWER_HANDLER

# Cors Setup
# See https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = default_headers + ("x-rh-identity", "HTTP_X_RH_IDENTITY")

APPEND_SLASH = False

# Celery settings
if ENVIRONMENT.bool("CLOWDER_ENABLED", default=False):
    REDIS_HOST = LoadedConfig.inMemoryDb.hostname
    REDIS_PORT = LoadedConfig.inMemoryDb.port
else:
    REDIS_HOST = ENVIRONMENT.get_value("REDIS_HOST", default="localhost")
    REDIS_PORT = ENVIRONMENT.get_value("REDIS_PORT", default="6379")

DEFAULT_REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

CELERY_BROKER_URL = ENVIRONMENT.get_value("CELERY_BROKER_URL", default=DEFAULT_REDIS_URL)

ACCESS_CACHE_DB = 1
ACCESS_CACHE_LIFETIME = 10 * 60
ACCESS_CACHE_ENABLED = ENVIRONMENT.bool("ACCESS_CACHE_ENABLED", default=True)
ACCESS_CACHE_CONNECT_SIGNALS = ENVIRONMENT.bool("ACCESS_CACHE_CONNECT_SIGNALS", default=True)

REDIS_MAX_CONNECTIONS = ENVIRONMENT.get_value("REDIS_MAX_CONNECTIONS", default=10)
REDIS_SOCKET_CONNECT_TIMEOUT = ENVIRONMENT.get_value("REDIS_SOCKET_CONNECT_TIMEOUT", default=0.1)
REDIS_SOCKET_TIMEOUT = ENVIRONMENT.get_value("REDIS_SOCKET_TIMEOUT", default=0.1)
REDIS_CACHE_CONNECTION_PARAMS = dict(
    max_connections=REDIS_MAX_CONNECTIONS,
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=ACCESS_CACHE_DB,
    socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=REDIS_SOCKET_TIMEOUT,
)

ROLE_CREATE_ALLOW_LIST = ENVIRONMENT.get_value("ROLE_CREATE_ALLOW_LIST", default="").split(",")

# Migration Setup
TENANT_PARALLEL_MIGRATION_MAX_PROCESSES = ENVIRONMENT.int("TENANT_PARALLEL_MIGRATION_MAX_PROCESSES", default=2)
TENANT_PARALLEL_MIGRATION_CHUNKS = ENVIRONMENT.int("TENANT_PARALLEL_MIGRATION_CHUNKS", default=2)

# Seeding Setup
PERMISSION_SEEDING_ENABLED = ENVIRONMENT.bool("PERMISSION_SEEDING_ENABLED", default=True)
ROLE_SEEDING_ENABLED = ENVIRONMENT.bool("ROLE_SEEDING_ENABLED", default=True)
GROUP_SEEDING_ENABLED = ENVIRONMENT.bool("GROUP_SEEDING_ENABLED", default=True)
MAX_SEED_THREADS = ENVIRONMENT.int("MAX_SEED_THREADS", default=None)

# disable log messages less than CRITICAL when running unit tests.
if len(sys.argv) > 1 and sys.argv[1] == "test":
    logging.disable(logging.CRITICAL)

# Optionally log all DB queries
if ENVIRONMENT.bool("LOG_DATABASE_QUERIES", default=False):
    LOGGING["loggers"]["django.db.backends"] = {"handlers": ["console"], "level": "DEBUG", "propagate": False}

# Internal API Configuration
INTERNAL_API_PATH_PREFIXES = ["/_private/"]

try:
    INTERNAL_DESTRUCTIVE_API_OK_UNTIL = parse_dt(os.environ.get("RBAC_DESTRUCTIVE_ENABLED_UNTIL", "not-a-real-time"))
    if INTERNAL_DESTRUCTIVE_API_OK_UNTIL.tzinfo is None:
        INTERNAL_DESTRUCTIVE_API_OK_UNTIL = INTERNAL_DESTRUCTIVE_API_OK_UNTIL.replace(tzinfo=pytz.UTC)
except ValueError as e:
    INTERNAL_DESTRUCTIVE_API_OK_UNTIL = datetime.datetime(1970, 1, 1, tzinfo=pytz.UTC)


AUTHENTICATE_WITH_ORG_ID = ENVIRONMENT.bool("AUTHENTICATE_WITH_ORG_ID", default=False)

KAFKA_ENABLED = ENVIRONMENT.get_value("KAFKA_ENABLED", default=False)
MOCK_KAFKA = ENVIRONMENT.get_value("MOCK_KAFKA", default=False)

NOTIFICATIONS_ENABLED = ENVIRONMENT.get_value("NOTIFICATIONS_ENABLED", default=False)
NOTIFICATIONS_RH_ENABLED = ENVIRONMENT.get_value("NOTIFICATIONS_RH_ENABLED", default=False)
NOTIFICATIONS_TOPIC = ENVIRONMENT.get_value("NOTIFICATIONS_TOPIC", default=None)

EXTERNAL_SYNC_TOPIC = ENVIRONMENT.get_value("EXTERNAL_SYNC_TOPIC", default=None)

# if we don't enable KAFKA we can't use the notifications
if not KAFKA_ENABLED:
    NOTIFICATIONS_ENABLED = False
    NOTIFICATIONS_RH_ENABLED = False
    NOTIFICATIONS_TOPIC = None

# Kafka settings
if KAFKA_ENABLED:
    KAFKA_AUTH = False
    if ENVIRONMENT.bool("CLOWDER_ENABLED", default=False):
        kafka_broker = LoadedConfig.kafka.brokers[0]
        KAFKA_HOST = kafka_broker.hostname
        KAFKA_PORT = kafka_broker.port
        try:
            if kafka_broker.authtype.value == "sasl":
                KAFKA_AUTH = {
                    "bootstrap_servers": f"{KAFKA_HOST}:{KAFKA_PORT}",
                    "sasl_plain_username": kafka_broker.sasl.username,
                    "sasl_plain_password": kafka_broker.sasl.password,
                    "sasl_mechanism": kafka_broker.sasl.saslMechanism.upper(),
                    "security_protocol": kafka_broker.sasl.securityProtocol.upper(),
                }
        except AttributeError:
            KAFKA_AUTH = False
    else:
        KAFKA_HOST = "localhost"
        KAFKA_PORT = "9092"
    KAFKA_SERVER = f"{KAFKA_HOST}:{KAFKA_PORT}"

    clowder_notifications_topic = KafkaTopics.get(NOTIFICATIONS_TOPIC)
    if clowder_notifications_topic:
        NOTIFICATIONS_TOPIC = clowder_notifications_topic.name

    clowder_sync_topic = KafkaTopics.get(EXTERNAL_SYNC_TOPIC)
    if clowder_sync_topic:
        EXTERNAL_SYNC_TOPIC = clowder_sync_topic.name
