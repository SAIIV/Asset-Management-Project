# UC-26 Generate an operational report

- **Priority:** Essential
- **Parent group:** FR-06
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Produce a reproducible view of permitted assets and workflow activity without changing operational records.

## Preconditions

- The custodian is signed in with reporting access for an assigned department.

## Trigger

The custodian requests an operational report.

## Main flow

1. The custodian selects a report type, department scope, period and applicable status filters.
2. The system validates filter values and identifies the records the custodian may access.
3. The system establishes a report cutoff and retrieves permitted records for the selected criteria.
4. The system calculates counts from distinct record identifiers and attaches the selected filters to the result.
5. The system displays the report with its generation time, cutoff and links to permitted supporting records.
6. The custodian reviews the result and requests an export.
7. The system rechecks export access and produces the same scoped report, excluding protected fields.

## Alternative flows

- **Alternative at main step 4:** No records match the validated filters.
    1. The system displays zero matching records and the applied filters without inventing report rows.
    - Outcome: Return to main step 5.

## Exception flows

- **Exception at main step 3:** The reporting query cannot complete consistently.
    1. The system labels the report unavailable and does not present a partial count as a completed total.
    2. The system offers a retry using the same filters.
    - Outcome: End without producing a completed report.

## Postconditions

**Success**

- A dated, scoped report and requested export are available.
- Operational records remain unchanged.

**Failure**

- No misleading completed report is issued; source records remain unchanged.

## Business rules

BR-01, BR-14

## Functional requirements

- **P3-FR-26.1** The system shall restrict report records and fields to the requesting user's permissions.
- **P3-FR-26.2** The system shall provide operational reports for assets, requests, transfers, maintenance, ownership changes, approvals and statuses.
- **P3-FR-26.3** The system shall identify the filters and data cutoff used for each generated report.

## Acceptance check

A report for a synthetic department reconciles with its distinct permitted records. A record from another restricted department does not appear in its rows, totals or export.
