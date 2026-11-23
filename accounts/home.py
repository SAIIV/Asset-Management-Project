"""Start page figures: a few counts per role, each linking to the page where the work is done.

Only pages the user's roles may open are linked (same "allowed" rule as the menu).
"""

from django.urls import reverse

from .permissions import Action


def _tile(label, value, hint, url, tone=""):
    return {"label": label, "value": value, "hint": hint, "url": url, "tone": tone}


def tiles(user, actions):
    from assets.models import Asset
    from circular_campus.choices import AssetStatus, RequestStatus, TransferStatus
    from exchange.catalogue import catalogue
    from exchange.models import ResourceRequest
    from exchange.requests import candidates_of
    from notifications.services import unread_count
    from transfers.models import Transfer

    dept = user.department_id
    out = []
    if Action.REGISTER_ASSET in actions:
        own = Asset.objects.filter(owner_department_id=dept)
        out.append(_tile("Assets in my department", own.count(),
                         f"{own.filter(is_listed=True, status=AssetStatus.AVAILABLE).count()} listed in the catalogue",
                         reverse("assets:list")))
    if Action.RESERVE_UNITS in actions:
        waiting = [r for r in ResourceRequest.objects.filter(status=RequestStatus.SUBMITTED).exclude(requester=user)
                   if any(a.owner_department_id == dept for a in candidates_of(r))]
        out.append(_tile("Requests for our items", len(waiting), "submitted and waiting for you to reserve",
                         reverse("transfers:incoming"), "warn" if waiting else ""))
    if Action.RELEASE_UNITS in actions:
        n = Transfer.objects.filter(asset__owner_department_id=dept, status=TransferStatus.SCHEDULED).count()
        out.append(_tile("Units to hand over", n, "approved and ready to release", reverse("transfers:list"),
                         "warn" if n else ""))
    if Action.APPROVE_REQUEST in actions:
        n = ResourceRequest.objects.filter(status=RequestStatus.UNDER_REVIEW).exclude(requester=user).count()
        out.append(_tile("Waiting for approval", n, "reserved requests to approve or return",
                         reverse("transfers:approvals"), "warn" if n else ""))
    if Action.SUBMIT_REQUEST in actions:
        mine = ResourceRequest.objects.filter(requester=user, status__in=[
            RequestStatus.DRAFT, RequestStatus.SUBMITTED, RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED])
        out.append(_tile("My open requests", mine.count(), "draft, submitted, in review or approved",
                         reverse("exchange:requests")))
    if Action.CONFIRM_RECEIPT in actions:
        n = Transfer.objects.filter(request__requester=user, status=TransferStatus.DISPATCHED).count()
        out.append(_tile("Deliveries to confirm", n, "on the way to you", reverse("transfers:list"),
                         "warn" if n else ""))
    if Action.SEARCH_ASSETS in actions:
        out.append(_tile("In the catalogue", catalogue().exclude(owner_department_id=dept).count(),
                         "items other departments can give", reverse("exchange:catalogue")))
    if Action.VIEW_SUSTAINABILITY in actions:
        from reports.sustainability import dashboard, sync_impacts

        sync_impacts()
        f = dashboard()
        co2e = f"{f['co2e_kg']:.0f} kg CO2e avoided" if f["co2e_kg"] is not None else "CO2e not available"
        out.append(_tile("Items reused", f["reuse_count"], co2e, reverse("reports:sustainability"), "ok"))
    unread = unread_count(user)
    out.append(_tile("Unread messages", unread, "in your inbox", reverse("notifications:inbox"),
                     "ai" if unread else ""))
    return out


def quick_actions(actions):
    """The main thing each role starts from (label, url, primary)."""
    out = []
    if Action.REGISTER_ASSET in actions:
        out.append(("Register an asset", reverse("assets:create"), True))
    if Action.SUBMIT_REQUEST in actions:
        out.append(("New request", reverse("exchange:request_create"), True))
    if Action.SEARCH_ASSETS in actions:
        out.append(("Browse the catalogue", reverse("exchange:catalogue"), False))
    if Action.RUN_REPORTS in actions:
        out.append(("Reports", reverse("reports:operational"), False))
    return out


def notices(user, limit=5):
    """The newest inbox messages (read or not), for the start page."""
    from notifications.models import Notification

    return list(Notification.objects.filter(user=user).order_by("-id")[:limit])


ACTION_WORDS = {
    "register_asset": "registered", "edit_asset": "edited", "publish_asset": "published",
    "unpublish_asset": "took off the catalogue", "change_asset_status": "changed the status of",
    "create_request": "created", "submit_request": "submitted", "revise_request": "revised",
    "cancel_request": "cancelled", "reserve_request": "reserved units for", "approve_request": "approved",
    "release_transfer": "released", "receive_transfer": "confirmed receipt of", "dispute_transfer": "disputed",
    "change_custody": "took over", "cannot_supply": "said they cannot supply", "report_fault": "reported a fault on",
    "publish_summary": "published a sustainability summary", "export_report": "exported a report",
    "edit_profile": "updated their profile", "change_password": "changed their password",
    "start_repair": "started the repair of", "finish_repair": "finished the repair of", "close_fault": "closed",
    "propose_lifecycle": "proposed retiring", "authorize_lifecycle": "approved", "reject_lifecycle": "rejected",
    "execute_lifecycle": "carried out", "cancel_lifecycle": "withdrew",
    "return_request": "put back to Submitted",
}
#: Internal steps that repeat a main step above (the same click), left out of the feed.
HIDDEN = ["sign_in", "sign_out", "sign_in_failed", "reserve_asset", "release_asset", "receive_asset",
          "consume_reservation", "release_reservation", "schedule_transfer", "decide_approval",
          "fulfil_request", "approve", "create", "update", "correct", "fix", "retire_asset", "invalidate_approval"]
LABELS = {"ResourceRequest": "Request", "Transfer": "Transfer", "Asset": "Asset", "Approval": "Approval",
          "MaintenanceRecord": "Fault", "LifecycleAction": "Retirement proposal"}


def recent_activity(user, limit=8):
    """What happened lately in the user's department (everything for the Administrator)."""
    from accounts.models import AuditLog
    from circular_campus.choices import RoleName

    rows = AuditLog.objects.select_related("user").exclude(action__in=HIDDEN)
    if not user.roles.filter(name=RoleName.ADMINISTRATOR).exists():
        rows = rows.filter(user__department_id=user.department_id)
    out = []
    for row in rows.exclude(user__isnull=True).order_by("-created_at", "-id")[:limit]:
        verb = ACTION_WORDS.get(row.action, row.action.replace("_", " "))
        what = "" if row.record_type in ("Report", "User", "") else f"{LABELS.get(row.record_type, row.record_type)} #{row.record_id}"
        out.append({"who": row.user.name, "verb": verb, "what": what, "when": row.created_at})
    return out
