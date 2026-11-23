"""Makes `allowed` (the action names the signed-in user may do) available in every template.

    {% if "register_asset" in allowed %} ... show the Assets menu link ... {% endif %}

This only hides links; the views still check can() on the server.
"""

from functools import lru_cache

from .permissions import allowed_actions


def brand(request):
    """Logo files that may be added to static/img/ (they are optional, so pages work without them):
    ku-logo.svg or ku-logo.png (Khalifa University) and campus.jpg (photo for the intro and sign-in pages)."""
    return dict(_find_brand())


@lru_cache(maxsize=1)
def _find_brand():
    from django.contrib.staticfiles import finders

    def first(*names):
        return next((name for name in names if finders.find(name)), None)

    return {"ku_logo": first("img/ku-logo.svg", "img/ku-logo.png"),
            "campus_photo": first("img/campus.jpg", "img/campus.png", "img/campus.webp")}


def access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"allowed": set()}
    return {"allowed": {action.value for action in allowed_actions(user)}}
