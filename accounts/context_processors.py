"""Makes `allowed` (the action names the signed-in user may do) available in every template.

    {% if "register_asset" in allowed %} ... show the Assets menu link ... {% endif %}

This only hides links; the views still check can() on the server.
"""

from .permissions import allowed_actions


def access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"allowed": set()}
    return {"allowed": {action.value for action in allowed_actions(user)}}
