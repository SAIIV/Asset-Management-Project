"""One date format on every page (19 Nov 2026), instead of Django's US default (Nov. 19, 2026).

Used through FORMAT_MODULE_PATH in settings. Form inputs keep the ISO format (2026-11-19).
"""

DATE_FORMAT = "j M Y"
SHORT_DATE_FORMAT = "j M Y"
DATETIME_FORMAT = "j M Y, H:i"
SHORT_DATETIME_FORMAT = "j M Y, H:i"
