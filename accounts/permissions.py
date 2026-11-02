"""C1 Login and roles: the access matrix of Design Document Section 6.2.

Every view asks one question before it shows or changes anything:

    can(user, action, record)  ->  True / False

The default answer is "no" (default: deny). A user is allowed only when one of
their roles has the action in ACCESS_MATRIX *and* the record passes that
role's scope check, for example "own department" or "not their own request".
The check runs on the server for every request, so changing a record ID in
the address bar does not get around it (BR-01, P3-NFR-SEC01).

Prototype 1 has four roles: Requester, Custodian, Approver and Administrator
(Section 3.4). The other Phase 3 roles have no rights yet; their rows are
added when those roles are built (they stay "deny" until then).
"""

from django.db import models

from circular_campus.choices import RoleName


class Action(models.TextChoices):
    """The actions (rows) of the Section 6.2 access matrix."""
    REGISTER_ASSET = "register_asset", "Register or edit an asset"
    REVIEW_AI_CATEGORY = "review_ai_category", "Accept, correct or reject an AI category"
    SEARCH_ASSETS = "search_assets", "Search listed assets"
    SUBMIT_REQUEST = "submit_request", "Submit or revise a request, choose a match"
    RESERVE_UNITS = "reserve_units", "Reserve units"
    APPROVE_REQUEST = "approve_request", "Approve a request"
    RELEASE_UNITS = "release_units", "Release units"
    CONFIRM_RECEIPT = "confirm_receipt", "Confirm receipt"
    REPORT_FAULT = "report_fault", "Report a fault"
    PROPOSE_LIFECYCLE = "propose_lifecycle", "Propose a lifecycle action"
    AUTHORIZE_LIFECYCLE = "authorize_lifecycle", "Authorize donation, recycling or disposal"
    RUN_REPORTS = "run_reports", "Run operational reports"
    VIEW_SUSTAINABILITY = "view_sustainability", "View the sustainability dashboard"
    PUBLISH_SUMMARY = "publish_summary", "Publish a sustainability summary"
    MANAGE_USERS = "manage_users", "Manage users, roles and AI settings"
    EDIT_AUDIT = "edit_audit", "Edit or delete an audit entry"


# Scope rules: how a role's right is limited to certain records.
ANY = "any"                    # every record
OWN_DEPT = "own_dept"          # records of the user's own department
OWN_ASSETS = "own_assets"      # assets owned by the user's department
OWN_REQUEST = "own_request"    # requests the user made
NOT_OWN = "not_own"            # anything except the user's own request (BR-02)

# ACCESS_MATRIX[action][role] = scope.  A missing role means "deny".
ACCESS_MATRIX = {
    Action.REGISTER_ASSET: {RoleName.CUSTODIAN: OWN_DEPT},
    Action.REVIEW_AI_CATEGORY: {RoleName.CUSTODIAN: OWN_DEPT},
    Action.SEARCH_ASSETS: {RoleName.REQUESTER: ANY, RoleName.CUSTODIAN: ANY, RoleName.APPROVER: ANY},
    Action.SUBMIT_REQUEST: {RoleName.REQUESTER: OWN_DEPT},
    Action.RESERVE_UNITS: {RoleName.CUSTODIAN: OWN_ASSETS},
    Action.APPROVE_REQUEST: {RoleName.APPROVER: NOT_OWN},
    Action.RELEASE_UNITS: {RoleName.CUSTODIAN: OWN_ASSETS},
    Action.CONFIRM_RECEIPT: {RoleName.REQUESTER: OWN_REQUEST},
    Action.REPORT_FAULT: {RoleName.REQUESTER: ANY, RoleName.CUSTODIAN: ANY},
    Action.PROPOSE_LIFECYCLE: {RoleName.CUSTODIAN: OWN_ASSETS},
    Action.AUTHORIZE_LIFECYCLE: {RoleName.APPROVER: NOT_OWN},
    Action.RUN_REPORTS: {RoleName.CUSTODIAN: OWN_DEPT, RoleName.APPROVER: OWN_DEPT},
    # Until the Sustainability Officer role exists, the Administrator views the
    # dashboard and edits the summary before it is published (Section 3.4).
    Action.VIEW_SUSTAINABILITY: {RoleName.ADMINISTRATOR: ANY},
    Action.PUBLISH_SUMMARY: {RoleName.ADMINISTRATOR: ANY},
    Action.MANAGE_USERS: {RoleName.ADMINISTRATOR: ANY},
    Action.EDIT_AUDIT: {},  # nobody, ever (BR-14)
}


def user_role_names(user):
    """The names of the roles a signed-in user holds (cached on the user object)."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return set()
    if not hasattr(user, "_role_names"):
        user._role_names = set(user.roles.values_list("name", flat=True))
    return user._role_names


def can(user, action, record=None):
    """True if the user may do the action (on this record, when one is given).

    With record=None only the role is checked; this is for showing or hiding a
    menu item or button. A view that reads or changes a record must pass the
    record, so the department and ownership rules are checked too.
    """
    rules = ACCESS_MATRIX.get(action, {})
    for role in user_role_names(user):
        scope = rules.get(role)
        if scope is not None and (record is None or _in_scope(user, scope, record)):
            return True
    return False


def allowed_actions(user):
    """Every action the user's roles allow (role level), for the start page."""
    return [action for action in Action if can(user, action)]


# ---------------------------------------------------------------- scope checks

def _department_of(record):
    """Which department a record belongs to (None if it has none)."""
    for attr in ("owner_department_id", "department_id"):
        if hasattr(record, attr):
            return getattr(record, attr)
    for attr in ("requester", "asset", "request", "lifecycle_action"):
        related = getattr(record, attr, None)
        if related is not None:
            return _department_of(related)
    return None


def _requester_of(record):
    """The user who asked for the record, or proposed it (None if nobody)."""
    if hasattr(record, "requester_id"):
        return record.requester_id
    request = getattr(record, "request", None)
    if request is not None:
        return request.requester_id
    return getattr(record, "proposer_id", None)


def _in_scope(user, scope, record):
    if scope == ANY:
        return True
    if scope in (OWN_DEPT, OWN_ASSETS):
        return user.department_id is not None and _department_of(record) == user.department_id
    if scope == OWN_REQUEST:
        return _requester_of(record) == user.pk
    if scope == NOT_OWN:
        # An Approval row is assigned to one approver; a request is open to any
        # approver except the person who made it (BR-02: no self-approval).
        if getattr(record, "approver_id", None) not in (None, user.pk):
            return False
        return _requester_of(record) != user.pk
    return False
