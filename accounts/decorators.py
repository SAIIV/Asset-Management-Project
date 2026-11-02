"""Use the access matrix in views.

Function view:

    @permission_required(Action.REGISTER_ASSET)
    def register_asset(request): ...

    # record-level check: the decorator loads the record and checks its scope
    @permission_required(Action.RELEASE_UNITS, record=lambda request, pk: get_object_or_404(Transfer, pk=pk))
    def release(request, pk): ...

Class-based view:

    class AssetCreate(ActionRequiredMixin, CreateView):
        action = Action.REGISTER_ASSET

Not signed in -> sent to the login page.  Signed in but not allowed -> 403.
"""

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .permissions import can


def permission_required(action, record=None):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            obj = record(request, *args, **kwargs) if record else None
            if not can(request.user, action, obj):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


class ActionRequiredMixin(LoginRequiredMixin):
    """For class-based views: set `action`; override get_permission_record() for a record check."""

    action = None

    def get_permission_record(self):
        return None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not can(request.user, self.action, self.get_permission_record()):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
