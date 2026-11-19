"""C9 Basic report: the operational table of requests and transfers (UC-26, Mockup 7).

    transfer_rows(department, start, end)   -> one row per transfer that left or reached the department
    request_rows(department, start, end)    -> one row per request made by the department
    write_csv(rows, columns, file)          -> the same rows as CSV

Custodians and Approvers see their own department only (access matrix: run
operational reports, scope "own department"). The numbers come straight from
the database, so the table and the CSV always agree. The AI summary of this
table is AI #5 (a later step).
"""

import csv

from accounts.models import AuditLog
from exchange.models import ResourceRequest
from transfers.models import Transfer

TRANSFER_COLUMNS = [
    ("transfer", "Transfer"), ("asset", "Asset"), ("from_department", "From"), ("to_department", "To"),
    ("request", "Request"), ("type", "Type"), ("approved_by", "Approved by"), ("released", "Released"),
    ("received", "Received"), ("condition", "Condition on receipt"), ("status", "Status"),
]
REQUEST_COLUMNS = [
    ("request", "Request"), ("requester", "Requester"), ("department", "Department"), ("purpose", "Purpose"),
    ("quantity", "Quantity"), ("urgency", "Urgency"), ("type", "Type"), ("required_by", "Required by"),
    ("reserved", "Units reserved"), ("status", "Status"),
]
REPORTS = {
    "transfers": ("Transfers", TRANSFER_COLUMNS),
    "requests": ("Requests", REQUEST_COLUMNS),
}


def _senders(transfers):
    """Department each transfer came from. After receipt the asset belongs to the receiver,
    so the sender is read from the 'change_custody' audit row written at receipt (C5)."""
    received = {f"Transfer #{t.pk} received": t.pk for t in transfers if t.received_at}
    senders = {}
    if received:
        for event in AuditLog.objects.filter(action="change_custody", reason__in=list(received)):
            senders[received[event.reason]] = (event.before_value or {}).get("owner_department")
    return {t.pk: senders.get(t.pk, t.asset.owner_department_id) for t in transfers}


def transfer_rows(department, start=None, end=None):
    from assets.models import Department
    transfers = list(
        Transfer.objects.select_related("asset__owner_department", "request__requester__department", "approver")
        .order_by("-id")
    )
    if start:
        transfers = [t for t in transfers if t.released_at and t.released_at.date() >= start]
    if end:
        transfers = [t for t in transfers if t.released_at and t.released_at.date() <= end]
    senders = _senders(transfers)
    names = dict(Department.objects.values_list("id", "name"))
    rows = []
    for t in transfers:
        to_id = t.request.requester.department_id
        if department is not None and department not in (senders[t.pk], to_id):
            continue
        rows.append({
            "transfer": f"T-{t.pk:04d}", "asset": t.asset.name,
            "from_department": names.get(senders[t.pk], "—"), "to_department": names.get(to_id, "—"),
            "request": f"#{t.request_id}", "type": t.get_type_display(), "approved_by": t.approver.name,
            "released": t.released_at.strftime("%Y-%m-%d %H:%M") if t.released_at else "",
            "received": t.received_at.strftime("%Y-%m-%d %H:%M") if t.received_at else "",
            "condition": t.get_condition_on_receipt_display() if t.condition_on_receipt else "",
            "status": t.status,
        })
    return rows


def request_rows(department, start=None, end=None):
    requests = (ResourceRequest.objects.select_related("requester__department", "specification")
                .prefetch_related("reservations").order_by("-id"))
    if department is not None:
        requests = requests.filter(requester__department_id=department)
    if start:
        requests = requests.filter(required_by__gte=start)
    if end:
        requests = requests.filter(required_by__lte=end)
    rows = []
    for r in requests:
        spec = getattr(r, "specification", None)
        rows.append({
            "request": f"#{r.pk}", "requester": r.requester.name,
            "department": r.requester.department.name if r.requester.department else "—",
            "purpose": spec.purpose if spec else "", "quantity": r.quantity, "urgency": r.get_urgency_display(),
            "type": r.get_type_display(), "required_by": r.required_by.isoformat(),
            "reserved": sum(1 for x in r.reservations.all() if x.status in ("Active", "Consumed")),
            "status": r.status,
        })
    return rows


def totals(rows):
    """How many rows have each status, for the line under the table."""
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return sorted(counts.items())


def _safe(value):
    """Stop a spreadsheet from running a cell as a formula (CSV injection)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def write_csv(rows, columns, file):
    writer = csv.writer(file)
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([_safe(row[key]) for key, _ in columns])

