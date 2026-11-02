"""
Django settings for the Circular Campus project (COSC 336, Group 6).

Secrets and machine-specific values are NOT written here. They are read from
a file called .env in the project root (see .env.example). .env is listed in
.gitignore, so real keys and passwords never reach GitHub.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# BASE_DIR is the repository root (the folder that holds manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the values in .env into environment variables.
load_dotenv(BASE_DIR / ".env")


def env(name, default=None, required=False):
    """Read one setting from the environment (filled from .env)."""
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def env_bool(name, default=False):
    return str(env(name, str(default))).strip().lower() in ("1", "true", "yes", "on")


# --- Security -------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]


# --- Applications ---------------------------------------------------------
# One Django app per module of the architecture view (Design Document, Fig. 4).
LOCAL_APPS = [
    "accounts",        # Accounts & Administration: User, Role, audit log (C1)
    "assets",          # Assets & Catalogue: Department, Category, Asset (C2)
    "exchange",        # Search & Requests: ResourceRequest, matches (C3, C4)
    "transfers",       # Reservations, Approvals & Transfers (C5)
    "reports",         # Reporting & Sustainability (C7, C9)
    "notifications",   # In-app notifications (C8)
    "ai",              # AI gateway and AI records (AI #1, #2, #5)
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # ArrayField and other PostgreSQL features
    *LOCAL_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "circular_campus.urls"
WSGI_APPLICATION = "circular_campus.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Shared templates (base layout) live in <repo>/templates.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# --- Database -------------------------------------------------------------
# PostgreSQL 16 + pgvector, started with "docker compose up -d".
# The same DB_* values in .env are used by docker-compose.yml to create the
# database, so Django and Docker always agree on the credentials.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", required=True),
        "USER": env("DB_USER", required=True),
        "PASSWORD": env("DB_PASSWORD", required=True),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
    }
}


# --- Users and passwords --------------------------------------------------
# Custom user model from day one (Design Document Section 9, table User).
# Changing the user model after the first migration is very hard in Django,
# so it is set before any table exists.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Language and time ----------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dubai"
USE_I18N = True
USE_TZ = True


# --- Static files and uploads ---------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # filled by collectstatic, git-ignored
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"          # uploaded photos/PDFs, git-ignored

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
