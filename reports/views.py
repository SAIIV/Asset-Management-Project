"""C9 Basic report (UC-26, Mockup 7): table of requests or transfers, with CSV export.

    /reports/?report=transfers&start=2026-11-01&end=2026-11-30
    /reports/?report=requests&format=csv        -> download the same table as CSV

The department is always the signed-in user's own (scope "own department");
it cannot be changed from the address bar.
"""

from datetime import date

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import permission_required
from accounts.permissions import Action
from accounts.services import AuditService

from .operational import REPORTS, request_rows, totals, transfer_rows, write_csv


def _date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@permission_required(Action.RUN_REPORTS)
def operational(request):
    report = request.GET.get("report", "transfers")
    if report not in REPORTS:
        report = "transfers"
    start, end = _date(request.GET.get("start", "")), _date(request.GET.get("end", ""))
    error = "The start date is after the end date." if start and end and start > end else ""
    department = request.user.department_id
    title, columns = REPORTS[report]
    rows = [] if error else (transfer_rows if report == "transfers" else request_rows)(department, start, end)

    if request.GET.get("format") == "csv" and not error:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = f'attachment; filename="circular-campus-{report}-{stamp}.csv"'
        response.write("﻿")  # so Excel opens the UTF-8 file correctly
        write_csv(rows, columns, response)
        AuditService.log(request.user, "export_report", record_type="Report", record_id=0,
                         after={"report": report, "start": str(start or ""), "end": str(end or ""),
                                "rows": len(rows)})
        return response

    query = request.GET.copy()
    query.pop("format", None)
    return render(request, "reports/operational.html", {
        "report": report, "reports": [(key, value[0]) for key, value in REPORTS.items()],
        "title": title, "columns": columns, "rows": [[row[key] for key, _ in columns] for row in rows],
        "count": len(rows), "totals": totals(rows), "start": start, "end": end, "error": error,
        "csv_query": query.urlencode(),
    })
