"""C9 Basic report (UC-26, Mockup 7): table of requests or transfers, with CSV export.

    /reports/?report=transfers&start=2026-11-01&end=2026-11-30
    /reports/?report=requests&format=csv        -> download the same table as CSV

The department is always the signed-in user's own (scope "own department");
it cannot be changed from the address bar.
"""

from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import permission_required
from accounts.permissions import Action
from accounts.services import AuditService

from .operational import REPORTS, request_rows, summary_facts, totals, transfer_rows, write_csv


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

    draft = None
    if request.method == "POST" and request.POST.get("action") == "draft" and not error:
        from ai.summary import draft_summary  # AI #5, Mockup 7: a draft only, the table stays the source
        draft = draft_summary("operational", summary_facts(title, request.user.department, start, end, rows))

    query = request.GET.copy()
    query.pop("format", None)
    return render(request, "reports/operational.html", {
        "report": report, "reports": [(key, value[0]) for key, value in REPORTS.items()],
        "title": title, "columns": columns, "rows": [[row[key] for key, _ in columns] for row in rows],
        "count": len(rows), "totals": totals(rows), "start": start, "end": end, "error": error,
        "csv_query": query.urlencode(), "draft": draft,
    })


@permission_required(Action.VIEW_SUSTAINABILITY)
def sustainability(request):
    """C7 Sustainability dashboard (UC-28, Mockup 6).

    Until the Sustainability Officer role exists, the Administrator sees it (Section 3.4).
    """
    from .sustainability import dashboard, sync_impacts

    start, end = _date(request.GET.get("start", "")), _date(request.GET.get("end", ""))
    error = "The start date is after the end date." if start and end and start > end else ""
    sync_impacts()  # store the impact of any transfer received since the last visit
    figures = {} if error else dashboard(start, end)
    draft = _summary_action(request, figures, start, end) if request.method == "POST" and figures else None
    if isinstance(draft, HttpResponse):
        return draft
    from ai.summary import latest_published

    from .sustainability import summary_facts

    return render(request, "reports/sustainability.html", {
        "f": figures, "start": start, "end": end, "error": error,
        "draft": draft,
        "published": latest_published("sustainability", summary_facts(figures, start, end) if figures else None),
    })


def _summary_action(request, figures, start, end):
    """AI #5 (UC-38, gate 8): draft a summary, then a person publishes or discards it."""
    from ai.summary import Draft, SummaryError, check_numbers, discard_summary, draft_summary, publish_summary

    from .sustainability import summary_facts

    facts = summary_facts(figures, start, end)
    action = request.POST.get("action")
    record_id = int(request.POST.get("ai_record") or 0)
    if action == "draft":
        return draft_summary("sustainability", facts)
    if action == "publish":
        text = request.POST.get("text", "")
        try:
            publish_summary(request.user, "sustainability", record_id, text, facts)
        except SummaryError as problem:
            messages.error(request, str(problem))
            return Draft(record_id=record_id, text=text.strip(), checks=check_numbers(text, facts))
        messages.success(request, "The summary was published. Every number in it matches the dashboard.")
        return redirect(request.get_full_path())
    if action == "discard":
        discard_summary(request.user, record_id)
        messages.info(request, "The draft was discarded. Nothing was published.")
        return redirect(request.get_full_path())
    return None
