import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
ENABLE_ASYNC = os.environ.get("ENABLE_ASYNC", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

import sys

_db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
if _db_url:
    _db_url = _db_url.strip().strip("'\"")


def _postgres_config_from_url(db_url: str) -> dict:
    import urllib.parse as urlparse

    parsed = urlparse.urlparse(db_url)
    if not parsed.scheme or not parsed.hostname:
        raise ImproperlyConfigured(
            "DATABASE_URL is malformed. Use a full URL like "
            "'postgresql://user:password@host:port/database'."
        )
    if not parsed.username:
        raise ImproperlyConfigured(
            "DATABASE_URL is missing username. For Supabase pooler use "
            "'postgres.<project-ref>' as username."
        )
    if parsed.password is None:
        raise ImproperlyConfigured(
            "DATABASE_URL is missing password. Ensure special characters are URL-encoded."
        )

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/") or "postgres",
        "USER": parsed.username,
        "PASSWORD": parsed.password,
        "HOST": parsed.hostname,
        "PORT": str(parsed.port or 5432),
        "OPTIONS": {"sslmode": os.environ.get("PG_SSLMODE", "require")}
        if parsed.hostname and "supabase" in parsed.hostname.lower()
        else {},
    }

if (
    len(sys.argv) > 1
    and sys.argv[1] == "test"
    and os.environ.get("FORCE_PG_TESTS")
    and _db_url
):
    DATABASES = {
        "default": _postgres_config_from_url(_db_url)
    }
elif len(sys.argv) > 1 and sys.argv[1] == "test":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "OPTIONS": {"timeout": 30},
        }
    }
elif _db_url:
    DATABASES = {
        "default": _postgres_config_from_url(_db_url)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 30},
        }
    }

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "merchants",
    "payouts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "playto.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "playto.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "dispatch-payout-processing": {
        "task": "payouts.tasks.dispatch_pending_payouts",
        "schedule": 10.0,
    },
    "resume-stuck-processing": {
        "task": "payouts.tasks.resume_stuck_processing_payouts",
        "schedule": 10.0,
    },
}
